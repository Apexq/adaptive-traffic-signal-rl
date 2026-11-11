"""Correctness-first RESCO runner. Training is always explicitly requested."""
import argparse
import csv
import json
import math
from pathlib import Path
import statistics
import tempfile
import time
import uuid

from baselines import select_baseline
from env import TrafficSimulation, tripinfo_metrics
from rl_agent import DQNAgent
from runtime import atomic_json

BASE_DIR = Path(__file__).resolve().parent.parent
SUMOCFG_C3 = BASE_DIR / "nets" / "cologne3" / "cologne3.sumocfg"
ARTIFACT_DIR = BASE_DIR / "artifacts" / "v2"
MODEL_PATH = ARTIFACT_DIR / "cologne3" / "best_model.json"
CKPT_PATH = ARTIFACT_DIR / "cologne3" / "training_checkpoint.json"
RESULTS_DIR = ARTIFACT_DIR / "cologne3"
VALIDATION_SEEDS = (10001, 10002, 10003)
TEST_SEEDS = (20001, 20002, 20003, 20004, 20005)


def write_csv(path, rows):
    if not rows:
        return
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temporary.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


class RealNetworkSimulation:
    def __init__(self, sumocfg_path=SUMOCFG_C3, mode="dqn", use_gui=False,
                 seed=42, sim_duration=3600, agent=None, train_mode=False,
                 model_path=None):
        if mode not in ("fixed", "actuated", "maxpressure", "dqn"):
            raise ValueError(f"Unknown controller: {mode}")
        if train_mode and mode != "dqn":
            raise ValueError("Only DQN supports training")
        self.engine = TrafficSimulation(sumocfg_path, use_gui, seed, sim_duration, finite_horizon=True)
        self.mode, self.train_mode = mode, train_mode
        self.engine.baseline_mode = mode
        self.agent = agent
        if mode == "dqn":
            if agent is None:
                self.agent = DQNAgent(seed=seed)
                self.agent.metadata = self.engine.identity
                if not train_mode:
                    path = Path(model_path) if model_path else ARTIFACT_DIR / Path(sumocfg_path).stem / "best_model.json"
                    if not path.exists():
                        raise FileNotFoundError(f"No v2 model at {path}; training must be started explicitly")
                    self.agent.load(path)
            elif agent.metadata and agent.metadata != self.engine.identity:
                raise ValueError("Agent scenario/control metadata mismatch")
            else:
                self.agent.metadata = self.engine.identity
        self.transition_count = 0

    def run(self, tripinfo_path=None, verbose=True, **progress):
        pending = {}
        loss_sum, updates, ep_reward = 0.0, 0, 0.0
        # Unique per-run path even when the caller does not need tripinfo files.
        with tempfile.TemporaryDirectory(prefix="traffic-rl-") as temp:
            output = Path(tripinfo_path) if tripinfo_path else Path(temp) / "trips.xml"
            try:
                self.engine.reset(tripinfo_path=output)
                last_report = -60.0
                while not (self.engine.terminated or self.engine.truncated):
                    for tl in self.engine.tl_ids:
                        if not self.engine.ready(tl):
                            continue
                        features, mask = self.engine.observe(tl)
                        if tl in pending:
                            old = pending.pop(tl)
                            self.agent.store_transition(old["features"], old["action"], old["reward"],
                                features, False, mask, False, old["duration"])
                            loss_sum += self.agent.update()
                            updates += 1
                            self.transition_count += 1
                        if self.mode == "dqn":
                            action = self.agent.select_action(features, mask, evaluate=not self.train_mode)
                        else:
                            # Sequential baselines must serve their next phase even if empty.
                            state = self.engine.state[tl]
                            lower, upper = self.engine.bounds(tl)
                            mask = [True] * len(features)
                            if state["elapsed"] < lower - 1e-9:
                                mask = [i == state["active"] for i in range(len(features))]
                            elif state["elapsed"] >= upper - 1e-9:
                                mask[state["active"]] = False
                            action = select_baseline(self.engine, tl, self.mode, features, mask)
                        self.engine.apply(tl, action, demand_mask=self.mode == "dqn")
                        if self.train_mode:
                            pending[tl] = dict(features=features, action=action, reward=0.0, duration=0.0)
                    self.engine.tick()
                    for tl, old in pending.items():
                        lanes = max(1, len(self.engine.topology[tl]["lanes"]))
                        reward = -self.engine.last_queues[tl] * self.engine.dt / (8 * lanes * 5)
                        old["reward"] += self.agent.gamma ** (old["duration"] / 5) * reward
                        old["duration"] += self.engine.dt
                        ep_reward += reward
                    elapsed = self.engine.conn.simulation.getTime() - self.engine.start_time
                    if verbose and elapsed - last_report >= 60:
                        print(f"{self.mode}: {elapsed:.0f}/{self.engine.sim_duration:.0f}s, "
                              f"queue={sum(self.engine.last_queues.values())}", flush=True)
                        last_report = elapsed
                for tl, old in pending.items():
                    features, mask = self.engine.observe(tl)
                    self.agent.store_transition(old["features"], old["action"], old["reward"],
                        features, self.engine.terminated, mask, self.engine.truncated, old["duration"])
                    loss_sum += self.agent.update()
                    updates += 1
                    self.transition_count += 1
                metrics = self.engine.metrics()
            finally:
                self.engine.close()
            metrics.update(tripinfo_metrics(output))
            metrics.update(mode=self.mode, seed=self.engine.seed,
                           ep_reward=ep_reward, avg_loss=loss_sum / max(1, updates),
                           transitions=self.transition_count)
            return metrics


def validation_score(agent, config, duration, seeds=VALIDATION_SEEDS):
    rows = [RealNetworkSimulation(config, agent=agent, seed=seed,
                                 sim_duration=duration).run(verbose=False) for seed in seeds]
    if any(r["collisions"] or r["teleports"] for r in rows):
        raise RuntimeError("Validation contains collisions/teleports; inspect the scenario")
    for row in rows:
        demand = row["completed_trips"] + row["unfinished_trips"] + row["undeparted_trips"]
        row["completion_rate"] = row["completed_trips"] / demand if demand else 0.0
    score = (-statistics.mean(r["completion_rate"] for r in rows),
             statistics.mean(r["selection_cost"] for r in rows))
    return score, rows


def train_dqn_checkpointed(total_episodes=50, sim_duration=3600, reset_ckpt=False,
                          sumocfg_path=SUMOCFG_C3, output_dir=None,
                          validation_seeds=VALIDATION_SEEDS):
    if total_episodes <= 0 or not validation_seeds:
        raise ValueError("Positive episode count and validation seeds required")
    training_seeds = {100 + ep * 13 for ep in range(1, total_episodes + 1)}
    if (training_seeds.intersection(validation_seeds) or training_seeds.intersection(TEST_SEEDS)
            or set(validation_seeds).intersection(TEST_SEEDS)):
        raise ValueError("Training, validation and test seeds must be disjoint")
    directory = Path(output_dir) if output_dir else ARTIFACT_DIR / Path(sumocfg_path).stem
    directory.mkdir(parents=True, exist_ok=True)
    checkpoint, model = directory / "training_checkpoint.json", directory / "best_model.json"
    # Fail rather than allow two writers to race on the same experiment.
    lock_path = directory / "training.lock"
    with lock_path.open("x") as lock:
        lock.write("Training in progress. Remove only after confirming no training process is running.\n")
    try:
        agent = DQNAgent(seed=42)
        agent.metadata = TrafficSimulation(sumocfg_path, sim_duration=sim_duration, finite_horizon=True).identity
        start_ep, best_score, rows = 1, (math.inf, math.inf), []
        manifest_path = directory / "experiment.json"
        manifest = {"metadata": agent.metadata, "validation_seeds": list(validation_seeds),
                    "test_seeds": list(TEST_SEEDS), "training_seed_rule": "100 + episode * 13"}
        if reset_ckpt and checkpoint.exists():
            raise FileExistsError("Fresh training needs a new --output-dir; existing artifacts are preserved")
        if checkpoint.exists():
            if not manifest_path.exists() or json.loads(manifest_path.read_text()) != manifest:
                raise ValueError("Resume experiment/seed configuration mismatch")
            last, best_score, rows = agent.load_checkpoint(checkpoint)
            if last > total_episodes:
                raise ValueError("Requested episode total precedes the saved checkpoint")
            start_ep = last + 1
            write_csv(directory / "training_log.csv", rows)
            # Recover a best model even if interruption occurred after checkpoint replacement.
            agent.save(model, best=True)
        atomic_json(manifest_path, manifest)
        try:
            for ep in range(start_ep, total_episodes + 1):
                started = time.perf_counter()
                metrics = RealNetworkSimulation(sumocfg_path, agent=agent, train_mode=True,
                    seed=100 + ep * 13, sim_duration=sim_duration).run(verbose=False)
                if metrics["collisions"] or metrics["teleports"]:
                    raise RuntimeError("Training contains collisions/teleports")
                score, validation_rows = validation_score(agent, sumocfg_path, sim_duration, validation_seeds)
                if score < best_score:
                    best_score = score
                    agent.best_net.copy_from(agent.q_net)
                rows.append(dict(episode=ep, epsilon=agent.epsilon, ep_reward=metrics["ep_reward"],
                    avg_loss=metrics["avg_loss"], training_cost=metrics["selection_cost"],
                    validation_cost=score[1], best_validation_cost=best_score[1],
                    validation_completion_rate=-score[0], best_validation_completion_rate=-best_score[0],
                    wall_seconds=time.perf_counter() - started))
                agent.decay_epsilon_episode()
                agent.save_checkpoint(checkpoint, ep, total_episodes, best_score, rows)
                agent.save(model, best=True)
                write_csv(directory / "training_log.csv", rows)
                write_csv(directory / f"validation_ep{ep:03d}.csv", validation_rows)
                print(f"Episode {ep}/{total_episodes}: validation={score[1]:.1f}, completion={-score[0]:.2%}, "
                      f"best completion={-best_score[0]:.2%}, epsilon={agent.epsilon:.3f}", flush=True)
        except KeyboardInterrupt:
            print("Interrupted. Only the last fully completed episode is resumable.")
            return None
        agent.q_net.copy_from(agent.best_net)
        agent.save(model)
        return agent
    finally:
        lock_path.unlink(missing_ok=True)


def improvement_pct(baseline, candidate):
    if baseline is None or candidate is None or baseline == 0:
        return None
    return 100 * (baseline - candidate) / baseline


def run_benchmark_comparison(sim_duration=3600, sumocfg_path=SUMOCFG_C3,
                             output_dir=None, seeds=TEST_SEEDS, model_path=None):
    if not seeds or set(seeds).intersection(VALIDATION_SEEDS):
        raise ValueError("Use nonempty held-out test seeds")
    directory = Path(output_dir) if output_dir else ARTIFACT_DIR / Path(sumocfg_path).stem
    model = Path(model_path) if model_path else directory / "best_model.json"
    manifest_path = model.parent / "experiment.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        forbidden = set(manifest["validation_seeds"])
        training_log = model.parent / "training_log.csv"
        checkpoint = model.parent / "training_checkpoint.json"
        if checkpoint.exists():
            last_episode = json.loads(checkpoint.read_text())["last_episode"]
            forbidden.update(100 + ep * 13 for ep in range(1, last_episode + 1))
        elif training_log.exists():
            with training_log.open(encoding="utf-8") as stream:
                forbidden.update(100 + int(r["episode"]) * 13 for r in csv.DictReader(stream))
        if forbidden.intersection(seeds):
            raise ValueError("Test seeds overlap this experiment's training/validation seeds")
    # Validate the model before spending time on baselines; never auto-train.
    RealNetworkSimulation(sumocfg_path, sim_duration=sim_duration, model_path=model)
    rows = []
    for mode in ("fixed", "actuated", "maxpressure", "dqn"):
        for seed in seeds:
            result = RealNetworkSimulation(sumocfg_path, mode=mode, seed=seed,
                sim_duration=sim_duration, model_path=model).run(verbose=False)
            rows.append(result)
            print(f"{mode}, seed={seed}: cost={result['selection_cost']:.1f}, "
                  f"completed={result['completed_trips']}, remaining={result['remaining_vehicles']}")
    write_csv(directory / "benchmark_detailed.csv", rows)
    summary = []
    for mode in ("fixed", "actuated", "maxpressure", "dqn"):
        subset = [r for r in rows if r["mode"] == mode]
        result = {"mode": mode, "seed_count": len(subset)}
        for metric in ("selection_cost", "observed_avg_waiting_time_s", "completed_avg_travel_time_s",
                       "avg_corridor_queue_veh", "total_co2_kg", "completed_trips", "remaining_vehicles",
                       "pending_vehicles", "teleports", "collisions"):
            values = [r[metric] for r in subset if r[metric] is not None]
            result[metric + "_mean"] = statistics.mean(values) if values else None
            result[metric + "_std"] = statistics.stdev(values) if len(values) > 1 else (0.0 if values else None)
        summary.append(result)
    write_csv(directory / "benchmark_summary.csv", summary)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("train", "compare", "fixed", "actuated", "maxpressure", "dqn"), nargs="?", default="compare")
    parser.add_argument("--scenario", choices=("cologne1", "cologne3"), default="cologne3")
    parser.add_argument("--duration", type=int, default=3600)
    parser.add_argument("--episodes", type=int, default=50)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()
    config = BASE_DIR / "nets" / args.scenario / (args.scenario + ".sumocfg")
    if args.mode == "train":
        train_dqn_checkpointed(args.episodes, args.duration, args.reset, config, args.output_dir)
    elif args.mode == "compare":
        run_benchmark_comparison(args.duration, config, args.output_dir)
    else:
        model = args.output_dir / "best_model.json" if args.output_dir else None
        result = RealNetworkSimulation(config, mode=args.mode, use_gui=not args.headless,
            sim_duration=args.duration, model_path=model).run()
        print(result)


if __name__ == "__main__":
    main()
