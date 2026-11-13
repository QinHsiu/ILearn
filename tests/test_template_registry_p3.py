"""P3: lifecycle template registry."""

from ilearn.orchestration.template_registry import (
    AdultCompanionTemplate,
    K12MathHostTemplate,
    TemplateRegistry,
)


def test_k12_selected_for_primary_assess():
    reg = TemplateRegistry()
    t = reg.select("primary", "assess_remediate")
    assert t.template_id == "k12_math_host"
    assert t.initial_state() == "onboard"
    nxt = t.transitions("onboard", "start_assess")
    assert nxt == "assess"


def test_adult_selected_for_career_companion():
    reg = TemplateRegistry()
    t = reg.select("career", "companion_chat")
    assert isinstance(t, AdultCompanionTemplate)
    assert t.initial_state() == "companion"


def test_unknown_stage_raises():
    reg = TemplateRegistry()
    try:
        reg.select("martian", "x")
        assert False
    except LookupError:
        pass


def test_k12_template_registered():
    assert K12MathHostTemplate().template_id == "k12_math_host"
