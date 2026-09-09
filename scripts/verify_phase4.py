#!/usr/bin/env python3
"""Phase 4 activation check: diagnose → metadata.enhanced (real SessionStore).

Usage (repo root):

    set ILEARN_ENABLE_ENHANCED_PROFILE=1
    set ILEARN_ENABLE_ENHANCED_AGENTS=1
    set ILEARN_ENABLE_ENHANCED_API=1
    python scripts/verify_phase4.py

Or let this script force-enable the three flags for the process.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Force flags for local activation demo (overrides data/features.yaml).
os.environ["ILEARN_ENABLE_ENHANCED_PROFILE"] = "1"
os.environ["ILEARN_ENABLE_ENHANCED_AGENTS"] = "1"
os.environ["ILEARN_ENABLE_ENHANCED_API"] = "1"

from ilearn.agents.orchestrator import MultiAgentOrchestrator  # noqa: E402
from ilearn.core.enhanced_flags import (  # noqa: E402
    clear_enhanced_flag_cache,
    is_enhanced_enabled,
)
from ilearn.core.enhanced_session import get_enhanced_profile  # noqa: E402
from ilearn.core.schemas import StudentProfile  # noqa: E402
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider  # noqa: E402
from ilearn.storage.sessions import SessionStore  # noqa: E402

PILOT = ROOT / "data" / "pilot"


def main() -> int:
    clear_enhanced_flag_cache()
    print("=" * 50)
    print("Phase 4: enhanced activation verify")
    print("=" * 50)

    print("\n[1] Feature flags:")
    flags = {
        "ENABLE_ENHANCED_PROFILE": is_enhanced_enabled("ENABLE_ENHANCED_PROFILE"),
        "ENABLE_ENHANCED_AGENTS": is_enhanced_enabled("ENABLE_ENHANCED_AGENTS"),
        "ENABLE_ENHANCED_API": is_enhanced_enabled("ENABLE_ENHANCED_API"),
    }
    for name, on in flags.items():
        print(f"  {name}: {on}")
    if not (flags["ENABLE_ENHANCED_PROFILE"] and flags["ENABLE_ENHANCED_AGENTS"]):
        print("\nERROR: PROFILE/AGENTS flags must be on")
        return 1

    with tempfile.TemporaryDirectory(prefix="ilearn-phase4-") as tmp:
        store = SessionStore(tmp)
        orch = MultiAgentOrchestrator(
            store=store,
            curriculum=PilotBeijingRenjiaoProvider(PILOT),
            llm=None,
        )
        print("\n[2] Orchestrator ready (llm=None → stub_mode)")

        sid = orch.create_session(
            StudentProfile(region="北京", grade=5, age=11, nickname="phase4")
        )
        paper = orch.generate_assessment(sid)
        answers = {item.id: (item.answer_key or "") for item in paper.items}
        for item in paper.items[:3]:
            answers[item.id] = "wrong-answer"
        orch.submit(sid, answers)
        orch.grade(sid)

        before = get_enhanced_profile(store.load(sid))
        print(f"\n[3] diagnose session={sid}")
        print(f"  before enhanced: {'yes' if before else 'no (expected)'}")
        diagnosis = orch.diagnose(sid)
        session = store.load(sid)
        after = get_enhanced_profile(session)

        print(f"  diagnosis rows: {len(diagnosis.knowledge_mastery)}")
        if after is None:
            print("  FAIL: metadata.enhanced missing after diagnose")
            return 1

        print("  OK: enhanced profile written")
        print(f"  student_id: {after.student_id}")
        print(f"  mastery keys: {len(after.cognitive.knowledge_mastery)}")
        print(f"  weak: {after.cognitive.weak_concepts[:5]}")
        print(f"  emotion: {after.emotional.current_emotion.value}")
        print(f"  style: {after.metacognitive.learning_style.value}")

        plan = orch.plan(sid)
        session = store.load(sid)
        blob = session.metadata.get("enhanced")
        recs = (blob or {}).get("recommendations") if isinstance(blob, dict) else None
        print("\n[4] plan + recommendations")
        print(f"  plan days: {len(plan.days) if plan and plan.days else 0}")
        print(f"  recommendations: {len(recs or [])}")

    print("\n" + "=" * 50)
    print("Phase 4 verify passed")
    print("=" * 50)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
