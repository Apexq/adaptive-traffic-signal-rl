"""Shared, connection-owned SUMO engine (custom API, not a gymnasium.Env)."""
import math
from pathlib import Path
import uuid
import xml.etree.ElementTree as ET

from runtime import CONNECTION_LOCK, FEATURE_DIM, scenario_identity, sumo_binary
import traci
import traci.constants as tc


def yellow_state(source):
    """Clear every served movement before an arbitrary target green."""
    return "".join("y" if ch in "gG" else "r" for ch in source)


class TrafficSimulation:
    def __init__(self, sumocfg_path, use_gui=False, seed=42, sim_duration=3600,
                 delta_time=5, yellow_time=3, all_red_time=1,
                 min_green_major=10, min_green_turn=4,
                 max_green_major=45, max_green_turn=10):
        self.sumocfg_path = Path(sumocfg_path).resolve()
        self.use_gui, self.seed = use_gui, seed
        self.sim_duration, self.delta_time = float(sim_duration), float(delta_time)
        self.yellow_time, self.all_red_time = float(yellow_time), float(all_red_time)
        self.min_green_major, self.min_green_turn = min_green_major, min_green_turn
        self.max_green_major, self.max_green_turn = max_green_major, max_green_turn
        values = (sim_duration, delta_time, yellow_time, all_red_time,
                  min_green_major, min_green_turn, max_green_major, max_green_turn)
        if any(not math.isfinite(v) or v <= 0 for v in values):
            raise ValueError("Simulation durations must be finite and positive")
        if min_green_major > max_green_major or min_green_turn > max_green_turn:
            raise ValueError("Minimum green exceeds maximum green")
        self.conn = None
        self.label = uuid.uuid4().hex
        self.audit = []  # optional bounded diagnostic trace; disabled by default
        self.audit_limit = 0
        self.topology = {}
        self.state = {}
        self.tripinfo_path = None
        self.identity = scenario_identity(self.sumocfg_path)
        self.identity["control"] = dict(zip(
            ("duration", "interval", "yellow", "all_red", "min_major", "min_turn", "max_major", "max_turn"),
            map(float, values),
        ))

    def reset(self, seed=None, tripinfo_path=None):
        self.close()
        if seed is not None:
            self.seed = seed
        self.tripinfo_path = Path(tripinfo_path) if tripinfo_path else None
        cmd = [sumo_binary("sumo-gui" if self.use_gui else "sumo"),
               "-c", str(self.sumocfg_path), "--seed", str(self.seed),
               "--no-step-log", "true", "--time-to-teleport", "-1"]
        if self.tripinfo_path:
            self.tripinfo_path.parent.mkdir(parents=True, exist_ok=True)
            cmd += ["--tripinfo-output", str(self.tripinfo_path),
                    "--tripinfo-output.write-unfinished", "true",
                    "--tripinfo-output.write-undeparted", "true"]
        try:
            with CONNECTION_LOCK:
                traci.start(cmd, label=self.label, doSwitch=False)
                self.conn = traci.getConnection(self.label)
            self.start_time = self.conn.simulation.getTime()
            self.end_time = self.start_time + self.sim_duration
            self.dt = self.conn.simulation.getDeltaT()
            # Timers cannot honor a deadline between simulation ticks.
            for value in self.identity["control"].values():
                if not math.isclose(value / self.dt, round(value / self.dt), abs_tol=1e-8):
                    raise ValueError("Control durations must be multiples of SUMO step-length")
            self.topology, self.state, self.audit = {}, {}, []
            self._discover()
            self.tl_ids = list(self.topology)
            if not self.tl_ids:
                raise ValueError("No controllable traffic lights in this scenario")
            self.lanes = sorted({l for top in self.topology.values() for l in top["lanes"]})
            self.network_lanes = self.conn.lane.getIDList()
            self._movement_cache = {}
            for lane in self.network_lanes:
                self.conn.lane.subscribe(lane, (tc.VAR_CO2EMISSION, tc.LAST_STEP_VEHICLE_HALTING_NUMBER))
            self.stats = dict(queue_vehicle_seconds=0.0, pending_vehicle_seconds=0.0,
                              total_co2_kg=0.0, incoming_co2_kg=0.0, max_queue_length_veh=0,
                              departed_vehicles=0, completed_trips=0, teleports=0, collisions=0)
            self.terminated = self.truncated = False
            self.last_queues = {tl: 0 for tl in self.tl_ids}
            return {tl: self.observe(tl) for tl in self.tl_ids}
        except BaseException:
            self.close()
            raise

    def _discover(self):
        for tl in self.conn.trafficlight.getIDList():
            program = self.conn.trafficlight.getProgram(tl)
            logic = next(p for p in self.conn.trafficlight.getAllProgramLogics(tl) if p.programID == program)
            links = self.conn.trafficlight.getControlledLinks(tl)
            phases, lanes = [], set()
            for index, phase in enumerate(logic.phases):
                if "g" not in phase.state.lower() or "y" in phase.state.lower():
                    continue
                turn = phase.duration <= 10
                allowed = {i for i, ch in enumerate(phase.state) if ch in ("G" if turn else "Gg")}
                phase_lanes = {link[0] for i in allowed for link in links[i]}
                lanes.update(link[0] for group in links for link in group)
                successor = logic.phases[(index + 1) % len(logic.phases)]
                clearance = max(self.yellow_time, successor.duration if "y" in successor.state.lower() else 0)
                if not math.isclose(clearance / self.dt, round(clearance / self.dt), abs_tol=1e-8):
                    raise ValueError("Network yellow duration not aligned with simulation step")
                phases.append(dict(index=index, signal=phase.state, turn=turn,
                                   links=allowed, lanes=sorted(phase_lanes), yellow=clearance))
            if len(phases) < 2:
                raise ValueError(f"{tl}: at least two green phases required")
            self.topology[tl] = dict(phases=phases, lanes=sorted(lanes), links=links)
            self.state[tl] = dict(active=0, target=0, elapsed=0.0, stage="green",
                                  remaining=0.0, since_decision=self.delta_time)
            self.conn.trafficlight.setRedYellowGreenState(tl, phases[0]["signal"])

    def bounds(self, tl):
        phase = self.topology[tl]["phases"][self.state[tl]["active"]]
        return ((self.min_green_turn, self.max_green_turn) if phase["turn"]
                else (self.min_green_major, self.max_green_major))

    def movement_counts(self, tl):
        # Actions do not change the vehicle snapshot until simulationStep().
        if not hasattr(self, "_movement_cache"):
            self._movement_cache = {}
        if tl in self._movement_cache:
            return self._movement_cache[tl]
        top = self.topology[tl]
        vehicles = {}
        for lane in top["lanes"]:
            for vid in self.conn.lane.getLastStepVehicleIDs(lane):
                next_tls = self.conn.vehicle.getNextTLS(vid)
                if next_tls and next_tls[0][0] == tl:
                    vehicles[vid] = (next_tls[0][1], self.conn.vehicle.getSpeed(vid),
                                     self.conn.vehicle.getWaitingTime(vid))
        counts = [
            (sum(speed < 0.1 for link, speed, wait in vehicles.values() if link in p["links"]),
             sum(link in p["links"] for link, speed, wait in vehicles.values()),
             sum(wait for link, speed, wait in vehicles.values() if link in p["links"]))
            for p in top["phases"]
        ]
        self._movement_cache[tl] = counts
        return counts

    def observe(self, tl, demand_mask=True):
        top, state = self.topology[tl], self.state[tl]
        counts = self.movement_counts(tl)
        queues = [q / (8.0 * max(1, len(p["lanes"]))) for p, (q, v, w) in zip(top["phases"], counts)]
        active = state["active"] if state["stage"] == "green" else state["target"]
        clock = state["elapsed"] if state["stage"] == "green" else -(
            state["remaining"] + (self.all_red_time if state["stage"] == "yellow" else 0)
        )
        features, demand = [], []
        for i, (p, (q, v, w)) in enumerate(zip(top["phases"], counts)):
            n = max(1, len(p["lanes"]))
            features.append([queues[i], v / (12.0 * n), min(1.0, w / (150.0 * n)),
                             max((x for j, x in enumerate(queues) if i != j), default=0.0),
                             float(i == active), float(not p["turn"]),
                             clock / self.max_green_major if i == active else 0.0])
            demand.append(not p["turn"] or q >= 2 or w >= 25)
        if not demand_mask:
            demand = [True] * len(features)
        if state["stage"] != "green" or state["elapsed"] < self.bounds(tl)[0] - 1e-9:
            mask = [i == active for i in range(len(features))]
        elif state["elapsed"] >= self.bounds(tl)[1] - 1e-9:
            mask = [ok and i != active for i, ok in enumerate(demand)]
            if not any(mask):
                mask = [i != active for i in range(len(features))]
        else:
            mask = demand
            mask[active] = True
        return features, mask

    def ready(self, tl):
        state = self.state[tl]
        baseline = getattr(self, "baseline_mode", None)
        turn = self.topology[tl]["phases"][state["active"]]["turn"]
        deadline = (8 if turn else 42) if baseline == "fixed" else ((8 if turn else 38) if baseline == "actuated" else self.bounds(tl)[1])
        return state["stage"] == "green" and (
            state["since_decision"] >= self.delta_time - 1e-9
            or state["elapsed"] >= min(deadline, self.bounds(tl)[1]) - 1e-9
        )

    def apply(self, tl, action, demand_mask=True):
        if self.terminated or self.truncated:
            raise RuntimeError("Episode finished; reset before stepping")
        if not self.ready(tl):
            raise RuntimeError("Traffic light is not at a decision boundary")
        _, mask = self.observe(tl, demand_mask=demand_mask)
        if type(action) is not int or not 0 <= action < len(mask) or not mask[action]:
            raise ValueError(f"Illegal action {action} for {tl}")
        state = self.state[tl]
        state["since_decision"] = 0.0
        if action != state["active"]:
            phase = self.topology[tl]["phases"][state["active"]]
            self.conn.trafficlight.setRedYellowGreenState(tl, yellow_state(phase["signal"]))
            state.update(target=action, stage="yellow", remaining=phase["yellow"])

    def tick(self):
        if self.terminated or self.truncated:
            raise RuntimeError("Episode finished")
        if any(s["stage"] == "green" and s["elapsed"] >= self.bounds(tl)[1] - 1e-9
               for tl, s in self.state.items()):
            raise RuntimeError("A legal phase change is required at the maximum-green deadline")
        if self.audit_limit and len(self.audit) < self.audit_limit:
            self.audit.append((self.conn.simulation.getTime(), {
                tl: {**state, "signal": self.conn.trafficlight.getRedYellowGreenState(tl)}
                for tl, state in self.state.items()
            }))
        self.conn.simulationStep()
        self._movement_cache = {}
        for tl, state in self.state.items():
            state["since_decision"] += self.dt
            if state["stage"] == "green":
                state["elapsed"] += self.dt
            else:
                state["remaining"] -= self.dt
                if state["remaining"] <= 1e-9:
                    if state["stage"] == "yellow":
                        state.update(stage="all_red", remaining=self.all_red_time)
                        signal = "r" * len(self.topology[tl]["phases"][0]["signal"])
                    else:
                        state.update(stage="green", active=state["target"], elapsed=0.0)
                        signal = self.topology[tl]["phases"][state["active"]]["signal"]
                    self.conn.trafficlight.setRedYellowGreenState(tl, signal)
        lane_values = self.conn.lane.getAllSubscriptionResults()
        halting = {l: lane_values[l][tc.LAST_STEP_VEHICLE_HALTING_NUMBER] for l in self.lanes}
        self.last_queues = {tl: sum(halting[l] for l in top["lanes"])
                            for tl, top in self.topology.items()}
        queue = sum(halting.values())
        self.stats["queue_vehicle_seconds"] += queue * self.dt
        self.stats["pending_vehicle_seconds"] += len(self.conn.simulation.getPendingVehicles()) * self.dt
        self.stats["max_queue_length_veh"] = max(self.stats["max_queue_length_veh"], queue)
        emissions = {l: lane_values[l][tc.VAR_CO2EMISSION] for l in self.network_lanes}
        self.stats["total_co2_kg"] += sum(emissions.values()) * self.dt / 1e6
        self.stats["incoming_co2_kg"] += sum(emissions[l] for l in self.lanes) * self.dt / 1e6
        for name, value in (
            ("departed_vehicles", self.conn.simulation.getDepartedNumber()),
            ("completed_trips", self.conn.simulation.getArrivedNumber()),
            ("teleports", self.conn.simulation.getStartingTeleportNumber()),
            ("collisions", self.conn.simulation.getCollidingVehiclesNumber()),
        ):
            self.stats[name] += value
        self.terminated = self.conn.simulation.getMinExpectedNumber() == 0
        self.truncated = not self.terminated and self.conn.simulation.getTime() >= self.end_time - 1e-9
        return self.terminated, self.truncated

    def metrics(self):
        elapsed = self.conn.simulation.getTime() - self.start_time
        return {**self.stats, "simulated_seconds": elapsed,
                "remaining_vehicles": self.conn.vehicle.getIDCount(),
                "pending_vehicles": len(self.conn.simulation.getPendingVehicles()),
                "avg_corridor_queue_veh": self.stats["queue_vehicle_seconds"] / max(elapsed, self.dt),
                "selection_cost": self.stats["queue_vehicle_seconds"] + self.stats["pending_vehicle_seconds"],
                "terminated": self.terminated, "truncated": self.truncated}

    def close(self):
        if self.conn is not None:
            connection, self.conn = self.conn, None
            with CONNECTION_LOCK:
                connection.close()


def tripinfo_metrics(path):
    trips = ET.parse(path).getroot().findall("tripinfo")
    departed = [t for t in trips if float(t.get("depart", -1)) >= 0]
    completed = [t for t in departed if float(t.get("arrival", -1)) >= 0]
    def average(rows, key):
        return sum(float(t.get(key, 0)) for t in rows) / len(rows) if rows else None
    return {"completed_trips": len(completed), "unfinished_trips": len(departed) - len(completed),
            "undeparted_trips": len(trips) - len(departed),
            "observed_avg_waiting_time_s": average(departed, "waitingTime"),
            "completed_avg_waiting_time_s": average(completed, "waitingTime"),
            "completed_avg_time_loss_s": average(completed, "timeLoss"),
            "completed_avg_travel_time_s": average(completed, "duration")}


class SumoTrafficEnv:
    """Single-TLS custom five-return API sharing the corridor state machine.

    Observations are K x 7 phase features; info['action_mask'] defines legal actions.
    This class deliberately does not claim gymnasium.Env/SB3 compatibility.
    """
    def __init__(self, sumocfg_path, tl_id=None, use_gui=False, delta_time=5,
                 yellow_time=3, min_green=10, max_green=45, sim_Compare_end=1800,
                 seed=42, tripinfo_file=None):
        self.engine = TrafficSimulation(sumocfg_path, use_gui, seed, sim_Compare_end,
                                        delta_time, yellow_time,
                                        min_green_major=min_green, max_green_major=max_green)
        self.tl_id, self.tripinfo_file = tl_id, tripinfo_file
        self.gamma = 0.88

    def reset(self, seed=None, options=None):
        observations = self.engine.reset(seed, self.tripinfo_file)
        try:
            if len(observations) != 1:
                raise ValueError("SumoTrafficEnv requires exactly one traffic light")
            discovered = next(iter(observations))
            if self.tl_id is not None and self.tl_id != discovered:
                raise ValueError("Configured traffic light not present")
            self.tl_id = discovered
            features, mask = observations[self.tl_id]
            return features, {"action_mask": mask}
        except BaseException:
            self.close()
            raise

    def step(self, action):
        try:
            demand_mask = getattr(self.engine, "baseline_mode", None) not in ("fixed", "actuated", "maxpressure")
            self.engine.apply(self.tl_id, action, demand_mask=demand_mask)
            reward, duration = 0.0, 0.0
            while True:
                terminated, truncated = self.engine.tick()
                n = max(1, len(self.engine.topology[self.tl_id]["lanes"]))
                reward -= self.gamma ** (duration / 5) * self.engine.last_queues[self.tl_id] * self.engine.dt / (8 * n * 5)
                duration += self.engine.dt
                if terminated or truncated or self.engine.ready(self.tl_id):
                    features, mask = self.engine.observe(self.tl_id, demand_mask=demand_mask)
                    return features, reward, terminated, truncated, {"action_mask": mask, "duration": duration}
        except BaseException:
            self.close()
            raise

    def close(self):
        self.engine.close()
