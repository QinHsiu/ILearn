# Dual-layer retrieval + Assessment.tsx

**Approved:** 2026-08-26 Approach 3  
**Do not commit docs/**

## Backend
- After local template selection for adaptive anchor, if shortfall: LLM generate (validated) else deterministic stub items
- Metadata: layer2_used, layer2_source
- Full 20-item paper unchanged

## Frontend
- `pages/Assessment.tsx`: anchor → continue → full; replace StudentApp step 2
- api client adaptiveStart/Continue
- onComplete feeds existing submit/run
