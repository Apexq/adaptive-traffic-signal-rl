"""Pre-training acceptance checks; never writes production model/checkpoint files."""
import argparse
import math
from pathlib import Path
import time
from corridor3_runner import BASE_DIR, RealNetworkSimulation
from rl_agent import DQNAgent
from runtime import atomic_json


def validate(output, full_duration=3600):
    report = {"purpose": "pre-training acceptance, not trained-policy performance", "runs": []}
    config = BASE_DIR / "nets/cologne3/cologne3.sumocfg"
    # Exercise the real 7-64-64-1 learner over independent short episodes.
    for seed in (113, 126, 139):
        agent = DQNAgent(seed=42)
        started = time.perf_counter()
        simulation = RealNetworkSimulation(config, seed=seed, sim_duration=120,
                                           agent=agent, train_mode=True)
        metrics = simulation.run(verbose=False)
        assert agent.train_steps > 0 and metrics["transitions"] > 0
        assert math.isfinite(metrics["avg_loss"])
        assert any(t[0] != t[3] for t in agent.replay_buffer)
        assert sum(t[6] for t in agent.replay_buffer) == 3
        assert not metrics["teleports"] and not metrics["collisions"]
        report["runs"].append({"kind": "120s learner smoke", "wall_seconds": time.perf_counter()-started,
                                "train_steps": agent.train_steps, **metrics})
        print(f"Learner smoke seed={seed}: OK", flush=True)
    for scenario, mode in (("cologne3", "fixed"), ("cologne3", "actuated"),
                           ("cologne3", "maxpressure"), ("cologne3", "dqn"), ("cologne1", "fixed")):
        cfg = BASE_DIR / "nets" / scenario / (scenario + ".sumocfg")
        agent = DQNAgent(seed=42) if mode == "dqn" else None
        started = time.perf_counter()
        simulation = RealNetworkSimulation(cfg, mode=mode, agent=agent, sim_duration=full_duration)
        simulation.engine.audit_limit = int(full_duration) + 1
        metrics = simulation.run(verbose=False)
        assert not metrics["teleports"] and not metrics["collisions"]
        assert metrics["remaining_vehicles"] == metrics["unfinished_trips"]
        assert metrics["departed_vehicles"] == metrics["completed_trips"] + metrics["remaining_vehicles"]
        for _, snapshot in simulation.engine.audit:
            for tl, state in snapshot.items():
                phase = simulation.engine.topology[tl]["phases"][state["active"]]
                assert state["elapsed"] <= (10 if phase["turn"] else 45)
        for before, after in zip(simulation.engine.audit, simulation.engine.audit[1:]):
            for tl in simulation.engine.tl_ids:
                a, b = before[1][tl]["signal"], after[1][tl]["signal"]
                assert not any(x in "gG" and y == "r" for x, y in zip(a, b))
        report["runs"].append({"kind": "full-horizon simulation (DQN is untrained)", "scenario": scenario,
                                "wall_seconds": time.perf_counter()-started, **metrics})
        print(f"{scenario} {mode} {full_duration}s: OK", flush=True)
    atomic_json(output, report)
    print(f"Acceptance report: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=BASE_DIR / "artifacts/v2/acceptance.json")
    parser.add_argument("--duration", type=int, default=3600)
    args = parser.parse_args()
    validate(args.output, args.duration)
