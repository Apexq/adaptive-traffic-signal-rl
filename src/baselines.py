"""
Baseline Traffic Signal Controllers:
  1. FixedTimeController: Conventional static cycle (switches every 40 seconds).
  2. ActuatedController: Classical gap-out / demand-actuated signal controller.
  3. MaxPressureController: Varaiya (2013) Max-Pressure adaptive controller.
"""

from typing import List
from env import SumoTrafficEnv


class FixedTimeController:
    """Switches phases strictly on a fixed green duration (e.g., 40s NS, 40s EW)."""

    def __init__(self, green_duration: int = 40):
        self.green_duration = green_duration

    def select_action(self, obs: List[float], env: SumoTrafficEnv) -> int:
        if env.elapsed_green >= self.green_duration:
            return 1 - env.current_action
        return env.current_action


class ActuatedController:
    """
    Classical Traffic-Actuated Controller (Gap-Out + Extension):
    Ends current green phase early (once min_green is met) if active queue drops
    to <= 2 vehicles while conflicting queue has waiting vehicles.
    """

    def __init__(self, gap_threshold: int = 2, max_green: int = 45):
        self.gap_threshold = gap_threshold
        self.max_green = max_green

    def select_action(self, obs: List[float], env: SumoTrafficEnv) -> int:
        if env.elapsed_green < env.min_green:
            return env.current_action

        queues = env.get_approach_queues()
        active_key = "NS" if env.current_action == 0 else "EW"
        other_key = "EW" if env.current_action == 0 else "NS"

        # Gap-out condition: active approach has almost cleared and competing approach has demand
        if queues[active_key] <= self.gap_threshold and queues[other_key] > self.gap_threshold:
            return 1 - env.current_action

        # Max-green reached
        if env.elapsed_green >= self.max_green and queues[other_key] > 0:
            return 1 - env.current_action

        return env.current_action


class MaxPressureController:
    """
    Max-Pressure Adaptive Signal Controller (Varaiya, 2013):
    At each decision step (after min_green), computes queue pressure on each phase
    and selects the phase with maximum net pressure.
    """

    def select_action(self, obs: List[float], env: SumoTrafficEnv) -> int:
        if env.elapsed_green < env.min_green:
            return env.current_action

        pressures = env.get_approach_pressures()
        # Hysteresis margin (1.5) prevents unnecessary yellow-light switching overhead
        if env.current_action == 0:
            if pressures["EW"] > pressures["NS"] + 1.5:
                return 1
            return 0
        else:
            if pressures["NS"] > pressures["EW"] + 1.5:
                return 0
            return 1
