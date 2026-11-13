# /exp_loop — ilearn-wiki-l2

## Round 0
- analysis: Curriculum RAG only; no human-readable wiki layer tied to L1 skills
- chosen: stdlib BM25 + CJK bigrams + skill boost + skill-graph edges
- evaluation: `tests/test_wiki_l2.py` all pass
- decision: **stop**
