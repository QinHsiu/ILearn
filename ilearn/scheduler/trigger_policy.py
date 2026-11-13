"""Thompson-sampling trigger priority — pure Beta-Bernoulli bandit (no LLM)."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Literal

Trigger = Literal["spaced_repetition", "engagement_drop", "goal_deviation"]


@dataclass
class BetaArm:
    """每种触发类型维护一个 Beta(alpha, beta) 分布。

    alpha = 成功消费次数 + 1，beta = 失败消费次数 + 1（Laplace 平滑）。
    """

    alpha: float = 1.0
    beta: float = 1.0

    def sample(self, rng: random.Random) -> float:
        return rng.betavariate(self.alpha, self.beta)

    def update(self, success: bool) -> None:
        if success:
            self.alpha += 1.0
        else:
            self.beta += 1.0

    @property
    def mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)


def _default_arms() -> dict[Trigger, BetaArm]:
    return {
        "spaced_repetition": BetaArm(),
        "engagement_drop": BetaArm(),
        "goal_deviation": BetaArm(),
    }


@dataclass
class TriggerPolicy:
    """Thompson 采样决定本次 scan 中触发类型的优先级排序。

    纯统计、无参数化模型、可序列化到 event_log 后重放。
    """

    arms: dict[Trigger, BetaArm] = field(default_factory=_default_arms)
    rng_seed: int | None = None

    def _rng(self) -> random.Random:
        return (
            random.Random(self.rng_seed)
            if self.rng_seed is not None
            else random.Random()
        )

    def rank(self, candidates: list[Trigger]) -> list[Trigger]:
        """按 Thompson 采样值降序排列候选触发类型。"""
        rng = self._rng()
        return sorted(candidates, key=lambda t: self.arms[t].sample(rng), reverse=True)

    def update(self, trigger: Trigger, success: bool) -> None:
        self.arms[trigger].update(success)

    def snapshot(self) -> dict:
        """写入 event_log 的可审计快照。"""
        arms = {
            t: {"alpha": a.alpha, "beta": a.beta, "mean": a.mean}
            for t, a in self.arms.items()
        }
        return {"arms": arms, "rng_seed": self.rng_seed}

    @classmethod
    def from_snapshot(cls, snap: dict, *, rng_seed: int | None = None) -> TriggerPolicy:
        # Accept both nested {"arms": ...} and flat legacy {trigger: {alpha,beta}}
        if "arms" in snap:
            arms_snap = snap["arms"]
            seed = rng_seed if rng_seed is not None else snap.get("rng_seed")
        else:
            arms_snap = snap
            seed = rng_seed
        policy = cls(rng_seed=seed)
        for t, v in arms_snap.items():
            if not isinstance(v, dict) or "alpha" not in v:
                continue
            policy.arms[t] = BetaArm(alpha=float(v["alpha"]), beta=float(v["beta"]))  # type: ignore[index]
        return policy
