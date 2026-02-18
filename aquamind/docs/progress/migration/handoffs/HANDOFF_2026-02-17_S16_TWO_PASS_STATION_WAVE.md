# HANDOFF 2026-02-17: S16 Two-Pass Faroe Station Wave

## Scope

Continue the Faroe `<30 months` freshwater rollout at `S16 Glyvradalur` using the established two-pass policy:

- strict station pass first (`--expected-site`, no mismatch override),
- controlled mixed-site recovery second (`--allow-station-mismatch`) only if strict blocks on station mismatch,
- semantic regression gates on all successful migrations.

## Non-negotiables honored

- Backup cutoff/horizon pinned to `2026-01-22`.
- Runtime remains FishTalk-agnostic (no runtime code changes).
- Source-specific handling stays in migration tooling/validation/reporting.
- Profile baseline remains `fw_default`.

## Wave execution summary

### Pass 1: Strict station guard

- Station: `S16 Glyvradalur`
- Cohorts attempted: `11`
- Migration success: `11/11`
- Semantic gate pass: `11/11`

Cohorts:

- `Bakkafrost Juli 2023|3|2023`
- `Bakkafrost Okt 2023|4|2023`
- `Bakkafrost feb 2024|1|2024`
- `Bakkafrost feb 2025|2|2025`
- `Bakkafrost mai 24|2|2024`
- `Stofnfiskur Aug 2024|4|2024`
- `Stofnfiskur August 25|4|2025`
- `Stofnfiskur Nov 2024|5|2024`
- `Stofnfiskur feb 2025|1|2025`
- `Stofnfiskur mai 2024|3|2024`
- `Stofnfiskur mai 2025|3|2025`

### Pass 2: Controlled mixed-site recovery

- Not required (`0` strict mismatch blockers).

## Regression statement

**No new semantic regression signal introduced by S16 station-wave execution.**

All migrated cohorts passed semantic validation with regression gates enabled.

## Faroe 7-station coverage delta

- Prior to S16 wave: `18/53` in-scope batches migrated+semantic PASS.
- After S16 wave: `29/53` in-scope batches migrated+semantic PASS.
- S16 status is now fully covered: `11/11`.

Remaining gaps:

- `S03`: `0/10`
- `S04`: `0/6`
- `S08`: `0/6`
- `S10`: `0/1`
- `S21`: `9/10`

## Artifact index

- S16 two-pass execution result:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-17/S16_station_wave_two_pass_execution_result_2026-02-17.json`
- S16 strict pass summary:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-17/S16_station_wave_migration_summary_2026-02-17.md`
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-17/S16_station_wave_migration_summary_2026-02-17.json`
- S16 per-cohort semantic outputs:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-17/S16_station_wave_*_semantic_validation_2026-02-17.md`
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-17/S16_station_wave_*_semantic_validation_2026-02-17.summary.json`
- Faroe coverage scoreboard (updated post-S16):
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-17/Faroe_fw_7station_coverage_scoreboard_2026-02-17.md`
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-17/Faroe_fw_7station_coverage_scoreboard_2026-02-17.json`

## Recommended next step

Run the next Faroe station wave at `S03` using the same two-pass policy (`strict` then controlled mismatch recovery only if needed), then re-publish the coverage scoreboard.
