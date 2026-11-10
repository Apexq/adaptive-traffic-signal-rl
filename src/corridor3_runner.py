"""
Real-World RESCO Cologne-3 (3 Intersections) & Cologne-1 Traffic Signal Control Runner
Features:
  - 4-Phase Acyclic Smart Phase Selection (Faz 0, 2, 4, 6) with Empty Turn-Phase Skipping
  - Deep Phase-Competition Q-Network (6 -> 64 -> 64 -> 1) trained from 100% random He weights
  - Live Console Progress Bar with Elapsed Time & ETA
  - Automatic Per-Episode Checkpoint Save & Resume (models/training_checkpoint.json)
"""

import csv
import os
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List

SUMO_HOME = os.environ.get("SUMO_HOME", r"C:\Program Files (x86)\SUMO")
SUMO_TOOLS = os.path.join(SUMO_HOME, "tools")
if SUMO_TOOLS not in sys.path:
    sys.path.append(SUMO_TOOLS)

import traci
from rl_agent import DQNAgent

BASE_DIR = Path(__file__).resolve().parent.parent
SUMOCFG_C3 = BASE_DIR / "nets" / "cologne3" / "cologne3.sumocfg"
MODEL_PATH = BASE_DIR / "models" / "dqn_resco_cologne.json"
CKPT_PATH = BASE_DIR / "models" / "training_checkpoint.json"
RESULTS_DIR = BASE_DIR / "results"


class RealNetworkSimulation:
    """
    Controls real-world RESCO Cologne-3 intersections with 4-phase acyclic smart phase selection.
    """

    def __init__(
        self,
        sumocfg_path: Path = SUMOCFG_C3,
        mode: str = "dqn",
        use_gui: bool = False,
        seed: int = 42,
        sim_duration: int = 3600,
        agent: DQNAgent | None = None,
        train_mode: bool = False,
    ):
        self.sumocfg_path = sumocfg_path
        self.mode = mode.lower()
        self.use_gui = use_gui
        self.seed = seed
        self.sim_duration = sim_duration
        self.train_mode = train_mode
        self.min_green_major = 10
        self.min_green_turn = 4
        self.max_green_major = 45
        self.max_green_turn = 10
        self.yellow_time = 3
        self.delta_time = 5

        if agent is not None:
            self.agent = agent
        else:
            self.agent = DQNAgent(seed=seed)
            if MODEL_PATH.exists() and not train_mode:
                self.agent.load(MODEL_PATH)

        # Populated dynamically from the real Cologne .net.xml
        self.tl_ids: List[str] = []
        self.tl_green_phases: Dict[str, List[int]] = {}
        self.tl_phase_lanes: Dict[str, List[List[str]]] = {}
        self.tl_is_turn_phase: Dict[str, List[bool]] = {}
        self.tl_all_lanes: Dict[str, List[str]] = {}

        self.current_action_idx: Dict[str, int] = {}
        self.elapsed_green: Dict[str, int] = {}
        self.pending_yellow: Dict[str, int] = {}
        self.target_action_idx: Dict[str, int] = {}

    def _discover_network_topology(self):
        """Inspects all traffic lights in the real Cologne network and maps all green phases (0, 2, 4, 6)."""
        self.tl_ids = list(traci.trafficlight.getIDList())
        for tl in self.tl_ids:
            logic = traci.trafficlight.getAllProgramLogics(tl)[0]
            links = traci.trafficlight.getControlledLinks(tl)

            green_phases = []
            phase_lanes = []
            is_turn_list = []
            all_lanes_set = set()

            for p_idx, phase in enumerate(logic.phases):
                if "y" not in phase.state.lower() and "g" in phase.state.lower():
                    is_turn = phase.duration <= 10
                    lanes_for_phase = []
                    # For turn phases, only count dedicated protected 'G' lanes; for major phases, count 'G' and 'g'
                    target_chars = ("G",) if is_turn else ("G", "g")
                    for link_idx, ch in enumerate(phase.state):
                        if ch in target_chars and link_idx < len(links) and links[link_idx]:
                            lane_id = links[link_idx][0][0]
                            if lane_id not in lanes_for_phase:
                                lanes_for_phase.append(lane_id)
                            all_lanes_set.add(lane_id)

                    green_phases.append(p_idx)
                    phase_lanes.append(lanes_for_phase)
                    is_turn_list.append(is_turn)

            self.tl_green_phases[tl] = green_phases
            self.tl_phase_lanes[tl] = phase_lanes
            self.tl_is_turn_phase[tl] = is_turn_list
            self.tl_all_lanes[tl] = sorted(all_lanes_set)

            self.current_action_idx[tl] = 0
            self.elapsed_green[tl] = 0
            self.pending_yellow[tl] = 0
            self.target_action_idx[tl] = 0

            traci.trafficlight.setPhase(tl, green_phases[0])
            traci.trafficlight.setPhaseDuration(tl, 10000)

    def _extract_phase_features_and_mask(self, tl: str) -> tuple[List[List[float]], List[bool]]:
        """
        Extracts the 6D feature vector and valid phase mask for each green phase p in {0, ..., K-1}:
          [q_norm, v_norm, w_norm, max_other_q_norm, is_active, is_major_phase]
        Masking for Smart Phase Skipping:
          - Protected left-turn phases (Faz 2, Faz 6) are masked out (False) if they have < 2 halting vehicles,
            so the DQN agent skips empty turn phases and jumps directly to high-demand phases!
        """
        phase_lanes_list = self.tl_phase_lanes[tl]
        is_turn_list = self.tl_is_turn_phase[tl]

        raw_queues = []
        raw_vehs = []
        raw_waits = []
        valid_mask = []

        for idx, lanes in enumerate(phase_lanes_list):
            n_lanes = max(1, len(lanes))
            halt_cnt = sum(traci.lane.getLastStepHaltingNumber(l) for l in lanes)
            veh_cnt = sum(traci.lane.getLastStepVehicleNumber(l) for l in lanes)
            wait_sum = sum(traci.lane.getWaitingTime(l) for l in lanes)

            q_norm = halt_cnt / (n_lanes * 8.0)
            v_norm = veh_cnt / (n_lanes * 12.0)
            w_norm = min(1.0, wait_sum / (n_lanes * 150.0))

            raw_queues.append(q_norm)
            raw_vehs.append(v_norm)
            raw_waits.append(w_norm)

            if is_turn_list[idx]:
                # Only allow selecting a dedicated left-turn phase if >= 2 vehicles are halted or waiting >= 25s
                valid_mask.append(halt_cnt >= 2 or wait_sum >= 25.0)
            else:
                valid_mask.append(True)

        cur_a = self.current_action_idx[tl]
        features = []
        for idx in range(len(phase_lanes_list)):
            other_qs = [raw_queues[j] for j in range(len(phase_lanes_list)) if j != idx]
            max_other_q = max(other_qs) if other_qs else 0.0
            is_act = 1.0 if idx == cur_a else 0.0
            is_major = 0.0 if is_turn_list[idx] else 1.0
            features.append(
                [
                    raw_queues[idx],
                    raw_vehs[idx],
                    raw_waits[idx],
                    max_other_q,
                    is_act,
                    is_major,
                ]
            )
        return features, valid_mask

    def _select_next_phase_idx(self, tl: str, phase_features: List[List[float]], valid_mask: List[bool]) -> int:
        cur_a = self.current_action_idx[tl]
        elapsed = self.elapsed_green[tl]
        num_phases = len(phase_features)
        is_turn = self.tl_is_turn_phase[tl][cur_a]

        if self.mode == "fixed":
            # 1. Fixed-Time: Rigidly cycles 0 -> 1 -> 2 -> 3 in fixed ring order
            fixed_dur = 8 if is_turn else 42
            if elapsed >= fixed_dur:
                return (cur_a + 1) % num_phases
            return cur_a

        min_g = self.min_green_turn if is_turn else self.min_green_major
        max_g = self.max_green_turn if is_turn else self.max_green_major
        if elapsed < min_g:
            return cur_a

        if self.mode == "actuated":
            # 2. Classical Actuated: Uses gap-out, but MUST follow fixed sequential ring order (0 -> 1 -> 2 -> 3)
            lanes_cur = self.tl_phase_lanes[tl][cur_a]
            active_halt = sum(traci.lane.getLastStepHaltingNumber(l) for l in lanes_cur)
            act_max_g = 8 if is_turn else 38
            if active_halt <= 2 or elapsed >= act_max_g:
                return (cur_a + 1) % num_phases
            return cur_a

        else:
            # 3. Proposed DQN RL with Smart Phase Skipping (Acyclic Phase Selection)
            if is_turn and elapsed >= max_g:
                # Immediately exit short turn phase to highest-demand major phase
                major_Mask = [not self.tl_is_turn_phase[tl][i] for i in range(num_phases)]
                return self.agent.select_action(phase_features, valid_mask=major_Mask, evaluate=not self.train_mode)

            if elapsed >= max_g:
                other_mask = [valid_mask[i] and i != cur_a for i in range(num_phases)]
                if any(other_mask):
                    return self.agent.select_action(phase_features, valid_mask=other_mask, evaluate=not self.train_mode)

            return self.agent.select_action(phase_features, valid_mask=valid_mask, evaluate=not self.train_mode)

    def run(
        self,
        tripinfo_path: Path | None = None,
        verbose: bool = True,
        ep_num: int = 0,
        total_eps: int = 0,
        train_start_wall: float = 0.0,
        start_ep_idx: int = 1,
    ) -> Dict[str, float]:
        try:
            traci.close()
        except Exception:
            pass

        sumo_bin = os.path.join(SUMO_HOME, "bin", "sumo-gui.exe" if self.use_gui else "sumo.exe")
        cmd = [
            sumo_bin,
            "-c",
            str(self.sumocfg_path),
            "--seed",
            str(self.seed),
            "--no-warnings",
            "true",
            "--no-step-log",
            "true",
        ]
        if tripinfo_path:
            cmd.extend(["--tripinfo-output", str(tripinfo_path)])

        traci.start(cmd)
        self._discover_network_topology()

        start_time = int(traci.simulation.getTime())
        end_time = start_time + self.sim_duration
        history = []
        ep_reward = 0.0
        losses = []

        while traci.simulation.getTime() < end_time:
            sim_t = int(traci.simulation.getTime()) - start_time

            if sim_t % self.delta_time == 0:
                for tl in self.tl_ids:
                    if self.pending_yellow[tl] == 0:
                        feats, valid_mask = self._extract_phase_features_and_mask(tl)
                        desired_idx = self._select_next_phase_idx(tl, feats, valid_mask)

                        if self.train_mode:
                            chosen_f = feats[desired_idx]
                            # Reward: queue pressure cleared + major-flow throughput bonus - competing queue penalty
                            pressure_gain = (
                                chosen_f[0] * 3.2
                                + chosen_f[1] * 1.6
                                + chosen_f[2] * 2.0
                                + chosen_f[5] * 0.4
                                - chosen_f[3] * 2.6
                            )
                            switch_cost = -0.18 if desired_idx != self.current_action_idx[tl] else 0.06
                            r_tl = pressure_gain + switch_cost
                            self.agent.store_transition(feats, desired_idx, r_tl, feats, False)
                            loss = self.agent.update()
                            if loss > 0:
                                losses.append(loss)
                            ep_reward += r_tl

                        if desired_idx != self.current_action_idx[tl]:
                            # Activate 3-second Yellow Phase for current green phase, then jump directly to desired phase!
                            cur_sumo_phase = self.tl_green_phases[tl][self.current_action_idx[tl]]
                            yellow_sumo_phase = cur_sumo_phase + 1
                            traci.trafficlight.setPhase(tl, yellow_sumo_phase)
                            self.pending_yellow[tl] = self.yellow_time
                            self.target_action_idx[tl] = desired_idx

            traci.simulationStep()

            for tl in self.tl_ids:
                if self.pending_yellow[tl] > 0:
                    self.pending_yellow[tl] -= 1
                    if self.pending_yellow[tl] == 0:
                        self.current_action_idx[tl] = self.target_action_idx[tl]
                        self.elapsed_green[tl] = 0
                        next_sumo_phase = self.tl_green_phases[tl][self.current_action_idx[tl]]
                        traci.trafficlight.setPhase(tl, next_sumo_phase)
                        traci.trafficlight.setPhaseDuration(tl, 10000)
                else:
                    self.elapsed_green[tl] += 1

            if sim_t % self.delta_time == 0:
                total_halting = 0
                total_co2_mg = 0.0
                per_tl_status = []
                for idx, tl in enumerate(self.tl_ids, 1):
                    lanes = self.tl_all_lanes[tl]
                    halt = sum(traci.lane.getLastStepHaltingNumber(l) for l in lanes)
                    co2 = sum(traci.lane.getCO2Emission(l) for l in lanes) * self.delta_time
                    total_halting += halt
                    total_co2_mg += co2
                    short_name = f"Kavsak-{idx}({tl[:6]})"
                    p_num = self.tl_green_phases[tl][self.current_action_idx[tl]]
                    p_type = "SolDonus" if self.tl_is_turn_phase[tl][self.current_action_idx[tl]] else "AnaYol"
                    per_tl_status.append(
                        f"{short_name}[Faz-{p_num}({p_type}) {self.elapsed_green[tl]:2d}s | Kuyruk:{halt:2d}]"
                    )

                history.append({"halting_total": total_halting, "co2_g": total_co2_mg / 1000.0})

                # Live Progress Bar during CLI training
                if self.train_mode and total_eps > 0 and sim_t % 60 == 0:
                    pct = int((sim_t / float(self.sim_duration)) * 100)
                    filled = pct // 5
                    bar = "#" * filled + "-" * (20 - filled)
                    elapsed_wall = time.time() - train_start_wall
                    done_frac = max(0.01, (ep_num - start_ep_idx) + (sim_t / float(self.sim_duration)))
                    rem_eps = (total_eps - start_ep_idx + 1) - done_frac
                    eta_sec = int((elapsed_wall / done_frac) * max(0.0, rem_eps))
                    eta_m, eta_s = divmod(eta_sec, 60)
                    sys.stdout.write(
                        f"\r  [Bolum {ep_num:02d}/{total_eps:02d}] [{bar}] %{pct:3d} | "
                        f"Anlik Kuyruk: {total_halting:2d} arac | Eps: {self.agent.epsilon:.3f} | "
                        f"Kalan Tahmini Sure (ETA): ~{eta_m:02d}dk {eta_s:02d}sn   "
                    )
                    sys.stdout.flush()

                if verbose and self.use_gui and sim_t % 10 == 0:
                    clock_h = int(traci.simulation.getTime()) // 3600
                    clock_m = (int(traci.simulation.getTime()) % 3600) // 60
                    clock_s = int(traci.simulation.getTime()) % 60
                    print(
                        f"[Koln Saat {clock_h:02d}:{clock_m:02d}:{clock_s:02d} (t={sim_t:4d}s) | Mod: {self.mode.upper():8s}]\n"
                        f"   " + " || ".join(per_tl_status) + f" => Toplam Kuyruk: {total_halting:3d} arac"
                    )

        traci.close()

        avg_q = sum(h["halting_total"] for h in history) / max(1, len(history))
        co2_kg = sum(h["co2_g"] for h in history) / 1000.0
        avg_wait = 0.0
        avg_loss = 0.0
        avg_dur = 0.0
        completed = 0

        if tripinfo_path and tripinfo_path.exists():
            tree = ET.parse(tripinfo_path)
            trips = tree.getroot().findall("tripinfo")
            completed = len(trips)
            n = max(1, completed)
            avg_wait = sum(float(t.attrib.get("waitingTime", 0.0)) for t in trips) / n
            avg_loss = sum(float(t.attrib.get("timeLoss", 0.0)) for t in trips) / n
            avg_dur = sum(float(t.attrib.get("duration", 0.0)) for t in trips) / n

        return {
            "mode": self.mode,
            "completed_trips": completed,
            "avg_waiting_time_s": round(avg_wait, 2),
            "avg_time_loss_s": round(avg_loss, 2),
            "avg_travel_time_s": round(avg_dur, 2),
            "avg_corridor_queue_veh": round(avg_q, 2),
            "total_co2_kg": round(co2_kg, 2),
            "ep_reward": round(ep_reward, 1),
            "avg_loss": round(sum(losses) / max(1, len(losses)), 4),
        }


def save_training_csv_and_svg(training_rows: List[Dict]):
    if not training_rows:
        return
    train_csv = RESULTS_DIR / "training_log.csv"
    with train_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(training_rows[0].keys()))
        writer.writeheader()
        writer.writerows(training_rows)


def train_dqn_checkpointed(total_episodes: int = 50, sim_duration: int = 3600, reset_ckpt: bool = False) -> DQNAgent:
    """
    Trains the 4-Phase Deep Q-Network (6 -> 64 -> 64 -> 1) on real RESCO Cologne-3
    with Live Progress Bar and Automatic Per-Episode Checkpoint Save & Resume.
    """
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR = BASE_DIR / "models"
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    agent = DQNAgent(seed=42)
    start_ep = 1
    best_wait = float("inf")
    training_rows: List[Dict] = []

    if reset_ckpt and CKPT_PATH.exists():
        CKPT_PATH.unlink()
        print("[BILGI] Eski egitim kaydi (checkpoint) sifirlandi. 1. Bolumden baslaniyor.")

    if CKPT_PATH.exists():
        try:
            last_ep, best_wait, training_rows = agent.load_checkpoint(CKPT_PATH)
            if last_ep < total_episodes:
                start_ep = last_ep + 1
                print("========================================================================================")
                print(f"  [KAYIT BULUNDU] Onceki egitim {last_ep}/{total_episodes}. bolumde kalmis (En Iyi Bekleme: {best_wait:.2f} sn).")
                print(f"  Egitim {start_ep}. bolumden KALDIGI YERDEN devam ediyor...")
                print("========================================================================================")
            else:
                print(f"[BILGI] {total_episodes}/{total_episodes} bolumluk egitim zaten tamamlanmis!")
                return agent
        except Exception:
            start_ep = 1

    print("========================================================================================")
    print(f"  GERCEK KOLN (COLOGNE-3) - 4 FAZLI AKILLI DQN EGITIMI ({start_ep}..{total_episodes} BOLUM)")
    print("  [BILGI] Her bolum sonunda otomatik kayit alinir.")
    print("  [BILGI] Istediginiz an Ctrl+C basip durdurabilir ve sonra kaldiginiz yerden devam edebilirsiniz!")
    print("========================================================================================")

    train_start_wall = time.time()

    try:
        for ep in range(start_ep, total_episodes + 1):
            t_path = RESULTS_DIR / f"train_c3_ep{ep}.tripinfo.xml"
            sim = RealNetworkSimulation(
                sumocfg_path=SUMOCFG_C3,
                mode="dqn",
                use_gui=False,
                seed=100 + ep * 13,
                sim_duration=sim_duration,
                agent=agent,
                train_mode=True,
            )
            m = sim.run(
                tripinfo_path=t_path,
                verbose=False,
                ep_num=ep,
                total_eps=total_episodes,
                train_start_wall=train_start_wall,
                start_ep_idx=start_ep,
            )
            if t_path.exists():
                t_path.unlink()

            is_new_best = False
            if m["avg_waiting_time_s"] < best_wait:
                best_wait = m["avg_waiting_time_s"]
                agent.best_net.copy_from(agent.q_net)
                is_new_best = True

            row = {
                "episode": ep,
                "epsilon": round(agent.epsilon, 3),
                "ep_reward": m["ep_reward"],
                "avg_waiting_time_s": m["avg_waiting_time_s"],
                "avg_corridor_queue_veh": m["avg_corridor_queue_veh"],
                "avg_loss": m["avg_loss"],
                "best_wait_s": round(best_wait, 2),
            }
            training_rows.append(row)
            agent.decay_epsilon_episode()

            # Save checkpoint & best weights immediately after every episode
            agent.save_checkpoint(CKPT_PATH, ep, total_episodes, best_wait, training_rows)
            agent.q_net_backup = DeepPhaseMLP_copy = None
            # Save best model to MODEL_PATH so GUI demos can use it right away
            best_dict = agent.best_net.to_dict()
            MODEL_PATH.write_text(__import__("json").dumps(best_dict, indent=2), encoding="utf-8")
            save_training_csv_and_svg(training_rows)

            best_tag = " [YENI REKOR!]" if is_new_best else ""
            sys.stdout.write("\r" + " " * 115 + "\r")
            print(
                f"  Bolum {ep:02d}/{total_episodes:02d} Tamamlandi | Eps: {row['epsilon']:.3f} | "
                f"Ort. Bekleme: {row['avg_waiting_time_s']:6.2f} sn | "
                f"Ort. Kuyruk: {row['avg_corridor_queue_veh']:5.2f} arac | "
                f"En Iyi: {best_wait:5.2f} sn{best_tag}"
            )

    except KeyboardInterrupt:
        try:
            traci.close()
        except Exception:
            pass
        print("\n\n========================================================================================")
        print(f"  [DURDURULDU] Egitim kullanici tarafindan duraklatildi.")
        print(f"  Son tamamlanan bolum ve en iyi model ({MODEL_PATH.name}) guvenle kaydedildi!")
        print("  Daha sonra tekrar baslattiginizda kaldigi bolumden devam edecektir.")
        print("========================================================================================")
        return agent

    agent.q_net.copy_from(agent.best_net)
    agent.save(MODEL_PATH)
    print(f"\n[TAMAMLANDI] 50 Bolumluk DQN egitimi bitti! En iyi model kaydedildi: {MODEL_PATH}\n")
    return agent


def run_benchmark_comparison(sim_duration: int = 1800):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    if not MODEL_PATH.exists():
        train_dqn_checkpointed(total_episodes=15, sim_duration=1800)

    modes = [
        ("fixed", "1. Fixed-Time (Sabit Sureli Klasik)"),
        ("actuated", "2. Actuated (Klasik Sirali Sensorlu)"),
        ("dqn", "3. DQN RL (4 Fazli Akilli Faz Atlama)"),
    ]
    rows = []
    print("========================================================================================")
    print("   GERCEK KOLN HARITASI (RESCO COLOGNE-3: 3 KAVSAK) - 3 DURUM KARSILASTIRMA TESTI")
    print("========================================================================================")
    for code, label in modes:
        t_path = RESULTS_DIR / f"c3_real_{code}.tripinfo.xml"
        sim = RealNetworkSimulation(
            sumocfg_path=SUMOCFG_C3,
            mode=code,
            use_gui=False,
            seed=42,
            sim_duration=sim_duration,
            train_mode=False,
        )
        metrics = sim.run(tripinfo_path=t_path, verbose=False)
        if t_path.exists():
            t_path.unlink()
        metrics["label"] = label
        rows.append(metrics)
        print(
            f"  {label:40s} | Ort. Bekleme: {metrics['avg_waiting_time_s']:6.2f} sn | "
            f"Kuyruk: {metrics['avg_corridor_queue_veh']:5.2f} arac | "
            f"Seyahat: {metrics['avg_travel_time_s']:6.2f} sn | CO2: {metrics['total_co2_kg']:6.2f} kg"
        )

    base_wait = rows[0]["avg_waiting_time_s"]
    act_wait = rows[1]["avg_waiting_time_s"]
    dqn_wait = rows[2]["avg_waiting_time_s"]
    print("----------------------------------------------------------------------------------------")
    for r in rows[1:]:
        imp = ((base_wait - r["avg_waiting_time_s"]) / base_wait) * 100.0
        print(f"  -> {r['label']} Sabit Isiga Gore Bekleme Suresini %{imp:.1f} Azaltti!")
    imp_vs_act = ((act_wait - dqn_wait) / act_wait) * 100.0
    print(f"  -> 3. DQN RL (Akilli Faz Atlama), Klasik Sensorlu (Actuated) Sisteme Gore Beklemeyi %{imp_vs_act:.1f} Daha Fazla Azaltti!")
    print("========================================================================================")

    csv_path = RESULTS_DIR / "cologne3_corridor_summary.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    arg = sys.argv[1].lower() if len(sys.argv) > 1 else "compare"
    if arg == "train":
        reset_flag = "--reset" in [a.lower() for a in sys.argv[2:]]
        train_dqn_checkpointed(total_episodes=50, sim_duration=3600, reset_ckpt=reset_flag)
        run_benchmark_comparison(sim_duration=1800)
    elif arg in ("fixed", "actuated", "dqn"):
        sim = RealNetworkSimulation(
            sumocfg_path=SUMOCFG_C3,
            mode=arg,
            use_gui=True,
            seed=42,
            sim_duration=1800,
            train_mode=False,
        )
        sim.run(verbose=True)
    else:
        run_benchmark_comparison(sim_duration=1800)
