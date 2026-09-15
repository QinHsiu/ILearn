from ilearn.core.step_align import align_steps


def test_p4_align_marks_matched_and_missing():
    rows = align_steps(
        ["对齐小数位", "随便写"],
        ["对齐小数位", "相乘", "点小数点"],
    )
    statuses = [r["status"] for r in rows]
    assert "matched" in statuses
    assert "missing" in statuses or "extra" in statuses
    blob = str(rows)
    assert "3.6" not in blob
