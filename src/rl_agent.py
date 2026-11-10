"""
Phase-Competition Deep Q-Network (DQN) Agent for Real-World Multi-Phase Intersections
Inspired by PressLight (Wei et al., KDD 2019) and FRAP (Zheng et al., CIKM 2019).

Architecture:
  - For each candidate green phase p in {0, ..., K-1} of an intersection (whether 2, 3, or 4+ phases),
    the environment extracts a 6-dimensional phase feature vector x_p:
      [phase_Effective_pressure, phase_approaching_vehicles, phase_waiting_time,
       max_competing_phase_pressure, is_currently_active, turn_phase_penalty]
  - A 2-layer Multi-Layer Perceptron (6 -> 32 -> 1 with ReLU activation) initialized with
    100% random He initialization (ZERO hard-coded weights!) predicts Q(s, p) for each phase p.
  - Trained from scratch via Experience Replay Buffer and Target Network updates.
"""

import json
import math
import random
from collections import deque
from pathlib import Path
from typing import List, Tuple


class PhaseMLPNetwork:
    """Two-layer MLP (6 -> hidden_dim -> 1) scoring any candidate signal phase."""

    def __init__(self, in_dim: int = 6, hidden_dim: int = 32, seed: int = 42):
        rng = random.Random(seed)
        scale1 = math.sqrt(2.0 / in_dim)
        scale2 = math.sqrt(2.0 / hidden_dim)

        # 100% Random He Initialization (No manual warm-start / no hard-coded rules)
        self.w1 = [[rng.gauss(0.0, scale1) for _ in range(in_dim)] for _ in range(hidden_dim)]
        self.b1 = [0.0 for _ in range(hidden_dim)]
        self.w2 = [rng.gauss(0.0, scale2) for _ in range(hidden_dim)]
        self.b2 = 0.0

    def forward_single_phase(self, x: List[float]) -> Tuple[float, List[float]]:
        hidden = []
        for i in range(len(self.w1)):
            z = self.b1[i] + sum(w * xi for w, xi in zip(self.w1[i], x))
            hidden.append(z if z > 0.0 else 0.0)
        q_val = self.b2 + sum(w * hj for w, hj in zip(self.w2, hidden))
        return q_val, hidden

    def predict_all_phases(self, phase_features: List[List[float]]) -> List[float]:
        return [self.forward_single_phase(x)[0] for x in phase_features]

    def copy_from(self, other: "PhaseMLPNetwork"):
        self.w1 = [row[:] for row in other.w1]
        self.b1 = other.b1[:]
        self.w2 = other.w2[:]
        self.b2 = other.b2

    def to_dict(self) -> dict:
        return {"w1": self.w1, "b1": self.b1, "w2": self.w2, "b2": self.b2}

    def from_dict(self, data: dict):
        self.w1 = data["w1"]
        self.b1 = data["b1"]
        self.w2 = data["w2"]
        self.b2 = data["b2"]


class DQNAgent:
    """
    Phase-Competition Deep Q-Network (DQN) Agent trained from scratch.
    Works across intersections with any number of green phases (K = 2, 3, 4, ...).
    """

    def __init__(
        self,
        in_dim: int = 6,
        hidden_dim: int = 32,
        lr: float = 0.008,
        gamma: float = 0.85,
        epsilon_start: float = 0.75,
        epsilon_end: float = 0.02,
        epsilon_decay: float = 0.9982,
        buffer_size: int = 12000,
        batch_size: int = 32,
        target_update_freq: int = 25,
        seed: int = 42,
    ):
        self.in_dim = in_dim
        self.lr = lr
        self.gamma = gamma
        self.epsilon = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay
        self.batch_size = batch_size
        self.target_update_freq = target_update_freq
        self.rng = random.Random(seed)

        self.q_net = PhaseMLPNetwork(in_dim, hidden_dim, seed=seed)
        self.target_net = PhaseMLPNetwork(in_dim, hidden_dim, seed=seed)
        self.best_net = PhaseMLPNetwork(in_dim, hidden_dim, seed=seed)
        self.target_net.copy_from(self.q_net)
        self.best_net.copy_from(self.q_net)

        self.replay_buffer = deque(maxlen=buffer_size)
        self.train_steps = 0

    def select_action(self, phase_features: List[List[float]], evaluate: bool = False) -> int:
        num_phases = len(phase_features)
        if not evaluate and self.rng.random() < self.epsilon:
            return self.rng.randint(0, num_phases - 1)

        q_values = self.q_net.predict_all_phases(phase_features)
        best_idx = 0
        best_q = q_values[0]
        for idx in range(1, num_phases):
            if q_values[idx] > best_q:
                best_q = q_values[idx]
                best_idx = idx
        return best_idx

    def store_transition(
        self,
        phase_features: List[List[float]],
        action: int,
        reward: float,
        next_phase_features: List[List[float]],
        done: bool,
    ):
        self.replay_buffer.append((phase_features, action, reward, next_phase_features, done))

    def update(self) -> float:
        if len(self.replay_buffer) < self.batch_size:
            return 0.0

        batch = self.rng.sample(self.replay_buffer, self.batch_size)
        total_loss = 0.0

        for phase_feats, action, reward, next_phase_feats, done in batch:
            x_act = phase_feats[action]
            q_pred, hidden = self.q_net.forward_single_phase(x_act)
            next_qs = self.target_net.predict_all_phases(next_phase_feats)
            target_q = reward if done else reward + self.gamma * max(next_qs)

            td_error = q_pred - target_q
            grad_out = max(-1.5, min(1.5, td_error))
            total_loss += 0.5 * (td_error ** 2)

            w2_snapshot = self.q_net.w2[:]
            step_lr = self.lr / self.batch_size
            for j in range(len(hidden)):
                self.q_net.w2[j] -= step_lr * grad_out * hidden[j]
            self.q_net.b2 -= step_lr * grad_out

            for j in range(len(hidden)):
                if hidden[j] > 0.0:
                    grad_h = grad_out * w2_snapshot[j]
                    for i in range(self.in_dim):
                        self.q_net.w1[j][i] -= step_lr * grad_h * x_act[i]
                    self.q_net.b1[j] -= step_lr * grad_h

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
