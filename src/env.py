"""
SUMO Traffic Signal Control Environment (Gymnasium-style interface via TraCI)
Provides state extraction, yellow-phase transition enforcement, reward computation,
and comprehensive KPI logging (Waiting Time, Queue Length, Travel Time, CO2 Emissions).
"""

import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Ensure SUMO tools are on sys.path
SUMO_HOME = os.environ.get("SUMO_HOME", r"C:\Program Files (x86)\SUMO")
SUMO_TOOLS = os.path.join(SUMO_HOME, "tools")
if SUMO_TOOLS not in sys.path:
    sys.path.append(SUMO_TOOLS)

import traci


class SumoTrafficEnv:
    """
    Microscopic Traffic Signal Control Environment built on Eclipse SUMO + TraCI.
    """

    def __init__(
        self,
        sumocfg_path: str | Path,
        tl_id: str = "TL_C1",
        use_gui: bool = False,
        delta_time: int = 5,
        yellow_time: int = 3,
        min_green: int = 10,
        max_green: int = 60,
        sim_Compare_end: int = 1800,
        seed: int = 42,
        tripinfo_file: Optional[str] = None,
    ):
        self.sumocfg_path = Path(sumocfg_path).resolve()
        self.tl_id = tl_id
        self.use_gui = use_gui
        self.delta_time = delta_time
        self.yellow_time = yellow_time
        self.min_green = min_green
        self.max_green = max_green
        self.sim_end = sim_Compare_end
        self.seed = seed
        self.tripinfo_file = tripinfo_file

        # Approach edges and their corresponding green phase indices in SUMO default 4-phase logic:
        # Phase 0: N-S Green (GGGgrrrrGGGgrrrr...)
        # Phase 1: N-S Yellow
        # Phase 2: E-W Green (rrrrGGGgrrrrGGGg...)
        # Phase 3: E-W Yellow
        self.approaches = {
            "NS": ["N2C_0", "N2C_1", "N2C_2", "S2C_0", "S2C_1", "S2C_2"],
            "EW": ["E2C_0", "E2C_1", "E2C_2", "W2C_0", "W2C_1", "W2C_2"],
        }
        self.outgoing = {
            "NS": ["C2N_0", "C2N_1", "C2N_2", "C2S_0", "C2S_1", "C2S_2"],
            "EW": ["C2E_0", "C2E_1", "C2E_2", "C2W_0", "C2W_1", "C2W_2"],
        }
        # Action 0 -> Green for N-S (SUMO phase 0)
        # Action 1 -> Green for E-W (SUMO phase 2)
        self.action_to_sumo_phase = {0: 0, 1: 2}
        self.current_action = 0
        self.elapsed_green = 0
        self.step_count = 0
        self.history: List[Dict[str, float]] = []

    def reset(self, seed: Optional[int] = None) -> Tuple[List[float], Dict]:
        if seed is not None:
            self.seed = seed

        try:
            traci.close()
        except Exception:
            pass

        sumo_binary = os.path.join(
            SUMO_HOME, "bin", "sumo-gui.exe" if self.use_gui else "sumo.exe"
        )
        cmd = [
            sumo_binary,
            "-c",
            str(self.sumocfg_path),
            "--seed",
            str(self.seed),
            "--no-warnings",
            "true",
            "--no-step-log",
            "true",
        ]
        if self.tripinfo_file:
            cmd.extend(["--tripinfo-output", str(self.tripinfo_file)])

        traci.start(cmd)
        self.current_action = 0
        self.elapsed_green = 0
        self.step_count = 0
        self.history = []

        traci.trafficlight.setPhase(self.tl_id, self.action_to_sumo_phase[self.current_action])
        traci.trafficlight.setPhaseDuration(self.tl_id, 10000)

        return self._get_observation(), {}

    def _sim_step(self, num_steps: int = 1):
        for _ in range(num_steps):
            if traci.simulation.getTime() >= self.sim_end:
                break
            traci.simulationStep()
            self.step_count += 1
            self.elapsed_green += 1
            self._record_step_metrics()

    def _record_step_metrics(self):
        all_lanes = self.approaches["NS"] + self.approaches["EW"]
        halting = sum(traci.lane.getLastStepHaltingNumber(l) for l in all_lanes)
        waiting = sum(traci.lane.getWaitingTime(l) for l in all_lanes)
        co2_mg = sum(traci.lane.getCO2Emission(l) for l in all_lanes)
        ns_q = sum(traci.lane.getLastStepHaltingNumber(l) for l in self.approaches["NS"])
        ew_q = sum(traci.lane.getLastStepHaltingNumber(l) for l in self.approaches["EW"])

        self.history.append(
            {
                "time": traci.simulation.getTime(),
                "halting_total": halting,
                "waiting_total": waiting,
                "ns_queue": ns_q,
                "ew_queue": ew_q,
                "co2_g": co2_mg / 1000.0,
                "active_action": self.current_action,
            }
        )

    def get_approach_queues(self) -> Dict[str, int]:
        ns_q = sum(traci.lane.getLastStepHaltingNumber(l) for l in self.approaches["NS"])
        ew_q = sum(traci.lane.getLastStepHaltingNumber(l) for l in self.approaches["EW"])
        return {"NS": ns_q, "EW": ew_q}

    def get_approach_pressures(self) -> Dict[str, float]:
        """Computes Max-Pressure metric (incoming queue + approaching density minus outgoing density)."""
        ns_in = sum(
            traci.lane.getLastStepHaltingNumber(l) * 1.5 + traci.lane.getLastStepVehicleNumber(l) * 0.5
            for l in self.approaches["NS"]
        )
        ns_out = sum(traci.lane.getLastStepVehicleNumber(l) * 0.2 for l in self.outgoing["NS"])

        ew_in = sum(
            traci.lane.getLastStepHaltingNumber(l) * 1.5 + traci.lane.getLastStepVehicleNumber(l) * 0.5
            for l in self.approaches["EW"]
        )
        ew_out = sum(traci.lane.getLastStepVehicleNumber(l) * 0.2 for l in self.outgoing["EW"])

        return {"NS": max(0.0, ns_in - ns_out), "EW": max(0.0, ew_in - ew_out)}

    def _get_observation(self) -> List[float]:
        """
        Returns 8-dimensional state vector:
        [ns_queue_norm, ew_queue_norm, ns_veh_norm, ew_veh_norm,
         ns_wait_norm, ew_wait_norm, current_action, min_green_satisfied]
        """
        ns_q = sum(traci.lane.getLastStepHaltingNumber(l) for l in self.approaches["NS"]) / 60.0
        ew_q = sum(traci.lane.getLastStepHaltingNumber(l) for l in self.approaches["EW"]) / 60.0
        ns_v = sum(traci.lane.getLastStepVehicleNumber(l) for l in self.approaches["NS"]) / 80.0
        ew_v = sum(traci.lane.getLastStepVehicleNumber(l) for l in self.approaches["EW"]) / 80.0
        ns_w = min(1.0, sum(traci.lane.getWaitingTime(l) for l in self.approaches["NS"]) / 1000.0)
        ew_w = min(1.0, sum(traci.lane.getWaitingTime(l) for l in self.approaches["EW"]) / 1000.0)
        min_g = 1.0 if self.elapsed_green >= self.min_green else 0.0
        return [ns_q, ew_q, ns_v, ew_v, ns_w, ew_w, float(self.current_action), min_g]

    def step(self, action: int) -> Tuple[List[float], float, bool, Dict]:
        """Executes action (0: NS Green, 1: EW Green) enforcing min_green, max_green, and yellow transitions."""
        # Enforce min_green and max_green constraints
        if action != self.current_action and self.elapsed_green < self.min_green:
            action = self.current_action
        elif action == self.current_action and self.elapsed_green >= self.max_green:
            # Force switch if conflicting direction has waiting vehicles
            queues = self.get_approach_queues()
            other_key = "EW" if self.current_action == 0 else "NS"
            if queues[other_key] > 0:
                action = 1 - self.current_action

        # Transition via yellow phase if action changed
        if action != self.current_action:
            yellow_phase = self.action_to_sumo_phase[self.current_action] + 1
            traci.trafficlight.setPhase(self.tl_id, yellow_phase)
            self._sim_step(self.yellow_time)
            self.current_action = action
            self.elapsed_green = 0
            traci.trafficlight.setPhase(self.tl_id, self.action_to_sumo_phase[self.current_action])
            traci.trafficlight.setPhaseDuration(self.tl_id, 10000)

        # Advance simulation by delta_time
        self._sim_step(self.delta_time)

        obs = self._get_observation()
        all_lanes = self.approaches["NS"] + self.approaches["EW"]
        halting = sum(traci.lane.getLastStepHaltingNumber(l) for l in all_lanes)
        waiting = sum(traci.lane.getWaitingTime(l) for l in all_lanes)
        reward = -(halting + 0.05 * waiting)

        done = traci.simulation.getTime() >= self.sim_end
        return obs, reward, done, {}

    def close(self):
        try:
            traci.close()
        except Exception:
            pass

    @staticmethod
    def parse_tripinfo_metrics(tripinfo_path: str | Path, history: List[Dict[str, float]]) -> Dict[str, float]:
        """Parses SUMO tripinfo.xml and step history into aggregate KPIs."""
        tree = ET.parse(tripinfo_path)
        root = tree.getroot()
        trips = root.findall("tripinfo")
        n = max(1, len(trips))
        avg_wait = sum(float(t.attrib.get("waitingTime", 0.0)) for t in trips) / n
        avg_timeloss = sum(float(t.attrib.get("timeLoss", 0.0)) for t in trips) / n
        avg_duration = sum(float(t.attrib.get("duration", 0.0)) for t in trips) / n

        avg_queue = sum(h["halting_total"] for h in history) / max(1, len(history))
        max_queue = max((h["halting_total"] for h in history), default=0.0)
        total_co2_kg = sum(h["co2_g"] for h in history) / 1000.0

        return {
            "completed_trips": len(trips),
            "avg_waiting_time_s": round(avg_wait, 2),
            "avg_time_loss_s": round(avg_timeloss, 2),
            "avg_travel_time_s": round(avg_duration, 2),
            "avg_queue_length_veh": round(avg_queue, 2),
            "max_queue_length_veh": round(max_queue, 2),
            "total_co2_kg": round(total_co2_kg, 2),
        }
