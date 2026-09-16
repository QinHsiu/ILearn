"""W5: local activation screenshots for social proof (Gauth-class entry).

Landing → demo CTA → three-role deep links, ≤2 user clicks. Outputs land under
``runtime_evidence/activation_screenshots/`` which is covered by
``runtime_evidence/*`` in ``.gitignore`` — **不入库 / not tracked**.

Modes
------
* ``--api-only`` (default): create demo via TestClient, probe mastery/parent/
  teacher evidence, write SVG storyboard cards + ``index.md``. No Playwright.
* ``--browser BASE_URL``: also capture real PNGs with Playwright when a local
  FE+BE stack is already running (optional; not required for the gate).

Usage (repo root)::

    python scripts/capture_activation_screenshots.py
    python scripts/capture_activation_screenshots.py --browser http://127.0.0.1:5173
"""

from __future__ import annotations

import argparse
import html
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from fastapi.testclient import TestClient

from ilearn.api.app import create_app

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "data" / "pilot"
OUT_DIR = ROOT / "runtime_evidence" / "activation_screenshots"
MAX_USER_CLICKS = 2


def _assert_link_is_shallow(link: str) -> None:
    assert link.startswith("?"), link
    assert "session_id=" in link or "student=1" in link or "role=" in link


def _write_svg(path: Path, title: str, subtitle: str, bullets: list[str]) -> None:
    lines = []
    y = 148
    for bullet in bullets[:7]:
        safe = html.escape(bullet)[:100]
        lines.append(f'<text x="48" y="{y}" font-size="18" fill="#222">{safe}</text>')
        y += 34
    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">
  <rect width="1280" height="720" fill="#f7f4ee"/>
  <rect x="0" y="0" width="18" height="720" fill="#002fa7"/>
  <text x="48" y="52" font-size="24" font-weight="700" fill="#002fa7">ILearn · 激活证明（W5）</text>
  <text x="48" y="100" font-size="36" font-weight="700" fill="#111">{html.escape(title)}</text>
  <text x="48" y="136" font-size="20" fill="#555">{html.escape(subtitle)}</text>
  {chr(10).join(lines)}
  <text x="48" y="690" font-size="15" fill="#666">本地脚本产出 · runtime_evidence/activation_screenshots · gitignore 不入库 · max_user_clicks={MAX_USER_CLICKS}</text>
</svg>
"""
    path.write_text(svg, encoding="utf-8")


def _capture_browser(base_url: str, links: dict[str, str], out: Path) -> list[str]:
    """Optional Playwright path — skipped cleanly if deps/server missing."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return ["playwright not installed — skipped real browser PNGs"]

    pages = [
        ("01_landing.png", base_url.rstrip("/") + "/"),
        ("02_student.png", base_url.rstrip("/") + "/?" + links["student"].lstrip("?")),
        ("03_parent.png", base_url.rstrip("/") + "/?" + links["parent"].lstrip("?")),
        ("04_teacher.png", base_url.rstrip("/") + "/?" + links["teacher"].lstrip("?")),
    ]
    shots: list[str] = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 720})
            for name, url in pages:
                page.goto(url, wait_until="networkidle", timeout=45000)
                target = out / name
                page.screenshot(path=str(target), full_page=False)
                shots.append(f"PNG {name} ({target.stat().st_size} bytes)")
            browser.close()
    except Exception as exc:  # noqa: BLE001 — optional path must never fail the gate
        return [f"browser capture failed (ok for --api-only gate): {exc}"]
    return shots


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--browser",
        metavar="BASE_URL",
        default=None,
        help="Optional FE origin for Playwright PNGs (e.g. http://127.0.0.1:5173)",
    )
    args = parser.parse_args(argv)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="ilearn-w5-"))
    sessions_dir = tmp / "sessions"
    sessions_dir.mkdir()
    client = TestClient(
        create_app(
            sessions_dir=sessions_dir,
            pilot_data_dir=PILOT,
            relationships_path=tmp / "relationships.json",
            llm=None,
        )
    )

    t0 = time.perf_counter()
    hops: list[str] = []

    assert client.get("/quality-gates").status_code == 200
    hops.append("GET /quality-gates")
    demo = client.post("/demo/units/math_5_1/session")
    assert demo.status_code == 200
    body = demo.json()
    sid = body["session_id"]
    links = body["links"]
    hops.append("POST /demo/units/math_5_1/session  # user click 1")
    for role in ("student", "parent", "teacher"):
        _assert_link_is_shallow(links[role])

    assert client.get(f"/sessions/{sid}/mastery-public").status_code == 200
    hops.append("GET mastery-public  # student evidence after click 2")
    assert client.get(f"/sessions/{sid}/summary/parent").status_code == 200
    hops.append("GET summary/parent")
    assert client.get(f"/sessions/{sid}/summary/teacher").status_code == 200
    hops.append("GET summary/teacher")
    assert client.get(f"/sessions/{sid}/error-notebook").status_code == 200
    hops.append("GET error-notebook")
    session_body = client.get(f"/sessions/{sid}").json()
    nickname = (session_body.get("profile") or {}).get("nickname") or "演示"
    weekly = client.get(f"/learners/{quote(nickname)}/weekly-report")
    assert weekly.status_code == 200
    hops.append(f"GET weekly-report ({nickname})")

    elapsed = time.perf_counter() - t0

    _write_svg(
        OUT_DIR / "01_landing.svg",
        "Landing · 一键体验",
        "课标在环 · 不泄终答 · ≤2 次点击见证据",
        [
            "CTA：体验小数乘法 / 角色卡一键体验",
            "质量门条可见 · waitlist 表单可用（不做 A/B）",
            f"demo session: {sid}",
        ],
    )
    _write_svg(
        OUT_DIR / "02_student.svg",
        "学生深链 · 敢问敢练",
        links["student"],
        [
            "证据：mastery-public（提示后做对不计入掌握）",
            "概念分镜翻页 · 错题本终答遮罩",
            "不直接给最终答案",
        ],
    )
    _write_svg(
        OUT_DIR / "03_parent.svg",
        "家长深链 · 今晚就能陪",
        links["parent"],
        [
            "证据：summary/parent + 自然周周报",
            "亲子题卡 / 错题本只读（不看终答）",
            "比上周：证据优先，正确率仅参考",
        ],
    )
    _write_svg(
        OUT_DIR / "04_teacher.svg",
        "教师深链 · 布置就能办完",
        links["teacher"],
        [
            "证据：summary/teacher + 布置回访完成态",
            "未开始 / 重练中 / 已提交",
            "分层布置回执可带走",
        ],
    )

    browser_notes: list[str] = []
    if args.browser:
        browser_notes = _capture_browser(args.browser, links, OUT_DIR)
    else:
        browser_notes = ["--browser not set; SVG storyboards only (enough for local social proof)"]

    generated = datetime.now(timezone.utc).isoformat()
    index = [
        "# Activation screenshots (W5)",
        "",
        "本地激活社会证明 · **不入库**（`runtime_evidence/*` in `.gitignore`）。",
        "",
        f"- generated_at_utc: `{generated}`",
        f"- session_id: `{sid}`",
        f"- elapsed_s: **{elapsed:.3f}** (budget 60)",
        f"- max_user_clicks: **{MAX_USER_CLICKS}**",
        f"- student_link: `{links['student']}`",
        f"- parent_link: `{links['parent']}`",
        f"- teacher_link: `{links['teacher']}`",
        "",
        "## Storyboard files",
        "",
        "- `01_landing.svg`",
        "- `02_student.svg`",
        "- `03_parent.svg`",
        "- `04_teacher.svg`",
        "",
        "## Hop log",
        "",
        *[f"- {h}" for h in hops],
        "",
        "## Browser notes",
        "",
        *[f"- {n}" for n in browser_notes],
        "",
        "Pass" if elapsed <= 60 else "FAIL over budget",
        "",
    ]
    (OUT_DIR / "index.md").write_text("\n".join(index), encoding="utf-8")
    print(f"OK W5 activation shots → {OUT_DIR} ({elapsed:.3f}s, clicks<={MAX_USER_CLICKS})")
    for note in browser_notes:
        print(f"  · {note}")
    return 0 if elapsed <= 60 else 1


if __name__ == "__main__":
    raise SystemExit(main())
