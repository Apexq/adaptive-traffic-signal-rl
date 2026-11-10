"""
Real-World RESCO Cologne-3 (3 Intersections) & Cologne-1 Traffic Signal Control Runner
- Automatically extracts real traffic light phases and incoming street lanes via TraCI
- Trains the Phase-Competition DQN Agent FROM SCRATCH (100% random initial weights)
- Evaluates Fixed-Time (Static), Actuated (Gap-Out), and DQN RL on real Cologne traffic (07:00-08:00 AM)
"""

import csv
import os
import sys
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
SUMOCFG_C1 = BASE_DIR / "nets" / "cologne1" / "cologne1.sumocfg"
MODEL_PATH = BASE_DIR / "models" / "dqn_resco_cologne.json"
RESULTS_DIR = BASE_DIR / "results"


class RealNetworkSimulation:
    """
    Controls real-world RESCO Cologne networks (Cologne-1 or Cologne-3) dynamically via TraCI.
    """

    def __init__(
        self,
        sumocfg_path: Path = SUMOCFG_C3,
        mode: str = "dqn",
        use_gui: bool = False,
        seed: int = 42,
        sim_duration: int = 1800,
        agent: DQNAgent | None = None,
        train_mode: bool = False,
    ):
        self.sumocfg_path = sumocfg_path
        self.mode = mode.lower()
        self.use_gui = use_gui
        self.seed = seed
        self.sim_duration = sim_duration
        self.train_mode = train_mode
        self.min_green = 10
        self.max_green = 45
        self.yellow_time = 3
        self.delta_time = 5

        if agent is not None:
            self.agent = agent
        else:
            self.agent = DQNAgent(seed=seed)
            if MODEL_PATH.exists() and not train_mode:
                self.agent.load(MODEL_PATH)

        # Populated dynamically from the real .net.xml once TraCI starts
        self.tl_ids: List[str] = []
        # Major green phases (e.g. [0, 4] in RESCO Cologne intersections)
        self.tl_major_phases: Dict[str, List[int]] = {}
        self.tl_major_lanes: Dict[str, List[List[str]]] = {}
        self.tl_all_lanes: Dict[str, List[str]] = {}

        self.current_action_idx: Dict[str, int] = {}
        self.elapsed_green: Dict[str, int] = {}
        self.transition_queue: Dict[str, List[Tuple[int, int]]] = {}
        self.target_action_idx: Dict[str, int] = {}
        self.prev_features: Dict[str, List[List[float]]] = {}

    def _discover_network_topology(self):
        """Inspects all traffic lights in the real Cologne network and maps major green phases to street lanes."""
        self.tl_ids = list(traci.trafficlight.getIDList())
        for tl in self.tl_ids:
            logic = traci.trafficlight.getAllProgramLogics(tl)[0]
            links = traci.trafficlight.getControlledLinks(tl)

            major_phases = []
            major_lanes = []
            all_lanes_set = set()

            for p_idx, phase in enumerate(logic.phases):
                if "y" not in phase.state.lower() and "g" in phase.state.lower():
                    lanes_for_phase = []
                    for link_idx, ch in enumerate(phase.state):
                        if ch in ("G", "g") and link_idx < len(links) and links[link_idx]:
                            lane_id = links[link_idx][0][0]
                            if lane_id not in lanes_for_phase:
                                lanes_for_phase.append(lane_id)
                            all_lanes_set.add(lane_id)

                    # In RESCO Cologne, major phases have duration >= 20s (phases 0 and 4),
                    # while 6s phases (2 and 6) are lagging left-turn clearance stages.
                    if phase.duration >= 15:
                        major_phases.append(p_idx)
                        major_lanes.append(lanes_for_phase)

            self.tl_major_phases[tl] = major_phases
            self.tl_major_lanes[tl] = major_lanes
            self.tl_all_lanes[tl] = sorted(all_lanes_set)

            self.current_action_idx[tl] = 0
            self.elapsed_green[tl] = 0
            self.transition_queue[tl] = []
            self.target_action_idx[tl] = 0

            traci.trafficlight.setPhase(tl, major_phases[0])
            traci.trafficlight.setPhaseDuration(tl, 10000)

    def _extract_phase_features(self, tl: str) -> List[List[float]]:
        """
        Builds the 6D feature vector for each major green phase p of traffic light `tl`:
          [q_norm, v_norm, w_norm, competing_q_norm, is_active, elapsed_ratio]
        """
        phase_lanes_list = self.tl_major_lanes[tl]
        raw_queues = []
        raw_vehs = []
        raw_waits = []

        for lanes in phase_lanes_list:
            n_lanes = max(1, len(lanes))
            q = sum(traci.lane.getLastStepHaltingNumber(l) for l in lanes) / (n_lanes * 8.0)
            v = sum(traci.lane.getLastStepVehicleNumber(l) for l in lanes) / (n_lanes * 12.0)
            w = min(1.0, sum(traci.lane.getWaitingTime(l) for l in lanes) / (n_lanes * 150.0))
            raw_queues.append(q)
            raw_vehs.append(v)
            raw_waits.append(w)

        cur_a = self.current_action_idx[tl]
        elapsed_ratio = min(1.0, self.elapsed_green[tl] / float(self.max_green))

        features = []
        for idx in range(len(phase_lanes_list)):
            other_qs = [raw_queues[j] for j in range(len(phase_lanes_list)) if j != idx]
            max_other_q = max(other_qs) if other_qs else 0.0
            is_act = 1.0 if idx == cur_a else 0.0
            features.append(
                [
                    raw_queues[idx],
                    raw_vehs[idx],
                    raw_waits[idx],
                    max_other_q,
                    is_act,
                    elapsed_ratio,
                ]
            )
        return features

    def _select_next_phase_idx(self, tl: str, phase_features: List[List[float]]) -> int:
        cur_a = self.current_action_idx[tl]
        elapsed = self.elapsed_green[tl]
        num_phases = len(phase_features)

        if self.mode == "fixed":
            # Standard Static Fixed-Time Cycle (45s per direction)
            if elapsed >= 45:
                return (cur_a + 1) % num_phases
            return cur_a

        if elapsed < self.min_green:
            return cur_a

        if self.mode == "actuated":
            # Classical Traffic-Actuated (Gap-Out): switches when active queue <= 2 and competing queue > 2
            lanes_cur = self.tl_major_lanes[tl][cur_a]
            other_a = (cur_a + 1) % num_phases
            lanes_other = self.tl_major_lanes[tl][other_a]
            active_halt = sum(traci.lane.getLastStepHaltingNumber(l) for l in lanes_cur)
            other_halt = sum(traci.lane.getLastStepHaltingNumber(l) for l in lanes_other)

            if active_halt <= 2 and other_halt > 2:
                return other_a
            if elapsed >= 35 and other_halt > 0:
                return other_a
            return cur_a

        else:
            # Proposed DQN RL Agent
            if elapsed >= self.max_green:
                other_a = (cur_a + 1) % num_phases
                if phase_features[other_a][0] > 0:
                    return other_a
            return self.agent.select_action(phase_features, evaluate=not self.train_mode)

    def _build_transition_sequence(self, tl: str, from_action: int, to_action: int) -> List[Tuple[int, int]]:
        """
        Builds the safe yellow + lagging left-turn transition sequence between major phases in Cologne.
        """
        logic = traci.trafficlight.getAllProgramLogics(tl)[0]
        num_sumo_phases = len(logic.phases)
        start_p = self.tl_major_phases[tl][from_action]
        end_p = self.tl_major_phases[tl][to_action]

        seq = []
        p = (start_p + 1) % num_sumo_phases
        while p != end_p:
            dur = int(logic.phases[p].duration)
            # Shorten lagging left-turn phase from 6s to 4s for snappier adaptive clearing
            step_dur = 3 if "y" in logic.phases[p].state.lower() else min(4, dur)
            seq.append((p, step_dur))
            p = (p + 1) % num_sumo_phases
        return seq

    def run(self, tripinfo_path: Path | None = None, verbose: bool = True) -> Dict[str, float]:
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

        for tl in self.tl_ids:
            self.prev_features[tl] = self._extract_phase_features(tl)

        while traci.simulation.getTime() < end_time:
            sim_t = int(traci.simulation.getTime()) - start_time

            if sim_t % self.delta_time == 0:
                for tl in self.tl_ids:
                    if not self.transition_queue[tl]:
                        feats = self._extract_phase_features(tl)
                        desired_idx = self._select_next_phase_idx(tl, feats)

                        # If training DQN from scratch, compute reward for the chosen action based on queue pressure
                        if self.train_mode:
                            chosen_f = feats[desired_idx]
                            # Reward choosing the phase that has higher queue, approaching flow, and wait time than its competitor
                            pressure_diff = (chosen_f[0] * 3.0 + chosen_f[1] * 1.5 + chosen_f[2] * 2.0) - (
                                chosen_f[3] * 2.5
                            )
                            # Small switching cost if changing phase unnecessarily when active queue is still high
                            switch_cost = -0.15 if desired_idx != self.current_action_idx[tl] else 0.05
                            r_tl = pressure_diff + switch_cost
                            self.agent.store_transition(feats, desired_idx, r_tl, feats, False)
                            loss = self.agent.update()
                            if loss > 0:
                                losses.append(loss)
                            ep_reward += r_tl

                        self.prev_features[tl] = feats

                        if desired_idx != self.current_action_idx[tl]:
                            self.transition_queue[tl] = self._build_transition_sequence(
                                tl, self.current_action_idx[tl], desired_idx
                            )
                            self.target_action_idx[tl] = desired_idx
                            if self.transition_queue[tl]:
                                first_p, _ = self.transition_queue[tl][0]
                                traci.trafficlight.setPhase(tl, first_p)
                                traci.trafficlight.setPhaseDuration(tl, 10000)

            traci.simulationStep()

            for tl in self.tl_ids:
                if self.transition_queue[tl]:
                    cur_p, rem_t = self.transition_queue[tl][0]
                    rem_t -= 1
                    if rem_t <= 0:
                        self.transition_queue[tl].pop(0)
                        if self.transition_queue[tl]:
                            next_p, _ = self.transition_queue[tl][0]
                            traci.trafficlight.setPhase(tl, next_p)
                            traci.trafficlight.setPhaseDuration(tl, 10000)
                        else:
                            self.current_action_idx[tl] = self.target_action_idx[tl]
                            self.elapsed_green[tl] = 0
                            green_p = self.tl_major_phases[tl][self.current_action_idx[tl]]
                            traci.trafficlight.setPhase(tl, green_p)
                            traci.trafficlight.setPhaseDuration(tl, 10000)
                    else:
                        self.transition_queue[tl][0] = (cur_p, rem_t)
                else:
                    self.elapsed_green[tl] += 1

            # Sample corridor queue and CO2 metrics every delta_time (5s)
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
                    per_tl_status.append(
                        f"{short_name}[AnaFaz-{self.current_action_idx[tl]} ({self.elapsed_green[tl]:2d}s) | Kuyruk:{halt:2d}]"
                    )

                history.append({"halting_total": total_halting, "co2_g": total_co2_mg / 1000.0})

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


def train_dqn_from_scratch(episodes: int = 6) -> DQNAgent:
    """
    Trains the Phase-Competition DQN Agent FROM SCRATCH (100% random He weights)
    on the real RESCO Cologne network and records the learning curve.
    """
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR = BASE_DIR / "models"
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    agent = DQNAgent(seed=42)
    best_wait = float("inf")
    training_rows = []

    print("========================================================================================")
    print(f"   GERCEK KOLN (RESCO COLOGNE-3) AGINDA SIFIRDAN (FROM-SCRATCH) DQN EGITIMI ({episodes} EPISODE)")
    print("========================================================================================")

    for ep in range(1, episodes + 1):
        t_path = RESULTS_DIR / f"train_c3_ep{ep}.tripinfo.xml"
        sim = RealNetworkSimulation(
            sumocfg_path=SUMOCFG_C3,
            mode="dqn",
            use_gui=False,
            seed=100 + ep * 13,
            sim_duration=1800,
            agent=agent,
            train_mode=True,
        )
        m = sim.run(tripinfo_path=t_path, verbose=False)
        if t_path.exists():
            t_path.unlink()

        if m["avg_waiting_time_s"] < best_wait:
            best_wait = m["avg_waiting_time_s"]
            agent.best_net.copy_from(agent.q_net)

        row = {
            "episode": ep,
            "epsilon": round(agent.epsilon, 3),
            "ep_reward": m["ep_reward"],
            "avg_waiting_time_s": m["avg_waiting_time_s"],
            "avg_corridor_queue_veh": m["avg_corridor_queue_veh"],
            "avg_loss": m["avg_loss"],
        }
        training_rows.append(row)
        print(
            f"  Episode {ep:02d}/{episodes} | Epsilon: {row['epsilon']:.3f} | "
            f"Ort. Bekleme: {row['avg_waiting_time_s']:6.2f} sn | "
            f"Ort. Kuyruk: {row['avg_corridor_queue_veh']:5.2f} arac | Loss: {row['avg_loss']:.4f}"
        )

    agent.q_net.copy_from(agent.best_net)
    agent.save(MODEL_PATH)

    train_csv = RESULTS_DIR / "training_log.csv"
    with train_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(training_rows[0].keys()))
        writer.writeheader()
        writer.writerows(training_rows)

    print(f"\n[OK] Sifirdan egitilen DQN modeli kaydedildi: {MODEL_PATH}\n")
    return agent


def run_benchmark_comparison():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    if not MODEL_PATH.exists():
        train_dqn_from_scratch(episodes=6)

    modes = [
        ("fixed", "1. Fixed-Time (Sabit Sureli Klasik)"),
        ("actuated", "2. Actuated (Klasik Sensorlu Gap-Out)"),
        ("dqn", "3. DQN RL (Sifirdan Egitilen Akilli Ajan)"),
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
            sim_duration=1800,
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
    print("----------------------------------------------------------------------------------------")
    for r in rows[1:]:
        imp = ((base_wait - r["avg_waiting_time_s"]) / base_wait) * 100.0
        print(f"  -> {r['label']} Sabit Isiga Gore Bekleme Suresini %{imp:.1f} Azaltti!")
    print("========================================================================================")

    csv_path = RESULTS_DIR / "cologne3_corridor_summary.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    arg = sys.argv[1].lower() if len(sys.argv) > 1 else "compare"
    if arg == "train":
        train_dqn_from_scratch(episodes=6)
        run_benchmark_comparison()
    elif arg in ("fixed", "actuated", "dqn"):
        if arg == "dqn" and not MODEL_PATH.exists():
            train_dqn_from_scratch(episodes=6)
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
        run_benchmark_comparison()
