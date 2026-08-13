import json
from pathlib import Path

from ilearn.agents.assessment import AssessmentAgent
from ilearn.agents.curriculum import CurriculumAgent
from ilearn.agents.protocol import AgentContext, SessionPhase
from ilearn.core.schemas import StudentProfile
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def test_assessment_items_carry_curriculum_objective_ids():
    profile = StudentProfile(region="北京", grade=5, age=11)
    cur = CurriculumAgent(pilot_dir=PILOT).run(
        AgentContext(session_id="s1", phase=SessionPhase.ONBOARD, profile=profile)
    )
    citations = cur.payload.get("citations") or []
    assert citations, "pilot RAG should return citations"
    ctx = AgentContext(
        session_id="s1",
        phase=SessionPhase.ASSESS,
        profile=profile,
        metadata={"citations": citations, "weak_knowledge_ids": []},
    )
    paper = AssessmentAgent(PilotBeijingRenjiaoProvider(PILOT)).run(ctx).payload["paper"]
    assert any(item.curriculum_objective_ids for item in paper.items)
    assert all(item.source_refs for item in paper.items)
    first_ref = paper.items[0].source_refs[0]
    assert first_ref.example_id or first_ref.curriculum_objective_ids


def test_curriculum_sources_have_content_hash():
    data = json.loads((PILOT / "curriculum_sources.json").read_text(encoding="utf-8"))
    assert all(entry.get("content_hash") for entry in data)
