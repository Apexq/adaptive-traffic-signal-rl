"""Real SUMO integration tests. Opt in with RUN_SUMO_TESTS=1."""
import math
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from env import TrafficSimulation, SumoTrafficEnv, yellow_state, tripinfo_metrics
from corridor3_runner import RealNetworkSimulation, train_dqn_checkpointed, improvement_pct
from rl_agent import DQNAgent
from runtime import FEATURE_DIM

ROOT = Path(__file__).resolve().parents[1]
C1 = ROOT / "nets/cologne1/cologne1.sumocfg"
C3 = ROOT / "nets/cologne3/cologne3.sumocfg"


class LogicTests(unittest.TestCase):
    def test_all_green_movements_receive_yellow(self):
        self.assertEqual(yellow_state("GGGggrrr"), "yyyyyrrr")

    def test_shared_lane_counts_only_served_movements(self):
        engine = TrafficSimulation.__new__(TrafficSimulation)
        engine.topology = {"TL": {"lanes": ["shared"], "phases": [{"links": {0}}, {"links": {1}}]}}
        engine.conn = SimpleNamespace(
            lane=SimpleNamespace(getLastStepVehicleIDs=lambda _: ["straight1", "straight2", "left"]),
            vehicle=SimpleNamespace(
                getNextTLS=lambda v: [("TL", 1 if v == "left" else 0, 5, "r")],
                getSpeed=lambda _: 0., getWaitingTime=lambda _: 3.))
        self.assertEqual(engine.movement_counts("TL"), [(2, 2, 6.), (1, 1, 3.)])

    def test_empty_and_unfinished_tripinfo(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trips.xml"
            path.write_text('<tripinfos/>')
            self.assertIsNone(tripinfo_metrics(path)["observed_avg_waiting_time_s"])
            path.write_text('<tripinfos><tripinfo depart="0" arrival="-1" waitingTime="12"/></tripinfos>')
            result = tripinfo_metrics(path)
            self.assertEqual(result["unfinished_trips"], 1)
            self.assertEqual(result["completed_trips"], 0)
            self.assertEqual(result["observed_avg_waiting_time_s"], 12)
            self.assertIsNone(result["completed_avg_travel_time_s"])
        self.assertIsNone(improvement_pct(0, 0))


@unittest.skipUnless(os.environ.get("RUN_SUMO_TESTS") == "1", "Set RUN_SUMO_TESTS=1")
class SumoTests(unittest.TestCase):
    def test_single_intersection_real_topology_and_relative_clock(self):
        env = SumoTrafficEnv(C1, sim_Compare_end=30)
        try:
            obs, info = env.reset()
            self.assertEqual(len(obs), 4)
            self.assertTrue(all(len(row) == FEATURE_DIM for row in obs))
            self.assertEqual(env.engine.start_time, 25200)
            done = False
            while not done:
                action = next(i for i, allowed in enumerate(info["action_mask"]) if allowed)
                obs, reward, terminated, truncated, info = env.step(action)
                self.assertTrue(math.isfinite(reward))
                done = terminated or truncated
            self.assertTrue(truncated)
            self.assertEqual(env.engine.conn.simulation.getTime(), 25230)
        finally:
            env.close()

    def test_two_environments_and_reset_exception_cleanup(self):
        a, b = TrafficSimulation(C1, sim_duration=10), TrafficSimulation(C3, sim_duration=10)
        try:
            a.reset()
            b.reset()
            a.tick()
            self.assertEqual(a.conn.simulation.getTime(), 25201)
            self.assertEqual(b.conn.simulation.getTime(), 25200)
            b.close()
            a.tick()
            self.assertEqual(a.conn.simulation.getTime(), 25202)
        finally:
            a.close()
            b.close()
        broken = TrafficSimulation(C1)
        with patch.object(broken, "_discover", side_effect=ValueError("bad topology")):
            with self.assertRaises(ValueError):
                broken.reset()
        self.assertIsNone(broken.conn)

    def test_phase_deadlines_clearance_and_emissions(self):
        engine = TrafficSimulation(C3, sim_duration=240)
        exact_co2 = exact_queue = 0.
        engine.audit_limit = 1000
        try:
            engine.reset()
            while not (engine.terminated or engine.truncated):
                for tl in engine.tl_ids:
                    if engine.ready(tl):
                        _, mask = engine.observe(tl, demand_mask=False)
                        state = engine.state[tl]
                        # Hold to the exact maximum, then jump directly to next legal phase.
                        active = state["active"]
                        action = active if mask[active] else next(i for i, ok in enumerate(mask) if ok)
                        engine.apply(tl, action, demand_mask=False)
                engine.tick()
                exact_co2 += sum(engine.conn.lane.getCO2Emission(l) for l in engine.network_lanes) * engine.dt / 1e6
                exact_queue += sum(engine.conn.lane.getLastStepHaltingNumber(l) for l in engine.lanes) * engine.dt
                for tl, state in engine.state.items():
                    self.assertLessEqual(state["elapsed"], engine.bounds(tl)[1])
            self.assertAlmostEqual(engine.metrics()["total_co2_kg"], exact_co2)
            self.assertEqual(engine.metrics()["queue_vehicle_seconds"], exact_queue)
            for previous, current in zip(engine.audit, engine.audit[1:]):
                for tl in engine.tl_ids:
                    before, after = previous[1][tl], current[1][tl]
                    self.assertFalse(any(a in 'Gg' and b == 'r' for a, b in zip(before["signal"], after["signal"])))
                    if before["stage"] == "all_red" and after["stage"] == "green":
                        self.assertTrue(all(c == "r" for c in before["signal"]))
                    if before["stage"] == "green" and after["stage"] == "yellow":
                        phase = engine.topology[tl]["phases"][before["active"]]
                        minimum = engine.min_green_turn if phase["turn"] else engine.min_green_major
                        self.assertGreaterEqual(before["elapsed"] + engine.dt, minimum)
            self.assertTrue(any(s["stage"] == "yellow" for _, sample in engine.audit for s in sample.values()))
            self.assertTrue(any(s["stage"] == "all_red" for _, sample in engine.audit for s in sample.values()))
        finally:
            engine.close()

    def test_real_learning_transitions_and_short_horizon(self):
        agent = DQNAgent(h1_dim=8, h2_dim=8)
        sim = RealNetworkSimulation(C3, agent=agent, train_mode=True, sim_duration=73)
        result = sim.run(verbose=False)
        self.assertIsNone(sim.engine.conn)
        self.assertGreater(agent.train_steps, 0)
        transitions = list(agent.replay_buffer)
        self.assertTrue(any(t[0] != t[3] for t in transitions))
        self.assertTrue(all(t[0] is not t[3] for t in transitions))
        self.assertTrue(all(t[2] <= 0 for t in transitions))
        self.assertEqual(sum(t[6] for t in transitions), 3)
        self.assertTrue(all(t[7] > 0 for t in transitions))
        self.assertEqual(result["remaining_vehicles"], result["unfinished_trips"])
        self.assertEqual(result["departed_vehicles"], result["completed_trips"] + result["remaining_vehicles"])
        self.assertTrue(math.isfinite(result["avg_loss"]))
        self.assertEqual(result["teleports"], 0)
        self.assertEqual(result["collisions"], 0)

    def test_empty_demand_natural_terminal(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / "empty.rou.xml").write_text("<routes/>")
            config = directory / "empty.sumocfg"
            config.write_text(f'<configuration><input><net-file value="{(C1.parent / "cologne1.net.xml").as_posix()}"/><route-files value="empty.rou.xml"/></input><time><begin value="25200"/></time></configuration>')
            result = RealNetworkSimulation(config, mode="fixed", sim_duration=10).run(verbose=False)
            self.assertTrue(result["terminated"])
            self.assertFalse(result["truncated"])
            self.assertEqual(result["completed_trips"], 0)
            self.assertEqual(result["selection_cost"], 0)
            self.assertIsNone(result["observed_avg_waiting_time_s"])

    def test_fractional_step_and_failed_run_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "fractional.sumocfg"
            config.write_text(f'<configuration><input><net-file value="{(C1.parent / "cologne1.net.xml").as_posix()}"/><route-files value="{(C1.parent / "cologne1.rou.xml").as_posix()}"/></input><time><begin value="25200"/><step-length value="0.5"/></time></configuration>')
            sim = RealNetworkSimulation(config, mode="fixed", sim_duration=60)
            sim.engine.audit_limit = 200
            result = sim.run(verbose=False)
            self.assertEqual(result["simulated_seconds"], 60)
            self.assertEqual(len(sim.engine.audit), 120)
            self.assertTrue(result["truncated"])
        broken = RealNetworkSimulation(C3, mode="fixed", sim_duration=10)
        with patch.object(broken.engine, "tick", side_effect=RuntimeError("injected failure")):
            with self.assertRaises(RuntimeError):
                broken.run(verbose=False)
        self.assertIsNone(broken.engine.conn)

    def test_trainer_checkpoint_and_no_implicit_training(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            agent = train_dqn_checkpointed(1, 30, output_dir=directory, validation_seeds=(10001,))
            self.assertTrue((directory / "training_checkpoint.json").exists())
            self.assertTrue((directory / "best_model.json").exists())
            self.assertFalse((directory / "training.lock").exists())
            (directory / "training_log.csv").unlink()
            loaded = train_dqn_checkpointed(1, 30, output_dir=directory, validation_seeds=(10001,))
            self.assertTrue((directory / "training_log.csv").exists())
            self.assertEqual(agent.q_net.to_dict(), loaded.q_net.to_dict())
            with self.assertRaises(ValueError):
                train_dqn_checkpointed(1, 30, output_dir=directory, validation_seeds=(10002,))
            with self.assertRaises(FileNotFoundError):
                RealNetworkSimulation(C3, model_path=directory / "missing.json")


if __name__ == "__main__":
    unittest.main()
