"""
Deep Phase-Competition Q-Network (DQN) Agent for Acyclic Multi-Phase Signal Control
Architecture:
  - 2 Hidden Layers: 6 inputs -> 64 ReLU -> 64 ReLU -> 1 Q-value output per phase
  - 100% Random He Initialization (No manual warm-start weights)
  - Experience Replay Buffer + Target Network + Gradient Clipping
  - Full Checkpoint Save & Resume Support (can pause/stop at any episode and resume later)
"""

import json
import math
import random
from collections import deque
from pathlib import Path
from typing import Dict, List, Tuple


class DeepPhaseMLP:
    """Three-layer Deep MLP (6 -> 64 -> 64 -> 1) with ReLU activations scoring any signal phase."""

    def __init__(self, in_dim: int = 6, h1_dim: int = 64, h2_dim: int = 64, seed: int = 42):
        self.in_dim = in_dim
        self.h1_dim = h1_dim
        self.h2_dim = h2_dim
        rng = random.Random(seed)

        s1 = math.sqrt(2.0 / in_dim)
        s2 = math.sqrt(2.0 / h1_dim)
        s3 = math.sqrt(2.0 / h2_dim)

        # 100% Random He Initialization
        self.w1 = [[rng.gauss(0.0, s1) for _ in range(in_dim)] for _ in range(h1_dim)]
        self.b1 = [0.0 for _ in range(h1_dim)]

        self.w2 = [[rng.gauss(0.0, s2) for _ in range(h1_dim)] for _ in range(h2_dim)]
        self.b2 = [0.0 for _ in range(h2_dim)]

        self.w3 = [rng.gauss(0.0, s3) for _ in range(h2_dim)]
        self.b3 = 0.0

    def forward_single_phase(self, x: List[float]) -> Tuple[float, List[float], List[float]]:
        h1 = []
        for i in range(self.h1_dim):
            z1 = self.b1[i] + sum(w * xi for w, xi in zip(self.w1[i], x))
            h1.append(z1 if z1 > 0.0 else 0.0)

        h2 = []
        for j in range(self.h2_dim):
            z2 = self.b2[j] + sum(w * h1i for w, h1i in zip(self.w2[j], h1))
            h2.append(z2 if z2 > 0.0 else 0.0)

        q_val = self.b3 + sum(w * h2j for w, h2j in zip(self.w3, h2))
        return q_val, h1, h2

    def predict_all_phases(self, phase_features: List[List[float]]) -> List[float]:
        return [self.forward_single_phase(x)[0] for x in phase_features]

    def copy_from(self, other: "DeepPhaseMLP"):
        self.w1 = [row[:] for row in other.w1]
        self.b1 = other.b1[:]
        self.w2 = [row[:] for row in other.w2]
        self.b2 = other.b2[:]
        self.w3 = other.w3[:]
        self.b3 = other.b3

    def to_dict(self) -> dict:
        return {
            "arch": "6-64-64-1",
            "w1": self.w1,
            "b1": self.b1,
            "w2": self.w2,
            "b2": self.b2,
            "w3": self.w3,
            "b3": self.b3,
        }

    def from_dict(self, data: dict):
        self.w1 = data["w1"]
        self.b1 = data["b1"]
        self.w2 = data["w2"]
        self.b2 = data["b2"]
        self.w3 = data["w3"]
        self.b3 = data["b3"]
        self.h1_dim = len(self.w1)
        self.h2_dim = len(self.w2)
        self.in_dim = len(self.w1[0])


class DQNAgent:
    """
    Deep Phase-Competition Q-Network Agent (6 -> 64 -> 64 -> 1)
    Supports Acyclic Smart Phase Selection, Experience Replay, Target Network,
    and full Checkpoint Save/Resume.
    """

    def __init__(
        self,
        in_dim: int = 6,
        h1_dim: int = 64,
        h2_dim: int = 64,
        lr: float = 0.003,
        gamma: float = 0.88,
        epsilon_start: float = 0.85,
        epsilon_end: float = 0.02,
        epsilon_decay_per_ep: float = 0.92,
        buffer_size: int = 20000,
        batch_size: int = 32,
        target_update_freq: int = 40,
        seed: int = 42,
    ):
        self.in_dim = in_dim
        self.h1_dim = h1_dim
        self.h2_dim = h2_dim
        self.lr = lr
        self.gamma = gamma
        self.epsilon = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay_per_ep = epsilon_decay_per_ep
        self.batch_size = batch_size
        self.target_update_freq = target_update_freq
        self.rng = random.Random(seed)

        self.q_net = DeepPhaseMLP(in_dim, h1_dim, h2_dim, seed=seed)
        self.target_net = DeepPhaseMLP(in_dim, h1_dim, h2_dim, seed=seed)
        self.best_net = DeepPhaseMLP(in_dim, h1_dim, h2_dim, seed=seed)
        self.target_net.copy_from(self.q_net)
        self.best_net.copy_from(self.q_net)

        self.replay_buffer = deque(maxlen=buffer_size)
        self.train_steps = 0

    def select_action(
        self,
        phase_features: List[List[float]],
        valid_mask: List[bool] | None = None,
        evaluate: bool = False,
    ) -> int:
        num_phases = len(phase_features)
        valid_indices = (
            [i for i in range(num_phases) if valid_mask[i]]
            if valid_mask and any(valid_mask)
            else list(range(num_phases))
        )

        if not evaluate and self.rng.random() < self.epsilon:
            return self.rng.choice(valid_indices)

        q_values = self.q_net.predict_all_phases(phase_features)
        best_idx = valid_indices[0]
        best_q = q_values[best_idx]
        for idx in valid_indices[1:]:
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
        step_lr = self.lr / self.batch_size

        for phase_feats, action, reward, next_phase_feats, done in batch:
            x_act = phase_feats[action]
            q_pred, h1, h2 = self.q_net.forward_single_phase(x_act)
            next_qs = self.target_net.predict_all_phases(next_phase_feats)
            target_q = reward if done else reward + self.gamma * max(next_qs)

            td_error = q_pred - target_q
            grad_out = max(-1.5, min(1.5, td_error))
            total_loss += 0.5 * (td_error ** 2)

            w3_snap = self.q_net.w3[:]
            w2_snap = [row[:] for row in self.q_net.w2]

            # Update Layer 3 (h2 -> out)
            for j in range(self.h2_dim):
                self.q_net.w3[j] -= step_lr * grad_out * h2[j]
            self.q_net.b3 -= step_lr * grad_out

            # Backprop to Layer 2 (h1 -> h2)
            grad_h2 = [0.0] * self.h2_dim
            for j in range(self.h2_dim):
                if h2[j] > 0.0:
                    g2 = grad_out * w3_snap[j]
                    grad_h2[j] = g2
                    for i in range(self.h1_dim):
                        self.q_net.w2[j][i] -= step_lr * g2 * h1[i]
                    self.q_net.b2[j] -= step_lr * g2

            # Backprop to Layer 1 (x -> h1)
            for i in range(self.h1_dim):
                if h1[i] > 0.0:
                    g1 = sum(grad_h2[j] * w2_snap[j][i] for j in range(self.h2_dim))
                    if g1 != 0.0:
                        for k in range(self.in_dim):
                            self.q_net.w1[i][k] -= step_lr * g1 * x_act[k]
                        self.q_net.b1[i] -= step_lr * g1

        self.train_steps += 1
        if self.train_steps % self.target_update_freq == 0:
            self.target_net.copy_from(self.q_net)

        return total_loss / self.batch_size

    def decay_epsilon_episode(self):
        self.epsilon = max(self.epsilon_end, self.epsilon * self.epsilon_decay_per_ep)

    def save(self, path: str | Path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.q_net.to_dict(), indent=2), encoding="utf-8")

    def load(self, path: str | Path):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if "w3" in data:
            self.q_net.from_dict(data)
            self.target_net.copy_from(self.q_net)
            self.best_net.copy_from(self.q_net)

    def save_checkpoint(
        self,
        ckpt_path: str | Path,
        last_episode: int,
        total_episodes: int,
        best_wait: float,
        training_rows: List[Dict],
    ):
        ckpt_path = Path(ckpt_path)
        ckpt_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "last_episode": last_episode,
            "total_episodes": total_episodes,
            "best_wait": best_wait,
            "epsilon": self.epsilon,
            "train_steps": self.train_steps,
            "q_net": self.q_net.to_dict(),
            "target_net": self.target_net.to_dict(),
            "best_net": self.best_net.to_dict(),
            "training_rows": training_rows,
        }
        ckpt_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def load_checkpoint(self, ckpt_path: str | Path) -> Tuple[int, float, List[Dict]]:
        data = json.loads(Path(ckpt_path).read_text(encoding="utf-8"))
        self.epsilon = data["epsilon"]
        self.train_steps = data["train_steps"]
        self.q_net.from_dict(data["q_net"])
        self.target_net.from_dict(data["target_net"])
        self.best_net.from_dict(data["best_net"])
        return int(data["last_episode"]), float(data["best_wait"]), list(data["training_rows"])
