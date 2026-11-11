"""Single-intersection entry point using the shared RESCO pipeline."""
import argparse
from pathlib import Path
from corridor3_runner import train_dqn_checkpointed, run_benchmark_comparison

SUMOCFG = Path(__file__).resolve().parent.parent / "nets/cologne1/cologne1.sumocfg"


def train_dqn(episodes=50, duration=3600, output_dir=None):
    return train_dqn_checkpointed(episodes, duration, sumocfg_path=SUMOCFG, output_dir=output_dir)


def evaluate_all_controllers(duration=3600, output_dir=None):
    return run_benchmark_comparison(duration, SUMOCFG, output_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("train", "compare"), nargs="?", default="compare")
    parser.add_argument("--episodes", type=int, default=50)
    parser.add_argument("--duration", type=int, default=3600)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if args.mode == "train":
        train_dqn(args.episodes, args.duration, args.output_dir)
    else:
        evaluate_all_controllers(args.duration, args.output_dir)
