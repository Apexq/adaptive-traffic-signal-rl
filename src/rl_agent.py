"""
Deep Phase-Competition Q-Network (DQN) Agent for Acyclic Multi-Phase Signal Control
Architecture:
  - 2 Hidden Layers: 7 inputs -> 64 ReLU -> 64 ReLU -> 1 Q-value output per phase
  - 100% Random He Initialization (No manual warm-start weights)
  - Experience Replay Buffer + Target Network + Clipped TD Gradients
  - Full Checkpoint Save & Resume Support (can pause/stop at any episode and resume later)
"""

import copy
import json
import math
import random
from collections import deque
from pathlib import Path
from typing import Dict, List, Tuple
from runtime import FEATURE_DIM, SCHEMA_VERSION, atomic_json


class DeepPhaseMLP:
    """Three-layer Deep MLP (7 -> 64 -> 64 -> 1) with ReLU activations scoring any signal phase."""

    def __init__(self, in_dim: int = FEATURE_DIM, h1_dim: int = 64, h2_dim: int = 64, seed: int = 42):
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
        if len(x) != self.in_dim or not all(math.isfinite(v) for v in x):
            raise ValueError("Invalid feature shape or non-finite observation")
        h1 = []
        for i in range(self.h1_dim):
            z1 = self.b1[i] + sum(w * xi for w, xi in zip(self.w1[i], x))
            h1.append(z1 if z1 > 0.0 else 0.0)

        h2 = []
        for j in range(self.h2_dim):
            z2 = self.b2[j] + sum(w * h1i for w, h1i in zip(self.w2[j], h1))
            h2.append(z2 if z2 > 0.0 else 0.0)

        q_val = self.b3 + sum(w * h2j for w, h2j in zip(self.w3, h2))
        if not math.isfinite(q_val):
            raise FloatingPointError("Non-finite Q value")
        return q_val, h1, h2

    def predict_all_phases(self, phase_features: List[List[float]]) -> List[float]:
        return [self.forward_single_phase(x)[0] for x in phase_features]

    def copy_from(self, other: "DeepPhaseMLP"):
        self.in_dim, self.h1_dim, self.h2_dim = other.in_dim, other.h1_dim, other.h2_dim
        self.w1 = [row[:] for row in other.w1]
        self.b1 = other.b1[:]
        self.w2 = [row[:] for row in other.w2]
        self.b2 = other.b2[:]
        self.w3 = other.w3[:]
        self.b3 = other.b3

    def to_dict(self) -> dict:
        return {
            "arch": f"{self.in_dim}-{self.h1_dim}-{self.h2_dim}-1",
            "w1": self.w1,
            "b1": self.b1,
            "w2": self.w2,
            "b2": self.b2,
            "w3": self.w3,
            "b3": self.b3,
        }

    def from_dict(self, data: dict):
        required = {"w1", "b1", "w2", "b2", "w3", "b3"}
        if not required <= data.keys():
            raise ValueError("Unsupported/legacy network architecture; retrain with schema v2")
        matrices = ((data["w1"], self.h1_dim, self.in_dim),
                    (data["w2"], self.h2_dim, self.h1_dim))
        for matrix, rows, cols in matrices:
            if len(matrix) != rows or any(len(row) != cols for row in matrix):
                raise ValueError("Checkpoint layer dimensions do not match the agent")
        for key, length in (("b1", self.h1_dim), ("b2", self.h2_dim), ("w3", self.h2_dim)):
            if len(data[key]) != length:
                raise ValueError("Checkpoint vector dimensions do not match the agent")
        values = [v for m, _, _ in matrices for row in m for v in row]
        values += data["b1"] + data["b2"] + data["w3"] + [data["b3"]]
        if not all(math.isfinite(v) for v in values):
            raise ValueError("Non-finite checkpoint weights")
        for key in required:
            setattr(self, key, copy.deepcopy(data[key]))



class DQNAgent:
    """
    Deep Phase-Competition Q-Network Agent (7 -> 64 -> 64 -> 1)
    Supports Acyclic Smart Phase Selection, Experience Replay, Target Network,
    and full Checkpoint Save/Resume.
    """

    def __init__(
        self,
        in_dim: int = FEATURE_DIM,
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
        if min(in_dim, h1_dim, h2_dim, batch_size, buffer_size, target_update_freq) <= 0:
            raise ValueError("Dimensions, capacities and update intervals must be positive")
        if (buffer_size < batch_size or not 0 < gamma <= 1 or not math.isfinite(lr) or lr < 0
                or not 0 <= epsilon_end <= epsilon_start <= 1 or not 0 < epsilon_decay_per_ep <= 1):
            raise ValueError("Invalid training hyperparameters")
        self.metadata = {}
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
        self._validate_features(phase_features)
        valid_indices = self._valid_indices(phase_features, valid_mask)

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

    def _validate_features(self, features):
        if not features or any(
            not isinstance(row, (list, tuple)) or len(row) != self.in_dim
            or not all(math.isfinite(v) for v in row) for row in features
        ):
            raise ValueError("Expected nonempty phase-by-feature finite observations")

    @staticmethod
    def _valid_indices(features, mask):
        if mask is None:
            return list(range(len(features)))
        if len(mask) != len(features) or not all(type(v) is bool for v in mask):
            raise ValueError("Invalid action mask")
        indices = [i for i, valid in enumerate(mask) if valid]
        if not indices:
            raise ValueError("No legal action in nonterminal state")
        return indices

    def store_transition(self, phase_features, action, reward, next_phase_features,
                         terminated, next_mask, truncated=False, duration=5.0):
        self._validate_features(phase_features)
        self._validate_features(next_phase_features)
        if not 0 <= action < len(phase_features):
            raise ValueError("Action out of bounds")
        if not math.isfinite(reward) or not math.isfinite(duration) or duration <= 0:
            raise ValueError("Invalid reward or transition duration")
        if not terminated:
            self._valid_indices(next_phase_features, next_mask)
        self.replay_buffer.append(copy.deepcopy((
            phase_features, action, reward, next_phase_features, bool(terminated),
            next_mask, bool(truncated), duration,
        )))

    def bellman_target(self, reward, next_features, terminated, next_mask, duration):
        if terminated:
            return reward
        next_qs = self.target_net.predict_all_phases(next_features)
        indices = self._valid_indices(next_features, next_mask)
        return reward + self.gamma ** (duration / 5.0) * max(next_qs[i] for i in indices)

    def update(self) -> float:
        if len(self.replay_buffer) < self.batch_size:
            return 0.0

        batch = self.rng.sample(self.replay_buffer, self.batch_size)
        total_loss = 0.0
        step_lr = self.lr / self.batch_size

        for phase_feats, action, reward, next_phase_feats, terminated, next_mask, truncated, duration in batch:
            x_act = phase_feats[action]
            q_pred, h1, h2 = self.q_net.forward_single_phase(x_act)
            target_q = self.bellman_target(reward, next_phase_feats, terminated, next_mask, duration)

            td_error = q_pred - target_q
            grad_out = max(-1.5, min(1.5, td_error))
            if not math.isfinite(td_error) or abs(td_error) > 1e100:
                raise FloatingPointError("Unstable TD target; refusing a corrupt update")
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

    def _hyperparameters(self):
        keys = ("in_dim", "h1_dim", "h2_dim", "lr", "gamma", "epsilon_end",
                "epsilon_decay_per_ep", "batch_size", "target_update_freq")
        return {**{k: getattr(self, k) for k in keys}, "buffer_size": self.replay_buffer.maxlen}

    def save(self, path, best=False):
        atomic_json(path, {
            "schema_version": SCHEMA_VERSION, "metadata": self.metadata,
            "hyperparameters": self._hyperparameters(),
            "q_net": (self.best_net if best else self.q_net).to_dict(),
        })

    def _read_payload(self, path):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if data.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("Legacy/incompatible model: schema v2 requires fresh training")
        if self.metadata and data.get("metadata") != self.metadata:
            raise ValueError("Model scenario or experiment configuration mismatch")
        return data

    def load(self, path):
        data = self._read_payload(path)
        network = DeepPhaseMLP(self.in_dim, self.h1_dim, self.h2_dim)
        network.from_dict(data["q_net"])
        self.q_net.copy_from(network)
        self.target_net.copy_from(network)
        self.best_net.copy_from(network)
        self.metadata = data["metadata"]

    def save_checkpoint(self, ckpt_path, last_episode, total_episodes, best_score, training_rows):
        atomic_json(ckpt_path, {
            "schema_version": SCHEMA_VERSION, "metadata": self.metadata,
            "hyperparameters": self._hyperparameters(),
            "last_episode": last_episode, "total_episodes": total_episodes,
            "best_score": best_score, "epsilon": self.epsilon,
            "train_steps": self.train_steps,
            "q_net": self.q_net.to_dict(), "target_net": self.target_net.to_dict(),
            "best_net": self.best_net.to_dict(), "training_rows": training_rows,
            "replay_buffer": list(self.replay_buffer), "rng_state": self.rng.getstate(),
        })

    def load_checkpoint(self, ckpt_path):
        data = self._read_payload(ckpt_path)
        if data["hyperparameters"] != self._hyperparameters():
            raise ValueError("Resume hyperparameters differ from checkpoint")
        # Validate on a temporary agent; never partially mutate a live learner.
        candidate = DQNAgent(**data["hyperparameters"])
        for name in ("q_net", "target_net", "best_net"):
            getattr(candidate, name).from_dict(data[name])
        for transition in data["replay_buffer"]:
            candidate.store_transition(*transition)
        def tuples(value):
            return tuple(map(tuples, value)) if isinstance(value, list) else value
        candidate.rng.setstate(tuples(data["rng_state"]))
        if (not 0 <= data["epsilon"] <= 1 or data["train_steps"] < 0
                or not math.isfinite(data["best_score"]) or data["last_episode"] < 0):
            raise ValueError("Invalid checkpoint training counters")
        candidate.epsilon = data["epsilon"]
        candidate.train_steps = data["train_steps"]
        candidate.metadata = data["metadata"]
        self.__dict__.update(candidate.__dict__)
        return int(data["last_episode"]), float(data["best_score"]), list(data["training_rows"])
