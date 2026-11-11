"""Regression checks requiring only the standard library (no running SUMO)."""
import copy
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from rl_agent import DQNAgent, DeepPhaseMLP
from runtime import FEATURE_DIM, atomic_json, scenario_identity
from generate_charts import chart


class AgentTests(unittest.TestCase):
    def features(self):
        return [[0.2] * FEATURE_DIM, [0.3] * FEATURE_DIM]

    def test_reject_flat_and_invalid_mask(self):
        agent = DQNAgent()
        with self.assertRaises(ValueError):
            agent.select_action([0.] * 9)
        with self.assertRaises(ValueError):
            agent.select_action(self.features(), [False, False])
        with self.assertRaises(ValueError):
            agent.select_action(self.features(), [True])
        self.assertEqual(agent.select_action(self.features(), [False, True]), 1)

    def test_masked_bootstrap_terminal_and_duration(self):
        agent = DQNAgent()
        agent.target_net.predict_all_phases = lambda _: [1., 100.]
        self.assertAlmostEqual(agent.bellman_target(2, self.features(), False, [True, False], 5), 2.88)
        self.assertAlmostEqual(agent.bellman_target(2, self.features(), False, [True, False], 10), 2 + .88**2)
        self.assertEqual(agent.bellman_target(2, self.features(), True, [False, False], 5), 2)

    def test_replay_copies_state_and_truncation_bootstraps(self):
        agent = DQNAgent(batch_size=1)
        state = self.features()
        agent.store_transition(state, 0, -1, state, False, [True, False], True, 5)
        state[0][0] = 999
        self.assertEqual(agent.replay_buffer[0][0][0][0], .2)
        self.assertTrue(agent.replay_buffer[0][6])
        self.assertTrue(math.isfinite(agent.update()))

    def test_resume_is_exact(self):
        a = DQNAgent(batch_size=2, h1_dim=4, h2_dim=3)
        a.metadata = {"scenario": "test"}
        for i in range(5):
            a.store_transition(self.features(), i % 2, -i, self.features(), False, [True, False], False, 5)
        a.update()
        a.decay_epsilon_episode()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "checkpoint.json"
            a.save_checkpoint(path, 2, 5, 123., [{"episode": 2}])
            b = DQNAgent(batch_size=2, h1_dim=4, h2_dim=3)
            b.metadata = a.metadata.copy()
            self.assertEqual(b.load_checkpoint(path)[0], 2)
            self.assertEqual(len(b.replay_buffer), 5)
            self.assertEqual(a.rng.getstate(), b.rng.getstate())
            self.assertEqual(a.epsilon, b.epsilon)
            self.assertEqual(a.update(), b.update())
            self.assertEqual(a.q_net.to_dict(), b.q_net.to_dict())
            self.assertEqual(a.target_net.to_dict(), b.target_net.to_dict())
            self.assertEqual(a.select_action(self.features()), b.select_action(self.features()))

    def test_legacy_and_foreign_model_fail_without_mutation(self):
        agent = DQNAgent()
        before = copy.deepcopy(agent.q_net.to_dict())
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "model.json"
            path.write_text('{"w1": []}')
            with self.assertRaises(ValueError):
                agent.load(path)
            agent.metadata = {"scenario": "A"}
            agent.save(path)
            agent.metadata = {"scenario": "B"}
            with self.assertRaises(ValueError):
                agent.load(path)
        self.assertEqual(before, agent.q_net.to_dict())

    def test_backprop_matches_finite_difference(self):
        agent = DQNAgent(in_dim=2, h1_dim=2, h2_dim=2, batch_size=1, lr=1e-5)
        net = agent.q_net
        net.w1, net.b1 = [[.2, .3], [.4, .2]], [.1, .1]
        net.w2, net.b2 = [[.2, .1], [.3, .2]], [.1, .1]
        net.w3, net.b3 = [.3, .4], .1
        state = [[.2, .5]]
        reward = net.forward_single_phase(state[0])[0] + .2
        before = copy.deepcopy(net.to_dict())
        expected = {}
        for name in ("w1", "b1", "w2", "b2", "w3", "b3"):
            value = getattr(net, name)
            paths = [(i, j) for i in range(2) for j in range(2)] if name in ("w1", "w2") else ([(i,) for i in range(2)] if name != "b3" else [()])
            for indices in paths:
                def change(offset):
                    net.from_dict(before)
                    if len(indices) == 2:
                        getattr(net, name)[indices[0]][indices[1]] += offset
                    elif indices:
                        getattr(net, name)[indices[0]] += offset
                    else:
                        net.b3 += offset
                    q = net.forward_single_phase(state[0])[0]
                    return .5 * (q - reward)**2
                expected[(name, indices)] = (change(1e-6) - change(-1e-6)) / 2e-6
        net.from_dict(before)
        agent.store_transition(state, 0, reward, state, True, [False], False, 5)
        agent.update()
        for (name, indices), gradient in expected.items():
            old, new = before[name], getattr(net, name)
            for i in indices:
                old, new = old[i], new[i]
            self.assertAlmostEqual((old-new)/agent.lr, gradient, places=7)

    def test_nonfinite_and_wrong_dimensions(self):
        network = DeepPhaseMLP()
        with self.assertRaises(ValueError):
            network.forward_single_phase([0.] * 9)
        with self.assertRaises(ValueError):
            network.forward_single_phase([math.nan] * FEATURE_DIM)
        state = network.to_dict()
        state["w1"][0].pop()
        with self.assertRaises(ValueError):
            network.from_dict(state)


class PersistenceTests(unittest.TestCase):
    def test_interrupted_replace_preserves_previous_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "checkpoint.json"
            atomic_json(path, {"valid": True})
            with patch("runtime.os.replace", side_effect=OSError("interrupted")):
                with self.assertRaises(OSError):
                    atomic_json(path, {"valid": False})
            self.assertEqual(json.loads(path.read_text()), {"valid": True})
            self.assertEqual(len(list(Path(tmp).iterdir())), 1)

    def test_zero_chart(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "chart.svg"
            chart([{"x": "empty", "y": 0}], "x", "y", path, "Empty")
            self.assertTrue(path.exists())
            self.assertNotIn("nan", path.read_text())

    def test_real_scenario_identity_changes_with_routes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path / "net.xml").write_text("network")
            (path / "route.xml").write_text("route1")
            config = path / "config.xml"
            config.write_text('<configuration><input><net-file value="net.xml"/><route-files value="route.xml"/></input></configuration>')
            old = scenario_identity(config)
            (path / "route.xml").write_text("route2")
            self.assertNotEqual(old, scenario_identity(config))


if __name__ == "__main__":
    unittest.main()
