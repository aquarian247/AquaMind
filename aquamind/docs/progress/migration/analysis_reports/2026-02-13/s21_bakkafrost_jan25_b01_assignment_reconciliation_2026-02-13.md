# S21 Bakkafrost S-21 jan 25 B01 assignment reconciliation

Date: 2026-02-13

## Key findings

- B01 has 8 FishTalk population segments in migration input members; 5 were materialized as AquaMind assignment rows.
- The first two windows match FishTalk status snapshots exactly at entry (`74,983` and `47,516` visible in source status rows).
- Later B01 windows (Nov/Dec/Jan) have no `status_values` rows and no `sub_transfers` edges in this extract for several segment PopulationIDs, so deterministic count reconstruction is not possible from current extract alone.
- One later segment (`CD9...`) was materialized with count from known removals floor (`2185`) because mortality/culling evidence exists while conserved/status baselines are zero.
- Segments without stage tokens + no subtransfer touch + no non-zero status/removals were suppressed by orphan-zero suppression logic.

## Extract coverage constraint observed

- `status_values.csv` max timestamp: `2025-10-31 14:58:32`
- `sub_transfers.csv` max timestamp: `2025-10-31 14:58:32`
- This explains why post-2025-10-31 B01 swimlane lanes cannot be reproduced faithfully from current transfer/status extracts.

## Artifacts

- Segment diagnostics CSV: `aquamind/docs/progress/migration/analysis_reports/2026-02-13/S21_Bakkafrost_S21_jan25_B01_population_segment_diagnostics_2026-02-13.csv`
- Summary JSON: `aquamind/docs/progress/migration/analysis_reports/2026-02-13/S21_Bakkafrost_S21_jan25_B01_population_segment_diagnostics_2026-02-13.summary.json`
