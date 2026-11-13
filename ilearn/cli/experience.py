"""CLI: experience extraction / stats (read-only — no LLM)."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from ilearn.experience.extractor import extract_experiences
from ilearn.experience.store import ExperienceStore

app = typer.Typer(help="经验检索层（只读先验）")

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


@app.command("stats")
def stats(
    events_file: Path | None = typer.Option(
        None,
        "--events",
        help="JSON/JSONL event dump to extract from (optional)",
    ),
) -> None:
    """统计经验命中/未命中率（离线）。"""
    records = []
    if events_file and events_file.is_file():
        text = events_file.read_text(encoding="utf-8").strip()
        if events_file.suffix == ".jsonl" or "\n" in text and not text.startswith("["):
            events = [json.loads(line) for line in text.splitlines() if line.strip()]
        else:
            raw = json.loads(text)
            events = raw if isinstance(raw, list) else raw.get("events", [])
        records = extract_experiences(events)

    store = ExperienceStore(records)
    report = store.hit_rate()
    typer.echo(json.dumps(report, ensure_ascii=False, indent=2))


@app.command("extract")
def extract(
    events_file: Path = typer.Argument(..., help="JSON/JSONL event dump"),
    out: Path | None = typer.Option(None, "--out", help="Write ExperienceRecord JSON"),
) -> None:
    """从 event_log 离线抽取 ExperienceRecord。"""
    text = events_file.read_text(encoding="utf-8").strip()
    if events_file.suffix == ".jsonl" or ("\n" in text and not text.startswith("[")):
        events = [json.loads(line) for line in text.splitlines() if line.strip()]
    else:
        raw = json.loads(text)
        events = raw if isinstance(raw, list) else raw.get("events", [])
    records = extract_experiences(events)
    payload = [r.model_dump(mode="json") for r in records]
    typer.echo(f"extracted {len(records)} records")
    if out:
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        typer.echo(f"wrote {out}")
