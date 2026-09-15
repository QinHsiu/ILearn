"""Capture demo API smoke evidence for competition runtime_evidence/."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from ilearn.api.app import create_app

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "runtime_evidence" / "demo_api_smoke.txt"
PILOT = ROOT / "data" / "pilot"
SESS = ROOT / "runtime_evidence" / "_tmp_demo_sessions"


def main() -> None:
    SESS.mkdir(parents=True, exist_ok=True)
    client = TestClient(
        create_app(
            sessions_dir=SESS,
            pilot_data_dir=PILOT,
            relationships_path=SESS / "relationships.json",
            llm=None,
        )
    )
    lines: list[str] = []
    created = client.post("/demo/units/math_5_1/session")
    lines.append(f"POST /demo/units/math_5_1/session -> {created.status_code}")
    payload = created.json()
    sid = payload["session_id"]
    lines.append(json.dumps(payload, ensure_ascii=False, indent=2))
    lines.append("")

    for path in (
        f"/sessions/{sid}/summary/teacher",
        f"/sessions/{sid}/summary/parent",
        f"/sessions/{sid}/summary/student",
        f"/sessions/{sid}/effectiveness",
    ):
        resp = client.get(path)
        body = resp.json()
        lines.append(f"GET {path} -> {resp.status_code}")
        lines.append(json.dumps(body, ensure_ascii=False, indent=2)[:4000])
        lines.append("")

    parent = client.get(f"/sessions/{sid}/summary/parent").json()
    weak = " ".join(parent.get("weak_skills") or [])
    tips = " ".join(parent.get("daily_practice_tips") or [])
    dirty = any(token in weak + tips for token in ("kp_", "dec_", "掌握度", "知识点"))
    lines.append(f"parent_purity_check_pass={not dirty}")
    if dirty:
        lines.append(f"weak_skills={parent.get('weak_skills')}")
        lines.append(f"tips_sample={parent.get('daily_practice_tips')}")

    for kind in ("report.pdf", "effectiveness.pdf"):
        r = client.get(f"/sessions/{sid}/export/{kind}")
        lines.append(
            f"GET /sessions/{sid}/export/{kind} -> {r.status_code} "
            f"content-type={r.headers.get('content-type')} "
            f"x-pdf-backend={r.headers.get('x-pdf-backend')} "
            f"bytes={len(r.content)}"
        )

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
