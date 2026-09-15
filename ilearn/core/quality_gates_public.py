"""P10 quality-gate visibility for Trust / capabilities."""

from __future__ import annotations

from typing import Any


def quality_gates_payload() -> dict[str, Any]:
    """Public, non-secret status of product quality gates."""
    gates = [
        {
            "id": "p1_citation",
            "name": "课标引用 fail-closed",
            "status": "enforced",
            "suite": "tests/eval_winbars/test_p1_citation_fail_closed.py",
        },
        {
            "id": "p2_mastery",
            "name": "提示后做对不计探针掌握",
            "status": "enforced",
            "suite": "tests/eval_winbars/test_p2_mastery_rigor.py",
        },
        {
            "id": "p3_no_leak",
            "name": "辅导不泄终答",
            "status": "enforced",
            "suite": "tests/eval_winbars/test_p3_no_answer_leak.py",
        },
        {
            "id": "agent_quality_gate",
            "name": "组卷/诊断/计划质量门 + 降级",
            "status": "enforced",
            "suite": "ilearn/core/quality_gate.py",
        },
        {
            "id": "pilot_data",
            "name": "试点课标数据质量",
            "status": "enforced",
            "suite": "tests/test_pilot_data_quality.py",
        },
    ]
    return {
        "product": "ILearn",
        "eval_suite": "tests/eval_winbars",
        "gates": gates,
        "summary": {
            "total": len(gates),
            "enforced": sum(1 for g in gates if g["status"] == "enforced"),
        },
        "how_to_verify": [
            "pytest tests/eval_winbars -q",
            "GET /quality-gates",
            "GET /capabilities",
        ],
    }
