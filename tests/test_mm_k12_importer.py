from pathlib import Path

from ilearn.data.importers.mm_k12 import iter_mm_k12_records, to_example_entry
from ilearn.data.kp_ids import load_alias_map

FIX = Path(__file__).parent / "fixtures" / "mm_k12_tiny.jsonl"
ALIAS = Path(__file__).resolve().parents[1] / "data" / "curriculum" / "kp_alias.json"


def test_iter_mm_k12_records():
    rows = list(iter_mm_k12_records(FIX))
    assert len(rows) == 6


def test_to_example_entry_maps_knowledge_id():
    alias = load_alias_map(ALIAS)
    rows = list(iter_mm_k12_records(FIX))
    mapped = [to_example_entry(r, alias) for r in rows]
    mapped = [m for m in mapped if m]
    assert mapped
    kid, ex = mapped[0]
    assert kid
    assert ex["stem"]
    assert ex["answer"]
    assert ex["source"] == "mm_k12"


def test_english_area_question_maps_rect_area():
    alias = load_alias_map(ALIAS)
    record = {
        "id": "en-1",
        "question": "A rectangle has length 8 cm and width 5 cm. Find the area.",
        "answer": "40",
    }
    mapped = to_example_entry(record, alias)
    assert mapped is not None
    assert mapped[0] == "rect_area"
