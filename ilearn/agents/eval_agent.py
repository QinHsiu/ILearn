"""Eval agent — runs offline step-grading benchmarks via PracticeAgent."""

from __future__ import annotations

from pathlib import Path

from ilearn.agents.protocol import AgentContext, AgentResult
from ilearn.eval.mathtutorbench_tasks import (
    run_mistake_correction_benchmark,
    run_mistake_location_benchmark,
    run_scaffolding_benchmark,
)
from ilearn.eval.runner import run_step_grading_benchmark
from ilearn.eval.tutor_gym_profile import run_completeness_benchmark
from ilearn.providers.llm import LLMClient

_DEFAULT_FIXTURE_NAME = "step_grading_fixtures.json"
_MISTAKE_LOCATION_FIXTURE = "mistake_location_fixtures.json"
_MISTAKE_CORRECTION_FIXTURE = "mistake_correction_fixtures.json"
_SCAFFOLDING_FIXTURE = "scaffolding_fixtures.json"
_COMPLETENESS_PROFILES = "step_completeness_profiles.json"


class EvalAgent:
    name = "eval"

    def __init__(self, fixtures_dir: Path, llm: LLMClient | None = None) -> None:
        self._fixtures_dir = fixtures_dir
        self._llm = llm

    def run_step_grading(self, fixtures_path: Path | None = None) -> dict:
        path = fixtures_path or (self._fixtures_dir / _DEFAULT_FIXTURE_NAME)
        return run_step_grading_benchmark(path, llm=self._llm)

    def run_mistake_location(self, fixtures_path: Path | None = None) -> dict:
        path = fixtures_path or (self._fixtures_dir / _MISTAKE_LOCATION_FIXTURE)
        return run_mistake_location_benchmark(path, llm=self._llm)

    def run_mistake_correction(self, fixtures_path: Path | None = None) -> dict:
        path = fixtures_path or (self._fixtures_dir / _MISTAKE_CORRECTION_FIXTURE)
        return run_mistake_correction_benchmark(path, llm=self._llm)

    def run_scaffolding(self, fixtures_path: Path | None = None) -> dict:
        path = fixtures_path or (self._fixtures_dir / _SCAFFOLDING_FIXTURE)
        return run_scaffolding_benchmark(path, llm=self._llm)

    def run_completeness(self, profiles_path: Path | None = None) -> dict:
        path = profiles_path or (self._fixtures_dir / _COMPLETENESS_PROFILES)
        return run_completeness_benchmark(path, llm=self._llm)

    def run(self, ctx: AgentContext) -> AgentResult:
        benchmark = ctx.metadata.get("benchmark", "step_grading")
        if benchmark == "mistake_location":
            report = self.run_mistake_location()
        elif benchmark == "mistake_correction":
            report = self.run_mistake_correction()
        elif benchmark == "scaffolding":
            report = self.run_scaffolding()
        elif benchmark == "completeness":
            report = self.run_completeness()
        else:
            report = self.run_step_grading()
        return AgentResult(
            phase=ctx.phase,
            payload={"eval_report": report},
        )
