from pathlib import Path

from ilearn.agents.eval_agent import EvalAgent

FIXTURES = Path(__file__).resolve().parents[1] / "data" / "eval"


def test_eval_agent_runs_step_grading_offline():
    agent = EvalAgent(fixtures_dir=FIXTURES, llm=None)
    report = agent.run_step_grading()
    assert report["total"] >= 10
    assert "step_f1" in report
    assert report["agents_invoked"] == ["practice"]
