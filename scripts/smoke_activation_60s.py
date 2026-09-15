"""P9 activation friction smoke: demo session exposes evidence within budget."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from ilearn.api.app import create_app

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "data" / "pilot"


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
    demo = client.post("/demo/units/math_5_1/session")
    assert demo.status_code == 200, demo.text
    sid = demo.json()["session_id"]
    parent = client.get(f"/sessions/{sid}/summary/parent")
    assert parent.status_code == 200
    body = parent.json()
    assert body.get("action_summary") or body.get("weak_skills") is not None
    elapsed = time.perf_counter() - t0
    print(f"OK activation evidence in {elapsed:.3f}s session={sid}")
    return 0 if elapsed <= 60 else 1


if __name__ == "__main__":
    raise SystemExit(main())
