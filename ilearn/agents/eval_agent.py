"""Eval agent — runs offline step-grading benchmarks via PracticeAgent."""

from __future__ import annotations

from pathlib import Path

from ilearn.agents.protocol import AgentContext, AgentResult
from ilearn.eval.runner import run_step_grading_benchmark
from ilearn.providers.llm import LLMClient

_DEFAULT_FIXTURE_NAME = "step_grading_fixtures.json"


class EvalAgent:
    name = "eval"

    def __init__(self, fixtures_dir: Path, llm: LLMClient | None = None) -> None:
        self._fixtures_dir = fixtures_dir
        self._llm = llm

    def run_step_grading(self, fixtures_path: Path | None = None) -> dict:
        path = fixtures_path or (self._fixtures_dir / _DEFAULT_FIXTURE_NAME)
        return run_step_grading_benchmark(path, llm=self._llm)

    def run(self, ctx: AgentContext) -> AgentResult:
        return AgentResult(
            phase=ctx.phase,
            payload={"eval_report": self.run_step_grading()},
        )
