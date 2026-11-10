"""
Interactive SUMO-GUI Live Demonstration Script
Launches SUMO-GUI with the trained DQN Agent (or selected baseline) controlling the intersection live.
"""

import sys
from pathlib import Path
from env import SumoTrafficEnv
from rl_agent import DQNAgent
from baselines import FixedTimeController, ActuatedController, MaxPressureController

BASE_DIR = Path(__file__).resolve().parent.parent
SUMOCFG = BASE_DIR / "nets" / "cologne1" / "cologne1.sumocfg"
MODEL_PATH = BASE_DIR / "models" / "dqn_cologne1.json"


def run_live_demo(mode: str = "dqn"):
    env = SumoTrafficEnv(SUMOCFG, use_gui=True, seed=42)
    obs, _ = env.reset()

    if mode == "dqn" and MODEL_PATH.exists():
        ctrl = DQNAgent()
        ctrl.load(MODEL_PATH)
        print("Loaded trained DQN model for live SUMO-GUI demonstration.")
    elif mode == "maxpressure":
        ctrl = MaxPressureController()
    elif mode == "actuated":
        ctrl = ActuatedController()
    else:
        ctrl = FixedTimeController()

    done = False
    while not done:
        if isinstance(ctrl, DQNAgent):
            action = ctrl.select_action(obs, evaluate=True)
        else:
            action = ctrl.select_action(obs, env)
        obs, _, done, _ = env.step(action)

    env.close()


if __name__ == "__main__":
    selected = sys.argv[1].lower() if len(sys.argv) > 1 else "dqn"
    run_live_demo(selected)
