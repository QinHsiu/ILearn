from pathlib import Path

from ilearn.agents.diagnosis import PortraitUpdater
from ilearn.core.schemas import GradeResult, LearnerPortrait, MasteryRecord
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def test_probe_lane_does_not_update_practice_score():
    portrait = LearnerPortrait(student_key="bj_g5")
    portrait.mastery_records["frac_add_same"] = MasteryRecord(
        practice_score=0.6,
        probe_mastery=0.4,
    )
    grade = GradeResult(
        item_id="q1",
        final_correct=True,
        knowledge_ids=["frac_add_same"],
        lane="probe",
    )
    updated = PortraitUpdater.update(
        portrait,
        [grade],
        session_id="s1",
        curriculum=PilotBeijingRenjiaoProvider(PILOT),
        grade=5,
    )
    rec = updated.mastery_records["frac_add_same"]
    assert rec.practice_score == 0.6
    assert rec.probe_mastery > 0.4


def test_practice_lane_does_not_update_probe_mastery():
    portrait = LearnerPortrait(student_key="bj_g5")
    portrait.mastery_records["frac_add_same"] = MasteryRecord(
        practice_score=0.4,
        probe_mastery=0.7,
    )
    grade = GradeResult(
        item_id="q1",
        final_correct=True,
        knowledge_ids=["frac_add_same"],
        lane="practice",
    )
    updated = PortraitUpdater.update(
        portrait,
        [grade],
        session_id="s1",
        curriculum=PilotBeijingRenjiaoProvider(PILOT),
        grade=5,
    )
    rec = updated.mastery_records["frac_add_same"]
    assert rec.probe_mastery == 0.7
    assert rec.practice_score > 0.4
