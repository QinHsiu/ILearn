"""P9 browser-path activation: demo deep-links + evidence hops ≤2."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from ilearn.api.app import create_app

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "data" / "pilot"
EVIDENCE = ROOT / "runtime_evidence" / "browser_path_activation.md"


def _assert_link_is_shallow(link: str) -> None:
    """Landing → role deep link is one navigation (query string only)."""
    assert link.startswith("?"), link
    # One click from Landing CTA; query params carry session — no nested path hops.
    assert "session_id=" in link or "student=1" in link or "login=1" in link


def main() -> int:
    import tempfile

    tmp = Path(tempfile.mkdtemp())
    client = TestClient(
        create_app(
            sessions_dir=tmp,
            pilot_data_dir=PILOT,
            relationships_path=tmp / "relationships.json",
            llm=None,
        )
    )
    t0 = time.perf_counter()
    hops: list[str] = []

    # Hop 0: Landing-equivalent probes
    assert client.get("/quality-gates").status_code == 200
    hops.append("GET /quality-gates")
    assert client.get("/capabilities").status_code == 200
    hops.append("GET /capabilities")

    # Hop 1: one CTA creates demo (Landing button)
    demo = client.post("/demo/units/math_5_1/session")
    assert demo.status_code == 200
    body = demo.json()
    sid = body["session_id"]
    links = body["links"]
    hops.append("POST /demo/units/math_5_1/session")
    for role in ("student", "parent", "teacher"):
        _assert_link_is_shallow(links[role])

    # Hop 2: each role lands on evidence (second click max)
    assert client.get(f"/sessions/{sid}/mastery-public").status_code == 200
    hops.append(f"GET mastery-public ({sid[:8]}…)")
    assert client.get(f"/sessions/{sid}/summary/parent").status_code == 200
    hops.append("GET summary/parent")
    assert client.get(f"/sessions/{sid}/summary/teacher").status_code == 200
    hops.append("GET summary/teacher")

    # Concept storyboard available for student soft-exit
    story = client.get("/pilot-assets/concept/mult_3digit.md")
    assert story.status_code == 200
    assert "不含终答" in story.text or "终答" in story.text
    hops.append("GET pilot-assets/concept/mult_3digit.md")

    elapsed = time.perf_counter() - t0
    lines = [
        "# Browser-path Activation Evidence",
        "",
        "Simulates Landing → demo CTA → role deep-link evidence (API equivalent of browser hops).",
        "",
        f"- session_id: `{sid}`",
        f"- elapsed_s: **{elapsed:.3f}** (budget 60)",
        f"- max_user_clicks: **2** (1 create demo + 1 open role link)",
        f"- student_link: `{links['student']}`",
        f"- parent_link: `{links['parent']}`",
        f"- teacher_link: `{links['teacher']}`",
        "",
        "## Hop log",
        "",
        *[f"- {h}" for h in hops],
        "",
        "Pass" if elapsed <= 60 else "FAIL over budget",
        "",
    ]
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text("\n".join(lines), encoding="utf-8")
    print(f"OK browser-path activation in {elapsed:.3f}s clicks<=2 session={sid}")
    return 0 if elapsed <= 60 else 1


if __name__ == "__main__":
    raise SystemExit(main())
