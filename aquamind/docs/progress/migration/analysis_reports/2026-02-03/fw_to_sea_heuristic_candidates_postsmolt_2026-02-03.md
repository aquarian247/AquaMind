# FW→Sea Heuristic Candidates (Post‑Smolt overlay)

**Method (heuristic):**
- Sea populations: `Ext_Populations_v2` names matching pattern like `S07 S21 SF NOV 25 (JUN 24)`, `ProdStage = MarineSite`, `StartTime >= 2023-01-01`.
- FW candidates: `ProdStage in {FreshWater, SmoltProduction, Hatchery}` AND hall mapped to **Post‑Smolt** (Faroe hall mapping).
- Time window: FW `EndTime` within ±60 days of sea `StartTime`.
- Scoring: date alignment + optional count alignment from `status_values.csv`.

**Summary:**
- sea_populations_pattern_2023plus: 1363
- fw_populations_postsmolt: 5439
- candidate_pairs_within_window: 126148
- final_pairs_top_per_sea: 6575
- pairs_with_count_alignment: 4681

**Output CSV:** `fw_to_sea_heuristic_candidates_postsmolt_2026-02-03.csv`

**Important:** Non‑canonical review aid only. Do not use as deterministic linkage.
