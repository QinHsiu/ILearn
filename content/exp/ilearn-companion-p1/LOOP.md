# /exp_loop — ilearn-companion-p1

## Round 0
- analysis_summary: P1 Ask/Answer + UI merged (#41/#42). Baseline eval harness created from design §6.
- plans: [baseline]
- chosen: baseline
- mini_validation: M1–M4 all pass; B1 secondary fail (grade-7 answer cit=0)
- evaluation: see metrics/summary.json (pre-P1)
- decision: continue → P1 B1 pack

## Round 1
- analysis_summary: junior_high Answer only honest-miss; evaluate(grade=7) crashed CurriculumError
- plans: [P1-b1-junior-high-pack, P2-expand-pilot-grades]
- chosen: P1 (pack stretch; defer full PILOT expand)
- mini_validation: u12–u14 citations; grade7 evaluate degrades without crash
- training: N/A
- evaluation: all gates pass including b1_citation_rate=1.0
- decision: **stop** — target_score met

## dead_ends
- DE-1: Expanding PILOT_GRADES in Round 1 would break 4–6 API contracts — deferred to P2 file.
