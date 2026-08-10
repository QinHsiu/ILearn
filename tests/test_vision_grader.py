from unittest.mock import MagicMock, patch

from ilearn.agents.practice import PracticeAgent
from ilearn.agents.protocol import AgentContext, SessionPhase
from ilearn.core.grading import VisionGrader
from ilearn.core.schemas import (
    AssessmentItem,
    AssessmentPaper,
    ImageAnswer,
    StudentAnswer,
    StudentProfile,
)
from ilearn.providers.llm import LLMClient


def _constructed_item() -> AssessmentItem:
    return AssessmentItem(
        id="c1",
        stem="计算 12+8",
        type="constructed",
        difficulty="easy",
        knowledge_ids=["g5_add"],
        answer_key="20",
        rubric_steps=["列式", "计算", "写答"],
    )


def test_vision_grader_offline_degrades_without_llm():
    result = VisionGrader(llm=None).grade_image(
        _constructed_item(),
        image_base64="aGVsbG8=",
        mime_type="image/png",
    )

    assert result.grading_degraded is True
    assert result.item_id == "c1"
    assert len(result.step_results) >= 1


class _SuccessfulVisionLLM:
    def available(self) -> bool:
        return False

    def vision_available(self) -> bool:
        return True

    def grade_image_json(
        self, system: str, image_base64: str, mime_type: str, user: str
    ) -> dict:
        return {
            "final_correct": True,
            "steps": ["12+8=20"],
            "step_results": [
                {
                    "step_index": 0,
                    "step_text": "12+8=20",
                    "status": "correct",
                    "comment": "计算正确",
                }
            ],
            "error_tags": [],
            "knowledge_ids": ["g5_add"],
            "hint_level_suggestion": "none",
        }


def test_vision_grader_parses_available_vision_result():
    result = VisionGrader(llm=_SuccessfulVisionLLM()).grade_image(
        _constructed_item(),
        image_base64="aGVsbG8=",
        mime_type="image/png",
    )

    assert result.final_correct is True
    assert result.steps == ["12+8=20"]
    assert result.grading_degraded is False


@patch("ilearn.providers.llm.OpenAI")
def test_grade_image_json_sends_data_uri_to_vision_model(mock_openai, monkeypatch):
    monkeypatch.setenv("ILEARN_VISION_MODEL", "vision-test-model")
    response = MagicMock()
    response.choices[0].message.content = '{"final_correct": true}'
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = response
    mock_openai.return_value = mock_client

    client = LLMClient(api_key="sk-test", model="text-test-model")
    result = client.grade_image_json(
        "grade image",
        image_base64="aGVsbG8=",
        mime_type="image/png",
        user="question and rubric",
    )

    assert result == {"final_correct": True}
    mock_client.chat.completions.create.assert_called_once_with(
        model="vision-test-model",
        messages=[
            {"role": "system", "content": "grade image"},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "question and rubric"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": "data:image/png;base64,aGVsbG8="
                        },
                    },
                ],
            },
        ],
    )


def test_practice_agent_image_grade_wins_for_same_item_id():
    item = _constructed_item()
    paper = AssessmentPaper(
        items=[item],
        grade=5,
        curriculum_label="北京·人教·小学数学",
    )
    ctx = AgentContext(
        session_id="s1",
        phase=SessionPhase.GRADE,
        profile=StudentProfile(region="北京", grade=5, age=11),
        paper=paper,
        answers=[StudentAnswer(item_id="c1", answer_text="19")],
        image_answers=[
            ImageAnswer(
                item_id="c1",
                image_base64="aGVsbG8=",
                mime_type="image/png",
            )
        ],
    )

    result = PracticeAgent(llm=_SuccessfulVisionLLM()).run(ctx)

    assert len(result.payload["grades"]) == 1
    assert result.payload["grades"][0].item_id == "c1"
    assert result.payload["grades"][0].final_correct is True
