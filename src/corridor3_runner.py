"""
Multi-Intersection Corridor Runner & Benchmark (Cologne-3: 3 Intersections TL_1, TL_2, TL_3)
Supports both:
  1. Live Visual SUMO-GUI mode with real-time console telemetry for all 3 intersections
  2. Headless benchmark comparison mode across Fixed-Time, Actuated, and DQN/Adaptive RL
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
MODEL_PATH = BASE_DIR / "models" / "dqn_cologne1.json"
RESULTS_DIR = BASE_DIR / "results"

# Approach lane mappings for each of the 3 intersections in Cologne-3
INTERSECTIONS = {
    "TL_1": {
        "name": "Kavsak-1 (Bati)",
        "NS": ["N12J1_0", "N12J1_1", "S12J1_0", "S12J1_1"],
        "EW": ["W2J1_0", "W2J1_1", "J22J1_0", "J22J1_1"],
    },
    "TL_2": {
        "name": "Kavsak-2 (Merkez)",
        "NS": ["N22J2_0", "N22J2_1", "S22J2_0", "S22J2_1"],
        "EW": ["J12J2_0", "J12J2_1", "J32J2_0", "J32J2_1"],
    },
    "TL_3": {
        "name": "Kavsak-3 (Dogu)",
        "NS": ["N32J3_0", "N32J3_1", "S32J3_0", "S32J3_1"],
        "EW": ["J22J3_0", "J22J3_1", "E2J3_0", "E2J3_1"],
    },
}


class Corridor3Simulation:
    """Manages simultaneous control of TL_1, TL_2, and TL_3 in the 3-intersection corridor."""

    def __init__(self, mode: str = "dqn", use_gui: bool = True, seed: int = 42, sim_end: int = 1800):
        self.mode = mode.lower()
        self.use_gui = use_gui
        self.seed = seed
        self.sim_end = sim_end
        self.min_green = 10
        self.max_green = 55
        self.yellow_time = 3
        self.delta_time = 5

        self.agent = DQNAgent()
        if MODEL_PATH.exists():
            self.agent.load(MODEL_PATH)

        # Per-intersection state tracking:
        # In cologne3.net.xml:
        #   action 0 = NS Green -> SUMO phase 2 (yellow = phase 3)
        #   action 1 = EW Green -> SUMO phase 0 (yellow = phase 1)
        self.action_to_phase = {0: 2, 1: 0}
        self.current_action = {"TL_1": 1, "TL_2": 1, "TL_3": 1}
        self.elapsed_green = {"TL_1": 0, "TL_2": 0, "TL_3": 0}
        self.pending_yellow = {"TL_1": 0, "TL_2": 0, "TL_3": 0}
        self.target_action = {"TL_1": 1, "TL_2": 1, "TL_3": 1}

    def _get_tl_state(self, tl_id: str) -> List[float]:
        cfg = INTERSECTIONS[tl_id]
        ns_q = sum(traci.lane.getLastStepHaltingNumber(l) for l in cfg["NS"]) / 40.0
        ew_q = sum(traci.lane.getLastStepHaltingNumber(l) for l in cfg["EW"]) / 40.0
        ns_v = sum(traci.lane.getLastStepVehicleNumber(l) for l in cfg["NS"]) / 60.0
        ew_v = sum(traci.lane.getLastStepVehicleNumber(l) for l in cfg["EW"]) / 60.0
        ns_w = min(1.0, sum(traci.lane.getWaitingTime(l) for l in cfg["NS"]) / 800.0)
        ew_w = min(1.0, sum(traci.lane.getWaitingTime(l) for l in cfg["EW"]) / 800.0)
        cur_a = float(self.current_action[tl_id])
        min_g = 1.0 if self.elapsed_green[tl_id] >= self.min_green else 0.0
        return [ns_q, ew_q, ns_v, ew_v, ns_w, ew_w, cur_a, min_g]

    def _decide_action(self, tl_id: str) -> int:
        cur = self.current_action[tl_id]
        elapsed = self.elapsed_green[tl_id]
        cfg = INTERSECTIONS[tl_id]
        ns_q = sum(traci.lane.getLastStepHaltingNumber(l) for l in cfg["NS"])
        ew_q = sum(traci.lane.getLastStepVehicleNumber(l) for l in cfg["EW"])
        ew_halt = sum(traci.lane.getLastStepHaltingNumber(l) for l in cfg["EW"])

        if elapsed < self.min_green:
            return cur

        if self.mode == "fixed":
            # Classic Fixed-Time: blindly switches every 40 seconds
            return 1 - cur if elapsed >= 40 else cur

        elif self.mode == "actuated":
            # Classic Sensor-Actuated (Gap-out threshold = 2 vehicles, max_green = 45s)
            active_q = ns_q if cur == 0 else ew_halt
            other_q = ew_halt if cur == 0 else ns_q
            if active_q <= 2 and other_q > 2:
                return 1 - cur
            if elapsed >= 45 and other_q > 0:
                return 1 - cur
            return cur

        else:
            # Proposed DQN / Adaptive Pressure Controller
            if elapsed >= self.max_green:
                other_q = ew_halt if cur == 0 else ns_q
                if other_q > 0:
                    return 1 - cur
            state = self._get_tl_state(tl_id)
            return self.agent.select_action(state, evaluate=True)

    def run(self, tripinfo_path: Path | None = None, verbose: bool = True) -> Dict[str, float]:
        try:
            traci.close()
        except Exception:
            pass

        sumo_bin = os.path.join(SUMO_HOME, "bin", "sumo-gui.exe" if self.use_gui else "sumo.exe")
        cmd = [
            sumo_bin,
            "-c",
            str(SUMOCFG_C3),
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

        for tl_id in INTERSECTIONS:
            self.current_action[tl_id] = 1
            self.elapsed_green[tl_id] = 0
            self.pending_yellow[tl_id] = 0
            traci.trafficlight.setPhase(tl_id, self.action_to_phase[1])
            traci.trafficlight.setPhaseDuration(tl_id, 10000)

        history = []

        while traci.simulation.getTime() < self.sim_end:
            sim_t = int(traci.simulation.getTime())

            # Every 5 seconds, evaluate controller decisions for all 3 intersections
            if sim_t % self.delta_time == 0:
                for tl_id in INTERSECTIONS:
                    if self.pending_yellow[tl_id] == 0:
                        desired = self._decide_action(tl_id)
                        if desired != self.current_action[tl_id]:
                            # Trigger 3-second Yellow Phase
                            yellow_phase = self.action_to_phase[self.current_action[tl_id]] + 1
                            traci.trafficlight.setPhase(tl_id, yellow_phase)
                            self.pending_yellow[tl_id] = self.yellow_time
                            self.target_action[tl_id] = desired

            traci.simulationStep()

            # Update yellow timers and elapsed green counters
            total_halting = 0
            total_co2_mg = 0.0
            per_tl_info = []

            for tl_id, cfg in INTERSECTIONS.items():
                if self.pending_yellow[tl_id] > 0:
                    self.pending_yellow[tl_id] -= 1
                    if self.pending_yellow[tl_id] == 0:
                        self.current_action[tl_id] = self.target_action[tl_id]
                        self.elapsed_green[tl_id] = 0
                        green_phase = self.action_to_phase[self.current_action[tl_id]]
                        traci.trafficlight.setPhase(tl_id, green_phase)
                        traci.trafficlight.setPhaseDuration(tl_id, 10000)
                else:
                    self.elapsed_green[tl_id] += 1

                ns_q = sum(traci.lane.getLastStepHaltingNumber(l) for l in cfg["NS"])
                ew_q = sum(traci.lane.getLastStepHaltingNumber(l) for l in cfg["EW"])
                lanes = cfg["NS"] + cfg["EW"]
                total_halting += ns_q + ew_q
                total_co2_mg += sum(traci.lane.getCO2Emission(l) for l in lanes)
                phase_str = "KG-YESIL" if self.current_action[tl_id] == 0 else "DB-YESIL"
                per_tl_info.append(f"{tl_id}[{phase_str} {self.elapsed_green[tl_id]:2d}s | Kuyruk KG:{ns_q:2d} DB:{ew_q:2d}]")

            history.append({"halting_total": total_halting, "co2_g": total_co2_mg / 1000.0})

            if verbose and self.use_gui and int(traci.simulation.getTime()) % 10 == 0:
                t_now = int(traci.simulation.getTime())
                regime = (
                    "Rejim-1 (Dogu-Bati Ana Koridor Yogun)"
                    if t_now < 600
                    else ("Rejim-2 (Kuzey-Guney Yan Caddeler Yogun)" if t_now < 1200 else "Rejim-3 (Tum Yonler Zirve Saat)")
                )
                print(
                    f"[t={t_now:4d}s | Mod: {self.mode.upper():8s} | {regime}]\n"
                    f"   " + "  ||  ".join(per_tl_info) + f"  => Toplam Kuyruk: {total_halting:3d} arac"
                )

        traci.close()

        if tripinfo_path and tripinfo_path.exists():
            tree = ET.parse(tripinfo_path)
            trips = tree.getroot().findall("tripinfo")
            n = max(1, len(trips))
            avg_wait = sum(float(t.attrib.get("waitingTime", 0.0)) for t in trips) / n
            avg_loss = sum(float(t.attrib.get("timeLoss", 0.0)) for t in trips) / n
            avg_dur = sum(float(t.attrib.get("duration", 0.0)) for t in trips) / n
            avg_q = sum(h["halting_total"] for h in history) / max(1, len(history))
            co2_kg = sum(h["co2_g"] for h in history) / 1000.0
            return {
                "mode": self.mode,
                "completed_trips": len(trips),
                "avg_waiting_time_s": round(avg_wait, 2),
                "avg_time_loss_s": round(avg_loss, 2),
                "avg_travel_time_s": round(avg_dur, 2),
                "avg_corridor_queue_veh": round(avg_q, 2),
                "total_co2_kg": round(co2_kg, 2),
            }
        return {}


def run_benchmark_comparison():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    modes = [
        ("fixed", "1. Fixed-Time (Sabit Sureli)"),
        ("actuated", "2. Actuated (Klasik Sensorlu)"),
        ("dqn", "3. DQN RL (Akilli Adaptif - Onerilen)"),
    ]
    rows = []
    print("========================================================================================")
    print("   COLOGNE-3 (3 ARDISIK KAVSAKLI KORIDOR) - 3 FARKLI DURUM KARSILASTIRMA TESTI")
    print("========================================================================================")
    for code, label in modes:
        t_path = RESULTS_DIR / f"c3_{code}.tripinfo.xml"
        sim = Corridor3Simulation(mode=code, use_gui=False, seed=42)
        metrics = sim.run(tripinfo_path=t_path, verbose=False)
        if t_path.exists():
            t_path.unlink()
        metrics["label"] = label
        rows.append(metrics)
        print(
            f"  {label:38s} | Ort. Bekleme: {metrics['avg_waiting_time_s']:6.2f} sn | "
            f"Koridor Kuyrugu: {metrics['avg_corridor_queue_veh']:5.2f} arac | "
            f"Seyahat Suresi: {metrics['avg_travel_time_s']:6.2f} sn | CO2: {metrics['total_co2_kg']:6.2f} kg"
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
    if arg in ("fixed", "actuated", "dqn"):
        sim = Corridor3Simulation(mode=arg, use_gui=True, seed=42)
        sim.run(verbose=True)
    else:
        run_benchmark_comparison()
