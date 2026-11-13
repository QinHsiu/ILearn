"""P2: ExperienceStore read-only prior."""

from ilearn.experience.store import ExperienceRecord, ExperienceStore


def test_retrieve_filters_stage_and_ranks():
    store = ExperienceStore(
        [
            ExperienceRecord(
                record_id="e1",
                learner_segment={"stage": "primary"},
                situation="分数 通分 薄弱",
                strategy="hint_level_2",
                outcome="effective",
            ),
            ExperienceRecord(
                record_id="e2",
                learner_segment={"stage": "career"},
                situation="职场 指标",
                strategy="open_learn",
                outcome="neutral",
            ),
            ExperienceRecord(
                record_id="e3",
                learner_segment={"stage": "primary"},
                situation="小数乘法 竖式",
                strategy="hint_level_1",
                outcome="ineffective",
            ),
        ]
    )
    hits = store.retrieve({"stage": "primary", "text": "分数通分不会"}, top_k=2)
    assert hits
    assert all(h.learner_segment["stage"] == "primary" for h in hits)
    prior = store.prior_for({"stage": "primary", "text": "分数通分不会"})
    assert prior.experience_refs
    assert prior.records[0].record_id in prior.experience_refs
