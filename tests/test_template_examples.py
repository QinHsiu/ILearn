import json
from pathlib import Path

from ilearn.data.build_pilot import LEGACY_KNOWLEDGE
from ilearn.data.importers.template_examples import supplement_legacy_from_templates

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def test_supplement_legacy_reaches_eight_per_kp():
    bank = {"frac_div": [{"id": "ex-1", "stem": "已有题", "answer": "2", "difficulty": "easy"}]}
    result = supplement_legacy_from_templates(
        bank,
        PILOT / "templates.json",
        LEGACY_KNOWLEDGE,
        min_per_kp=8,
    )
    for entry in LEGACY_KNOWLEDGE:
        kp_id = entry["id"]
        examples = result.get(kp_id, [])
        assert len(examples) >= 8, f"{kp_id} has {len(examples)} examples"
        assert all(ex.get("source") == "template" or ex["id"] == "ex-1" for ex in examples)


def test_template_examples_have_required_fields():
    result = supplement_legacy_from_templates(
        {},
        PILOT / "templates.json",
        [LEGACY_KNOWLEDGE[0]],
        min_per_kp=2,
    )
    examples = result["mult_3digit"]
    assert len(examples) >= 2
    for ex in examples:
        assert ex["stem"]
        assert ex["answer"]
        assert ex["label"]
        assert ex["source"] == "template"
