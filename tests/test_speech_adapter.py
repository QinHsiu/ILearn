"""SpeechAssessmentAdapter is a replaceable perception adapter."""

from pathlib import Path

import pytest

from ilearn.agents.practice import PracticeAgent
from ilearn.core.schemas import AssessmentItem, AssessmentPaper
from ilearn.perception.adapter import PerceptionOutput
from ilearn.perception.speech import SpeechAssessmentAdapter


def test_speech_adapter_requires_backend_by_default(tmp_path: Path):
    adapter = SpeechAssessmentAdapter()
    audio = tmp_path / "a.wav"
    audio.write_bytes(b"RIFF")
    with pytest.raises(NotImplementedError):
        adapter.transcribe(str(audio))


def test_speech_adapter_with_injectable_backend(tmp_path: Path):
    def fake_asr(path: str) -> PerceptionOutput:
        return PerceptionOutput(
            text="2",
            source_type="speech",
            confidence=0.91,
            raw_ref=f"item:p1|{path}",
        )

    adapter = SpeechAssessmentAdapter(transcribe_fn=fake_asr)
    audio = tmp_path / "utt.wav"
    audio.write_bytes(b"RIFF")
    out = adapter.transcribe(str(audio))
    assert out.source_type == "speech"
    assert out.text == "2"

    agent = PracticeAgent(llm=None)
    item = AssessmentItem(
        id="p1",
        stem="1+1=?",
        type="fill",
        difficulty="easy",
        knowledge_ids=["dec_mult"],
        answer_key="2",
    )
    paper = AssessmentPaper(curriculum_label="test", grade=5, items=[item])
    grades = agent.grade_perception_outputs(paper, [out])
    assert grades[0].final_correct is True
    assert grades[0].receipt is not None
    assert grades[0].receipt.ocr_confidence == 0.91


def test_citation_carries_region_edition_fields():
    from ilearn.core.schemas import CurriculumCitation

    c = CurriculumCitation(
        citation_id="c1",
        title="小数乘法",
        excerpt="…",
        source_label="北京·人教",
        region="北京",
        edition="人教",
    )
    assert c.region == "北京"
    assert c.edition == "人教"
