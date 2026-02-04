# FW→Sea Heuristic Candidate Links (Non-canonical)

**Method (heuristic):**
- Sea populations: `Ext_Populations_v2` names matching pattern like `S07 S21 SF NOV 25 (JUN 24)` and `ProdStage = MarineSite`, `StartTime >= 2023-01-01`.
- FW candidates: `ProdStage in {FreshWater, SmoltProduction, Hatchery}` and `Site` station code matches the sea name’s FW station code.
- Time window: FW `EndTime` within ±60 days of sea `StartTime`.
- Scoring: date alignment + (optional) count alignment from `status_values.csv` (FW last count before EndTime vs sea first count after StartTime).

**Summary:**
- sea_populations_pattern_2023plus: 1363
- candidate_pairs_within_window: 428436
- final_pairs_top5_per_sea: 6575
- pairs_with_count_alignment: 5242

**Output CSV:** `analysis_reports/2026-02-03/fw_to_sea_heuristic_candidates_2026-02-03.csv`

**Important:** This report is **non-canonical** and should not be used as deterministic linkage without manual validation.
