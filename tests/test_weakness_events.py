from pathlib import Path

from ilearn.core.diagnosis import PortraitUpdater
from ilearn.core.schemas import GradeResult, KnowledgeEvidence, LearnerPortrait
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def test_repeated_errors_same_knowledge_collapse_to_one_weakness_event_per_session():
    portrait = LearnerPortrait(student_key="bj_g5")
    grades = [
        GradeResult(
            item_id="q1",
            final_correct=False,
            error_tags=["calc_error"],
            knowledge_ids=["frac_add_same"],
        ),
        GradeResult(
            item_id="q2",
            final_correct=False,
            error_tags=["concept_gap"],
            knowledge_ids=["frac_add_same"],
        ),
    ]
    updated = PortraitUpdater.update(
        portrait,
        grades,
        session_id="s1",
        curriculum=PilotBeijingRenjiaoProvider(PILOT),
        grade=5,
    )
    assert len(updated.weakness_events) == 1
    event = updated.weakness_events[0]
    assert event.knowledge_id == "frac_add_same"
    assert event.error_tag == "concept_gap"
    assert event.session_id == "s1"
    assert len(updated.weakness_log) == 2


def test_weakness_events_separate_across_sessions():
    portrait = LearnerPortrait(student_key="bj_g5")
    grade = GradeResult(
        item_id="q1",
        final_correct=False,
        error_tags=["calc_error"],
        knowledge_ids=["frac_add_same"],
    )
    PortraitUpdater.update(
        portrait,
        [grade],
        session_id="s1",
        curriculum=PilotBeijingRenjiaoProvider(PILOT),
        grade=5,
    )
    PortraitUpdater.update(
        portrait,
        [grade],
        session_id="s2",
        curriculum=PilotBeijingRenjiaoProvider(PILOT),
        grade=5,
    )
    assert len(portrait.weakness_events) == 2
    assert {e.session_id for e in portrait.weakness_events} == {"s1", "s2"}


def test_weakness_event_aggregates_max_confidence_from_evidence():
    portrait = LearnerPortrait(student_key="bj_g5")
    ev_low = KnowledgeEvidence(
        session_id="s1",
        item_id="q1",
        knowledge_id="frac_add_same",
        lane="probe",
        correct=False,
        error_tag="calc_error",
        confidence=0.5,
    )
    ev_high = KnowledgeEvidence(
        session_id="s1",
        item_id="q2",
        knowledge_id="frac_add_same",
        lane="probe",
        correct=False,
        error_tag="misread",
        confidence=0.9,
    )
    PortraitUpdater.update(
        portrait,
        [],
        session_id="s1",
        curriculum=PilotBeijingRenjiaoProvider(PILOT),
        grade=5,
        evidence=[ev_low, ev_high],
    )
    assert len(portrait.weakness_events) == 1
    assert portrait.weakness_events[0].confidence == 0.9
    assert portrait.weakness_events[0].error_tag == "misread"
    assert portrait.weakness_events[0].evidence_id == ev_high.evidence_id
