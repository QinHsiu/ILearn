"""Validate / report cognitive skill graph coverage."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ilearn.core.cognitive_profile import CognitiveSkillGraph, validate_cognitive_skills


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build/validate cognitive skill graph")
    parser.add_argument(
        "--check",
        type=Path,
        default=Path("data/cognitive_skills.json"),
        help="Path to cognitive_skills.json",
    )
    args = parser.parse_args(argv)
    errs = validate_cognitive_skills(args.check)
    if errs:
        print("\n".join(errs))
        return 1
    g = CognitiveSkillGraph(args.check)
    units: dict[str, int] = {}
    for skill in g.all_skills():
        units[skill.knowledge_point] = units.get(skill.knowledge_point, 0) + 1
    print(f"ok: {len(g.all_skills())} skills, units={units}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
