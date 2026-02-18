# S21 Bakkafrost S-21 jan 25 migration packet (batch 464)

Date: 2026-02-13

## Batch

- Migration DB: `aquamind_db_migr_dev`
- Batch ID: `464`
- Batch number: `Bakkafrost S-21 jan 25`
- Lifecycle stage snapshot: `Parr`

## Coverage windows

- Assignments: `2025-01-06` -> `2025-12-16`
- Transfer actions: `2025-04-02` -> `2025-10-29`
- Feeding: `2025-04-02` -> `2025-10-30`
- Mortality: `2025-01-06` -> `2026-01-22`
- Treatments: `2025-10-22T09:08:13+00:00` -> `2025-12-18T12:25:04+00:00`

## Scope boundary

- This migrated batch is station-scoped (`S21 Viðareiði`) and includes in-station lifecycle progression from `R1..R7` onward.
- Broodstock provenance fan-in (`L01 Við Áir -> S21 R1..R7`, `2025-01-06`) is tracked as evidence/provenance context and is not materialized as standalone L01 assignment rows in this batch packet.
- Provenance reference: `aquamind/docs/progress/migration/analysis_reports/2026-02-13/s21_bakkafrost_jan25_egg_origin_fanin_l01_to_rogn_2026-02-13.md`

## Counts

- assignments_total: `123`
- assignments_active: `17`
- assignments_departed: `106`
- transfer_workflows: `46`
- transfer_actions: `51`
- feeding_events: `872`
- mortality_events: `1494`
- treatments: `22`

## Stage assignment counts

- `Egg&Alevin`: `7`
- `Fry`: `12`
- `Parr`: `99`
- `Smolt`: `5`

## Artifacts

- Assignments CSV: `aquamind/docs/progress/migration/analysis_reports/2026-02-13/S21_Bakkafrost_S21_jan25_migration_batch_464_assignments_2026-02-13.csv`
- Transfer actions CSV: `aquamind/docs/progress/migration/analysis_reports/2026-02-13/S21_Bakkafrost_S21_jan25_migration_batch_464_transfer_actions_2026-02-13.csv`
- Summary JSON: `aquamind/docs/progress/migration/analysis_reports/2026-02-13/S21_Bakkafrost_S21_jan25_migration_batch_464_summary_2026-02-13.json`
