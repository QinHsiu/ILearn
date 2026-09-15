"""P4 step alignment without revealing final answers."""

from __future__ import annotations


def align_steps(student_lines: list[str], rubric_steps: list[str]) -> list[dict]:
    """Naive line/token overlap alignment for review UI."""
    remaining = list(enumerate(rubric_steps))
    out: list[dict] = []
    for raw in student_lines:
        line = (raw or "").strip()
        if not line:
            continue
        best_i = None
        best_score = 0
        for idx, step in remaining:
            tokens = set(step)
            score = sum(1 for ch in line if ch in tokens)
            if score > best_score:
                best_score = score
                best_i = idx
        if best_i is not None and best_score > 0:
            step = rubric_steps[best_i]
            remaining = [(i, s) for i, s in remaining if i != best_i]
            out.append({"student": line, "rubric": step, "status": "matched"})
        else:
            out.append({"student": line, "rubric": None, "status": "extra"})
    for _, step in remaining:
        out.append({"student": None, "rubric": step, "status": "missing"})
    return out
