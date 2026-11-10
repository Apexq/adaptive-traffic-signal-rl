"""
Deep Q-Network (DQN) Agent for Adaptive Traffic Signal Control
Implements a 2-layer Multi-Layer Perceptron (MLP) Q-Network with ReLU activations,
Experience Replay Buffer, Target Network synchronization, and Epsilon-Greedy exploration.
Runs natively on CPU across any Python 3.10-3.14+ environment.
"""

import json
import math
import random
from collections import deque
from pathlib import Path
from typing import List, Tuple


class MLPNetwork:
    """Two-layer MLP (state_dim -> hidden_dim -> action_dim) with ReLU activation."""

    def __init__(self, state_dim: int = 8, hidden_dim: int = 32, action_dim: int = 2, seed: int = 42):
        rng = random.Random(seed)
        scale1 = math.sqrt(2.0 / state_dim)
        scale2 = math.sqrt(2.0 / hidden_dim)

        self.w1 = [[rng.gauss(0.0, scale1 * 0.15) for _ in range(state_dim)] for _ in range(hidden_dim)]
        self.b1 = [0.0 for _ in range(hidden_dim)]
        self.w2 = [[rng.gauss(0.0, scale2 * 0.15) for _ in range(hidden_dim)] for _ in range(action_dim)]
        self.b2 = [0.0 for _ in range(action_dim)]

        # State features: [ns_q, ew_q, ns_v, ew_v, ns_w, ew_w, cur_act, min_g]
        # Warm-start hidden units to capture approach queue pressure, approaching flow, and switching hysteresis
        for j in range(0, 8):
            self.w1[j][0] = 2.4   # NS halting queue
            self.w1[j][2] = 0.9   # NS approaching vehicles
            self.w1[j][4] = 1.5   # NS cumulative wait
            self.w1[j][6] = -0.18 # Small hysteresis bonus when already on NS (action 0)
            self.w2[0][j] = 1.5
            self.w2[1][j] = -1.2

        for j in range(8, 16):
            self.w1[j][1] = 2.4   # EW halting queue
            self.w1[j][3] = 0.9   # EW approaching vehicles
            self.w1[j][5] = 1.5   # EW cumulative wait
            self.w1[j][6] = 0.18  # Small hysteresis bonus when already on EW (action 1)
            self.w2[1][j] = 1.5
            self.w2[0][j] = -1.2

    def forward(self, x: List[float]) -> Tuple[List[float], List[float]]:
        hidden = []
        for i in range(len(self.w1)):
            z = self.b1[i] + sum(w * xi for w, xi in zip(self.w1[i], x))
            hidden.append(z if z > 0.0 else 0.0)

        out = []
        for k in range(len(self.w2)):
            q = self.b2[k] + sum(w * hj for w, hj in zip(self.w2[k], hidden))
            out.append(q)
        return out, hidden

    def copy_from(self, other: "MLPNetwork"):
        self.w1 = [row[:] for row in other.w1]
        self.b1 = other.b1[:]
        self.w2 = [row[:] for row in other.w2]
        self.b2 = other.b2[:]

    def to_dict(self) -> dict:
        return {"w1": self.w1, "b1": self.b1, "w2": self.w2, "b2": self.b2}

    def from_dict(self, data: dict):
        self.w1 = data["w1"]
        self.b1 = data["b1"]
        self.w2 = data["w2"]
        self.b2 = data["b2"]


class DQNAgent:
    """
    Deep Q-Network (DQN) Agent with Experience Replay and Target Network.
    """

    def __init__(
        self,
        state_dim: int = 8,
        action_dim: int = 2,
        hidden_dim: int = 32,
        lr: float = 0.0005,
        gamma: float = 0.95,
        epsilon_start: float = 0.30,
        epsilon_end: float = 0.01,
        epsilon_decay: float = 0.990,
        buffer_size: int = 10000,
        batch_size: int = 32,
        target_update_freq: int = 50,
        seed: int = 42,
    ):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.lr = lr
        self.gamma = gamma
        self.epsilon = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay
        self.batch_size = batch_size
        self.target_update_freq = target_update_freq
        self.rng = random.Random(seed)

        self.q_net = MLPNetwork(state_dim, hidden_dim, action_dim, seed=seed)
        self.target_net = MLPNetwork(state_dim, hidden_dim, action_dim, seed=seed)
        self.best_net = MLPNetwork(state_dim, hidden_dim, action_dim, seed=seed)
        self.target_net.copy_from(self.q_net)
        self.best_net.copy_from(self.q_net)

        self.replay_buffer = deque(maxlen=buffer_size)
        self.train_steps = 0

    def select_action(self, state: List[float], evaluate: bool = False) -> int:
        # Respect min_green indicator (state[7] == 0.0 means min_green not yet met)
        if state[7] < 0.5:
            return int(round(state[6]))

        if not evaluate and self.rng.random() < self.epsilon:
            return self.rng.randint(0, self.action_dim - 1)

        q_values, _ = self.q_net.forward(state)
        return 0 if q_values[0] >= q_values[1] else 1

    def store_transition(self, state: List[float], action: int, reward: float, next_state: List[float], done: bool):
        self.replay_buffer.append((state, action, reward / 50.0, next_state, done))

    def update(self) -> float:
        if len(self.replay_buffer) < self.batch_size:
            return 0.0

        batch = self.rng.sample(self.replay_buffer, self.batch_size)
        total_loss = 0.0

        for state, action, reward, next_state, done in batch:
            q_values, hidden = self.q_net.forward(state)
            next_q_values, _ = self.target_net.forward(next_state)
            target_q = reward if done else reward + self.gamma * max(next_q_values)

            td_error = q_values[action] - target_q
            grad_out = max(-1.0, min(1.0, td_error))
            total_loss += 0.5 * (td_error ** 2)

            w2_action_snapshot = self.q_net.w2[action][:]
            for j in range(len(hidden)):
                self.q_net.w2[action][j] -= (self.lr / self.batch_size) * grad_out * hidden[j]
            self.q_net.b2[action] -= (self.lr / self.batch_size) * grad_out

            for j in range(len(hidden)):
                if hidden[j] > 0.0:
                    grad_h = grad_out * w2_action_snapshot[j]
                    for i in range(self.state_dim):
                        self.q_net.w1[j][i] -= (self.lr / self.batch_size) * grad_h * state[i]
                    self.q_net.b1[j] -= (self.lr / self.batch_size) * grad_h

        self.train_steps += 1
        if self.train_steps % self.target_update_freq == 0:
            self.target_net.copy_from(self.q_net)

        self.epsilon = max(self.epsilon_end, self.epsilon * self.epsilon_decay)
        return total_loss / self.batch_size

    def save(self, path: str | Path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.q_net.to_dict(), indent=2), encoding="utf-8")

    def load(self, path: str | Path):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        self.q_net.from_dict(data)
        self.target_net.copy_from(self.q_net)
