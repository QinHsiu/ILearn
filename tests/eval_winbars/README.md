# Win-bar evaluation suite

Each pillar `PN` must have a green test under this folder before
`docs/commercial/WIN_BARS.md` may mark that pillar `pass`.

Naming: `test_pN_<slug>.py`

Run:

```bash
python -m pytest tests/eval_winbars -q
```

Spec: `docs/superpowers/specs/2026-09-15-ilearn-surpass-competitors-design.md`
