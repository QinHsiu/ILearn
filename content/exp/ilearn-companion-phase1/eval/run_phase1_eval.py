"""Phase-1 ultimate Companion gates. Run from ILearn root."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from ilearn.agents.companion import CompanionAgent
from ilearn.core.schemas import SessionPhase, SessionState, StudentProfile
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider

EVAL_DIR = Path(__file__).resolve().parent
EXP_DIR = EVAL_DIR.parent
OUT = EXP_DIR / "metrics" / "summary.json"


def main() -> int:
    agent = CompanionAgent(PilotBeijingRenjiaoProvider(ROOT / "data" / "pilot"), llm=None)
    rows = [
        json.loads(line)
        for line in (EVAL_DIR / "suite.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    details = []
    intents_ok = 0
    plan_ok = 0
    predict_ok = 0
    cite_need = 0
    cite_ok = 0

    for row in rows:
        grade = int(row.get("grade") or 5)
        life_stage = row.get("life_stage")
        profile = StudentProfile(
            region="北京",
            grade=grade,
            age=min(18, max(6, grade + 6)),
            life_stage=life_stage,
        )
        session = SessionState(
            session_id=f"ph1-{row['id']}",
            profile=profile,
            phase=SessionPhase.IDLE,
        )
        reply = agent.chat(session, row["message"])
        intent_match = reply.intent == row["expect_intent"]
        if intent_match:
            intents_ok += 1
        week = False
        risk = False
        cited = bool(reply.citations)
        if row.get("require_week"):
            week = "周一" in (reply.reply or "") and bool(
                session.metadata.get("companion_week_plan")
            )
            if week:
                plan_ok = 1
        if row.get("require_risk"):
            risk = "风险" in (reply.reply or "") and bool(
                session.metadata.get("companion_risk_forecast")
            )
            if risk:
                predict_ok = 1
        if row.get("require_cite"):
            cite_need += 1
            if cited:
                cite_ok += 1
        details.append(
            {
                "id": row["id"],
                "intent_match": intent_match,
                "got": reply.intent,
                "week": week,
                "risk": risk,
                "citations": len(reply.citations or []),
            }
        )

    five_intents_ok = 1.0 if intents_ok == len(rows) else intents_ok / len(rows)
    # Require the five capability probes (first 5 rows) exact
    first5 = details[:5]
    five_cap = 1.0 if all(d["intent_match"] for d in first5) else 0.0

    p1 = subprocess.run(
        [sys.executable, str(ROOT / "content/exp/ilearn-companion-p1/eval/run_companion_eval.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    leak = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_tutor_rails.py",
            "tests/eval_winbars/test_p3_no_answer_leak.py",
            "tests/test_companion_plan_predict.py",
            "-q",
            "--tb=line",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    metrics = {
        "five_intents_ok": five_cap,
        "plan_week_ok": float(plan_ok),
        "predict_risk_ok": float(predict_ok),
        "stage_pack_cite_rate": round(cite_ok / max(1, cite_need), 4),
        "p1_eval_pass": 1.0 if p1.returncode == 0 else 0.0,
        "leak_suite_pass": 1.0 if leak.returncode == 0 else 0.0,
        "suite_intent_rate": round(five_intents_ok, 4),
    }
    thresholds = {
        "five_intents_ok": 1.0,
        "plan_week_ok": 1.0,
        "predict_risk_ok": 1.0,
        "stage_pack_cite_rate": 0.75,
        "p1_eval_pass": 1.0,
        "leak_suite_pass": 1.0,
    }
    gates = {
        k: {
            "value": metrics[k],
            "threshold": thresholds[k],
            "pass": metrics[k] >= thresholds[k],
        }
        for k in thresholds
    }
    payload = {
        "experiment_id": "ilearn-companion-phase1",
        "all_pass": all(g["pass"] for g in gates.values()),
        "gates": gates,
        "metrics": metrics,
        "details": details,
        "p1_stdout_tail": (p1.stdout or "")[-400:],
        "leak_stdout_tail": (leak.stdout or "")[-400:],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"all_pass": payload["all_pass"], "gates": gates}, ensure_ascii=False, indent=2))
    return 0 if payload["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
