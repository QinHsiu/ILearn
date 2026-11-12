"""Companion P1 metric eval — design §6 / TARGET.md.

Run from repo root:
  python content/exp/ilearn-companion-p1/eval/run_companion_eval.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]  # .../ILearn
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ilearn.agents.companion import CompanionAgent
from ilearn.core.schemas import SessionPhase, SessionState, StudentProfile
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider

EVAL_DIR = Path(__file__).resolve().parent
EXP_DIR = EVAL_DIR.parent
UTTERANCES = EVAL_DIR / "utterances.jsonl"
OUT_JSON = EXP_DIR / "metrics" / "summary.json"
NO_HIT_MARKERS = ("未命中", "没有命中", "没有找到", "可引用")


def _load_rows() -> list[dict]:
    rows = []
    for line in UTTERANCES.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _session(grade: int = 5) -> SessionState:
    age = min(18, max(6, grade + 6))
    return SessionState(
        session_id="eval-companion",
        profile=StudentProfile(region="北京", grade=grade, age=age),
        phase=SessionPhase.IDLE,
    )


def run_offline_chat_eval() -> dict:
    # Force offline: no API keys in process for this harness.
    for key in list(os.environ):
        if "API_KEY" in key or key.endswith("_TOKEN"):
            os.environ.pop(key, None)

    pilot = ROOT / "data" / "pilot"
    agent = CompanionAgent(PilotBeijingRenjiaoProvider(pilot), llm=None)
    rows = _load_rows()

    intents: list[str] = []
    non_assess_intents: list[str] = []
    answer_grounded = 0
    answer_total = 0
    offline_ok = 0
    offline_total = 0
    details: list[dict] = []

    for row in rows:
        grade = int(row.get("grade") or 5)
        mode = row.get("mode") or "exam_tutor"
        reply = agent.chat(_session(grade), row["message"], mode=mode)
        offline_total += 1
        nonempty = bool((reply.reply or "").strip())
        if nonempty:
            offline_ok += 1
        intents.append(reply.intent)
        if row.get("non_assessment", True):
            non_assess_intents.append(reply.intent)

        grounded = None
        if reply.intent == "answer":
            answer_total += 1
            text = reply.reply or ""
            grounded = bool(reply.citations) or any(m in text for m in NO_HIT_MARKERS)
            if grounded:
                answer_grounded += 1

        details.append(
            {
                "id": row["id"],
                "message": row["message"],
                "expect_intent": row.get("expect_intent"),
                "got_intent": reply.intent,
                "nonempty": nonempty,
                "citations": len(reply.citations or []),
                "grounded": grounded,
                "reply_preview": (reply.reply or "")[:120],
            }
        )

    ask_answer = sum(1 for i in non_assess_intents if i in {"ask", "answer"})
    ask_answer_share = ask_answer / max(1, len(non_assess_intents))
    answer_grounded_rate = answer_grounded / max(1, answer_total)
    offline_nonempty_rate = offline_ok / max(1, offline_total)

    # Secondary B1: grade≥7 answer turns should preferably cite pack snippets.
    b1_rows = [d for d in details if d["id"] in {"u12", "u13", "u14"}]
    b1_cited = sum(1 for d in b1_rows if (d.get("citations") or 0) > 0)
    b1_citation_rate = b1_cited / max(1, len(b1_rows))

    return {
        "ask_answer_share": round(ask_answer_share, 4),
        "answer_grounded_rate": round(answer_grounded_rate, 4),
        "offline_nonempty_rate": round(offline_nonempty_rate, 4),
        "b1_citation_rate": round(b1_citation_rate, 4),
        "n_non_assessment": len(non_assess_intents),
        "n_answer": answer_total,
        "details": details,
    }


def run_leak_suite() -> dict:
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/test_tutor_rails.py",
        "tests/eval_winbars/test_p3_no_answer_leak.py",
        "tests/test_companion_agent.py",
        "-q",
        "--tb=line",
    ]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return {
        "leak_suite_pass": 1.0 if proc.returncode == 0 else 0.0,
        "returncode": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-500:],
        "stderr_tail": (proc.stderr or "")[-500:],
    }


def main() -> int:
    chat = run_offline_chat_eval()
    leak = run_leak_suite()
    thresholds = {
        "ask_answer_share": 0.60,
        "answer_grounded_rate": 1.0,
        "leak_suite_pass": 1.0,
        "offline_nonempty_rate": 1.0,
        "b1_citation_rate": 0.66,
    }
    metrics = {
        "ask_answer_share": chat["ask_answer_share"],
        "answer_grounded_rate": chat["answer_grounded_rate"],
        "offline_nonempty_rate": chat["offline_nonempty_rate"],
        "leak_suite_pass": leak["leak_suite_pass"],
        "b1_citation_rate": chat["b1_citation_rate"],
    }
    gates = {
        k: {"value": metrics[k], "threshold": thresholds[k], "pass": metrics[k] >= thresholds[k]}
        for k in thresholds
    }
    payload = {
        "experiment_id": "ilearn-companion-p1",
        "metrics": metrics,
        "gates": gates,
        "all_pass": all(g["pass"] for g in gates.values()),
        "chat": {k: v for k, v in chat.items() if k != "details"},
        "details": chat["details"],
        "leak": leak,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"all_pass": payload["all_pass"], "gates": gates}, ensure_ascii=False, indent=2))
    return 0 if payload["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
