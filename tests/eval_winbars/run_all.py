"""Run all win-bar tests and print a short report."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    cmd = [sys.executable, "-m", "pytest", str(ROOT / "tests" / "eval_winbars"), "-q"]
    proc = subprocess.run(cmd, cwd=ROOT)
    report = ROOT / "runtime_evidence" / "winbar_report.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        f"# Win-bar report\n\nCommand: `{' '.join(cmd)}`\n\nExit: {proc.returncode}\n",
        encoding="utf-8",
    )
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
