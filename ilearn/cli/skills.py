"""CLI: teaching skill induction / listing (no LLM)."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from ilearn.experience.models import ExperienceRecord
from ilearn.skills.inducer import induce_skills
from ilearn.skills.registry import SkillRegistry

app = typer.Typer(help="MemCryst 教学技能")

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_SKILLS = _PROJECT_ROOT / "data" / "skills" / "registry.json"


@app.command("induce")
def induce(
    records_file: Path = typer.Argument(..., help="ExperienceRecord JSON array"),
    out: Path | None = typer.Option(None, "--out"),
    min_episodic: int = typer.Option(5, "--min-episodic"),
) -> None:
    raw = json.loads(records_file.read_text(encoding="utf-8"))
    records = [ExperienceRecord.model_validate(r) for r in raw]
    skills = induce_skills(records, min_episodic=min_episodic)
    payload = [s.model_dump(mode="json") for s in skills]
    typer.echo(f"induced {len(skills)} skills")
    path = out or _DEFAULT_SKILLS
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    typer.echo(f"wrote {path}")


@app.command("list")
def list_skills(
    registry: Path = typer.Option(_DEFAULT_SKILLS, "--registry"),
) -> None:
    if not registry.is_file():
        typer.echo("[]")
        return
    from ilearn.skills.models import TeachingSkill

    raw = json.loads(registry.read_text(encoding="utf-8"))
    skills = [TeachingSkill.model_validate(r) for r in raw]
    reg = SkillRegistry(skills)
    for s in reg.list_active() or skills:
        typer.echo(
            f"{s.skill_id}  status={s.status}  conf={s.confidence}  "
            f"inv={s.invocation_count}/{s.success_count}"
        )
