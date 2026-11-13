"""StateMachineTemplate + registry + HostStateMachineBackend.advance (P3)."""

import pytest

from ilearn.orchestration.backend import HostStateMachineBackend, UnexpectedTransition
from ilearn.orchestration.k12_template import K12MathHostTemplate, K12Template
from ilearn.orchestration.registry import TemplateRegistry


def test_k12_template_wraps_existing_flow():
    t = K12Template()
    assert t.transitions("ONBOARD", "onboard.completed") == "ASSESS"
    assert t.transitions("PLAN", "plan.completed") == "PRACTICE_LOOP"
    assert t.transitions("ONBOARD", "unknown") is None


def test_registry_selects_by_stage():
    reg = TemplateRegistry([K12Template()])
    assert reg.select("k12", "exam_prep").template_id == "k12-standard"
    with pytest.raises(LookupError):
        reg.select("elder", "hobby")


def test_host_backend_advance_uses_template():
    backend = HostStateMachineBackend(template=K12MathHostTemplate())
    assert backend.advance("onboard", "start_assess") == "assess"
    with pytest.raises(UnexpectedTransition):
        backend.advance("onboard", "nope")


def test_host_backend_switches_template():
    backend = HostStateMachineBackend(template=K12Template())
    assert backend.advance("ONBOARD", "onboard.completed") == "ASSESS"
