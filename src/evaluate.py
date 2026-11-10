"""
Training & Multi-Seed Benchmark Evaluation Pipeline
Compares Fixed-Time, Actuated, Max-Pressure, and Proposed DQN Controller
across 5 random seeds on the Cologne-1 benchmark network.
Outputs CSV tables and SVG comparison charts in results/.
"""

import csv
import math
from pathlib import Path
from typing import Dict, List

from env import SumoTrafficEnv
from baselines import FixedTimeController, ActuatedController, MaxPressureController
from rl_agent import DQNAgent

BASE_DIR = Path(__file__).resolve().parent.parent
SUMOCFG = BASE_DIR / "nets" / "cologne1" / "cologne1.sumocfg"
RESULTS_DIR = BASE_DIR / "results"
MODELS_DIR = BASE_DIR / "models"


def train_dqn(episodes: int = 8) -> DQNAgent:
    """Trains the DQN agent on Cologne-1 and logs episode returns."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    agent = DQNAgent(seed=42)
    best_wait = float("inf")
    training_rows = []

    print(f"=== Training DQN Agent on Cologne-1 ({episodes} Episodes) ===")
    for ep in range(1, episodes + 1):
        tripinfo_path = RESULTS_DIR / f"train_ep{ep}.tripinfo.xml"
        env = SumoTrafficEnv(
            SUMOCFG,
            use_gui=False,
            seed=100 + ep * 17,
            tripinfo_file=str(tripinfo_path),
        )
        obs, _ = env.reset()
        done = False
        ep_reward = 0.0
        losses = []

        while not done:
            action = agent.select_action(obs, evaluate=False)
            next_obs, reward, done, _ = env.step(action)
            agent.store_transition(obs, action, reward, next_obs, done)
            loss = agent.update()
            if loss > 0:
                losses.append(loss)
            obs = next_obs
            ep_reward += reward

        env.close()
        metrics = SumoTrafficEnv.parse_tripinfo_metrics(tripinfo_path, env.history)
        if tripinfo_path.exists():
            tripinfo_path.unlink()

        if metrics["avg_waiting_time_s"] < best_wait:
            best_wait = metrics["avg_waiting_time_s"]
            agent.best_net.copy_from(agent.q_net)

        avg_loss = sum(losses) / max(1, len(losses))
        row = {
            "episode": ep,
            "epsilon": round(agent.epsilon, 3),
            "total_reward": round(ep_reward, 1),
            "avg_waiting_time_s": metrics["avg_waiting_time_s"],
            "avg_queue_length_veh": metrics["avg_queue_length_veh"],
            "avg_loss": round(avg_loss, 4),
        }
        training_rows.append(row)
        print(
            f"  Episode {ep:02d}/{episodes} | Reward: {row['total_reward']:8.1f} | "
            f"Avg Wait: {row['avg_waiting_time_s']:5.2f}s | Avg Queue: {row['avg_queue_length_veh']:5.2f} | "
            f"Eps: {row['epsilon']:.3f}"
        )

    # Save training log
    train_csv = RESULTS_DIR / "training_log.csv"
    with train_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(training_rows[0].keys()))
        writer.writeheader()
        writer.writerows(training_rows)

    agent.q_net.copy_from(agent.best_net)
    model_path = MODELS_DIR / "dqn_cologne1.json"
    agent.save(model_path)
    print(f"Saved trained DQN weights to: {model_path}\n")
    return agent


def evaluate_all_controllers(agent: DQNAgent, seeds: List[int] = [42, 101, 202, 303, 404]):
    """Evaluates Fixed-Time, Actuated, Max-Pressure, and DQN across multiple random seeds."""
    controllers = {
        "Fixed-Time": FixedTimeController(green_duration=40),
        "Actuated": ActuatedController(gap_threshold=2, max_green=45),
        "Max-Pressure": MaxPressureController(),
        "DQN (Proposed)": agent,
    }

    detailed_rows = []
    summary_rows = []

    print(f"=== Evaluating Controllers across {len(seeds)} Random Seeds {seeds} ===")
    for name, ctrl in controllers.items():
        seed_metrics = []
        for s in seeds:
            tripinfo_path = RESULTS_DIR / f"eval_{name.replace(' ', '_')}_s{s}.tripinfo.xml"
            env = SumoTrafficEnv(
                SUMOCFG,
                use_gui=False,
                seed=s,
                tripinfo_file=str(tripinfo_path),
            )
            obs, _ = env.reset()
            done = False
            while not done:
                if isinstance(ctrl, DQNAgent):
                    action = ctrl.select_action(obs, evaluate=True)
                else:
                    action = ctrl.select_action(obs, env)
                obs, _, done, _ = env.step(action)
            env.close()

            m = SumoTrafficEnv.parse_tripinfo_metrics(tripinfo_path, env.history)
            if tripinfo_path.exists():
                tripinfo_path.unlink()

            m["controller"] = name
            m["seed"] = s
            seed_metrics.append(m)
            detailed_rows.append(m)

        # Compute mean and std across seeds
        def mean_std(key: str):
            vals = [x[key] for x in seed_metrics]
            mean = sum(vals) / len(vals)
            var = sum((v - mean) ** 2 for v in vals) / max(1, len(vals) - 1)
            return round(mean, 2), round(math.sqrt(var), 2)

        w_m, w_s = mean_std("avg_waiting_time_s")
        q_m, q_s = mean_std("avg_queue_length_veh")
        t_m, t_s = mean_std("avg_travel_time_s")
        c_m, c_s = mean_std("total_co2_kg")
        trips_m, _ = mean_std("completed_trips")

        summary_rows.append(
            {
                "controller": name,
                "wait_mean_s": w_m,
                "wait_std_s": w_s,
                "queue_mean_veh": q_m,
                "queue_std_veh": q_s,
                "travel_mean_s": t_m,
                "travel_std_s": t_s,
                "co2_mean_kg": c_m,
                "co2_std_kg": c_s,
                "throughput_mean": trips_m,
            }
        )
        print(
            f"  {name:16s} | Wait: {w_m:5.2f} ± {w_s:4.2f}s | "
            f"Queue: {q_m:5.2f} ± {q_s:4.2f} veh | Travel: {t_m:5.2f}s | CO2: {c_m:6.2f} kg"
        )

    # Save CSVs
    detailed_csv = RESULTS_DIR / "benchmark_detailed_seeds.csv"
    with detailed_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(detailed_rows[0].keys()))
        writer.writeheader()
        writer.writerows(detailed_rows)

    summary_csv = RESULTS_DIR / "benchmark_summary.csv"
    with summary_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    generate_svg_chart(summary_rows, RESULTS_DIR / "benchmark_comparison.svg")
    print(f"\nSaved benchmark results to: {summary_csv}")
    print(f"Saved comparison chart to:  {RESULTS_DIR / 'benchmark_comparison.svg'}")


def generate_svg_chart(summary_rows: List[Dict], output_path: Path):
    """Generates a clean vector bar chart comparing Average Waiting Time and Queue Length."""
    colors = ["#ef4444", "#f59e0b", "#3b82f6", "#10b981"]
    max_wait = max(r["wait_mean_s"] for r in summary_rows) * 1.2

    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 420" width="100%" height="100%">',
        '<rect width="760" height="420" fill="#ffffff" rx="10"/>',
        '<text x="380" y="38" text-anchor="middle" font-family="Arial, sans-serif" font-size="18" font-weight="bold" fill="#1e293b">Controller Performance Comparison on Cologne-1 (5 Seeds Mean ± SD)</text>',
        '<line x1="90" y1="330" x2="700" y2="330" stroke="#94a3b8" stroke-width="2"/>',
        '<line x1="90" y1="70" x2="90" y2="330" stroke="#94a3b8" stroke-width="2"/>',
        '<text x="35" y="200" text-anchor="middle" transform="rotate(-90 35 200)" font-family="Arial, sans-serif" font-size="13" font-weight="bold" fill="#334155">Average Waiting Time per Vehicle (seconds)</text>',
    ]

    bar_width = 90
    spacing = 145
    start_x = 135

    for idx, row in enumerate(summary_rows):
        x = start_x + idx * spacing
        val = row["wait_mean_s"]
        std = row["wait_std_s"]
        bar_h = (val / max_wait) * 240.0
        y = 330.0 - bar_h
        color = colors[idx % len(colors)]

        svg.append(f'<rect x="{x}" y="{y:.1f}" width="{bar_width}" height="{bar_h:.1f}" fill="{color}" rx="5"/>')
        svg.append(
            f'<text x="{x + bar_width/2}" y="{y - 10:.1f}" text-anchor="middle" font-family="Arial, sans-serif" font-size="13" font-weight="bold" fill="#0f172a">{val:.2f}s (±{std:.2f})</text>'
        )
        svg.append(
            f'<text x="{x + bar_width/2}" y="355" text-anchor="middle" font-family="Arial, sans-serif" font-size="13" font-weight="bold" fill="#1e293b">{row["controller"]}</text>'
        )
        svg.append(
            f'<text x="{x + bar_width/2}" y="375" text-anchor="middle" font-family="Arial, sans-serif" font-size="11" fill="#64748b">Queue: {row["queue_mean_veh"]:.1f} veh | CO2: {row["co2_mean_kg"]:.1f} kg</text>'
        )

    svg.append("</svg>")
    output_path.write_text("\n".join(svg), encoding="utf-8")


if __name__ == "__main__":
    trained_agent = train_dqn(episodes=8)
    evaluate_all_controllers(trained_agent)
