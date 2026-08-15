from ilearn.core.diagnostic_rules import (
    ERROR_TAG_TO_TYPE,
    ErrorType,
    classify_solo_from_grades,
    enrich_diagnosis,
)
from ilearn.core.schemas import GradeResult, KnowledgeMastery


def test_error_tag_mapping():
    assert ERROR_TAG_TO_TYPE["concept_gap"] == ErrorType.CONCEPTUAL
    assert ERROR_TAG_TO_TYPE["calc_error"] == ErrorType.PROCEDURAL
    assert ERROR_TAG_TO_TYPE["misread"] == ErrorType.READING
    assert ERROR_TAG_TO_TYPE["method_wrong"] == ErrorType.TRANSFER
    assert ERROR_TAG_TO_TYPE["incomplete"] == ErrorType.PROCEDURAL


def test_solo_prestructural_when_all_wrong_empty_tags():
    grades = [
        GradeResult(item_id="q1", final_correct=False, error_tags=[]),
        GradeResult(item_id="q2", final_correct=False, error_tags=[]),
    ]
    assert classify_solo_from_grades(grades) == "prestructural"


def test_solo_unistructural_when_wrong_with_tags():
    grades = [
        GradeResult(item_id="q1", final_correct=False, error_tags=["concept_gap"]),
    ]
    assert classify_solo_from_grades(grades) == "unistructural"


def test_solo_multistructural_when_mostly_correct():
    grades = [
        GradeResult(item_id="q1", final_correct=True, error_tags=[]),
        GradeResult(item_id="q2", final_correct=True, error_tags=[]),
        GradeResult(item_id="q3", final_correct=False, error_tags=["calc_error"]),
    ]
    assert classify_solo_from_grades(grades) == "multistructural"


def test_enrich_diagnosis_flags_and_suffix():
    grades = [
        GradeResult(
            item_id="q1",
            final_correct=False,
            error_tags=["concept_gap"],
            knowledge_ids=["k1"],
        ),
    ]
    mastery = [
        KnowledgeMastery(
            knowledge_id="k1",
            score_rate=0.0,
            error_tag_counts={"concept_gap": 1},
            level="weak",
            item_ids=["q1"],
        )
    ]
    enrichment = enrich_diagnosis(knowledge_mastery=mastery, grades=grades)
    assert "solo:unistructural" in enrichment.flags
    assert "rule:concept_gap" in enrichment.flags
    assert "k1" in enrichment.why_suffix_by_knowledge_id
    assert enrichment.why_suffix_by_knowledge_id["k1"]


def test_enrich_empty_grades():
    enrichment = enrich_diagnosis(knowledge_mastery=[], grades=[])
    assert enrichment.flags == []
    assert enrichment.why_suffix_by_knowledge_id == {}
