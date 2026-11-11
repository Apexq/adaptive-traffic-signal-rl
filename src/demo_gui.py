"""Single-intersection GUI using the same validated engine as Cologne-3."""
import argparse
from pathlib import Path
from corridor3_runner import RealNetworkSimulation


def run_live_demo(mode="dqn", duration=3600, model_path=None, use_gui=True):
    config = Path(__file__).resolve().parent.parent / "nets/cologne1/cologne1.sumocfg"
    return RealNetworkSimulation(config, mode=mode, use_gui=use_gui,
                                 sim_duration=duration, model_path=model_path).run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", nargs="?", default="dqn", choices=("dqn", "fixed", "actuated", "maxpressure"))
    parser.add_argument("--duration", type=int, default=3600)
    parser.add_argument("--model", type=Path)
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()
    print(run_live_demo(args.mode, args.duration, args.model, not args.headless))
