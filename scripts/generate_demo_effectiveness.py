"""Write data/demo/effectiveness_summary.json from the seeded math_5_1 session."""

from __future__ import annotations

import json
from pathlib import Path

from ilearn.core.effectiveness import compute_metrics
from ilearn.demo.seed import seed_demo_session
from ilearn.demo.units import load_demo_unit

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "demo" / "effectiveness_summary.json"


def generate_demo_effectiveness(out_path: Path | None = None) -> dict:
    """Compute metrics on an in-memory seeded demo session and write summary JSON."""
    session = seed_demo_session(load_demo_unit("math_5_1"))
    row = compute_metrics(session).model_dump()
    results = [row]
    n = len(results)
    summary = {
        "total_sessions": n,
        "avg_mastery_gain": sum(r["mastery_gain"] for r in results) / n,
        "avg_time_saved": sum(r["time_saved_percent"] for r in results) / n,
        "avg_completion_rate": sum(r["completion_rate"] for r in results) / n,
        "total_weakness_resolved": sum(r["weakness_resolved_count"] for r in results),
        "sessions": results,
    }
    dest = out_path or OUT
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return summary


if __name__ == "__main__":
    summary = generate_demo_effectiveness()
    print("效果量化演示数据已生成")
    print(f"   - 平均掌握度提升: {summary['avg_mastery_gain']:.1f}%")
    print(f"   - 平均批改时间节省: {summary['avg_time_saved']:.1f}%")
    print(f"   - 总解决薄弱点: {summary['total_weakness_resolved']}")
