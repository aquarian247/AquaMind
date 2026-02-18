# HANDOFF 2026-02-18: S08 Two-Pass Faroe Station Wave

## Scope

Execute the Faroe `<30 months` freshwater station wave for `S08 Gjógv` under the established two-pass policy:

- strict station pass first (`--expected-site`),
- mismatch recovery only if strict preflight blocks (`--allow-station-mismatch`),
- semantic regression gate required for each successful migration.

## Policy and constraints

- Backup horizon: `2026-01-22`.
- Profile: `fw_default`.
- Runtime remains FishTalk-agnostic.
- Source-specific rules remain in migration tooling and validation/reporting only.

## Result

- Cohorts targeted: `6`.
- Strict migration success: `6/6`.
- Strict semantic pass: `6/6`.
- Recovery cohorts needed: `0`.
- Recovery semantic pass: `0/0` (not applicable).

## Coverage impact

- Prior Faroe 7-station snapshot (after S03 completion): `39/53`.
- Updated snapshot after S08 completion: `45/53`.

Station rollup now:

- `S03`: `10/10`
- `S04`: `0/6`
- `S08`: `6/6`
- `S10`: `0/1`
- `S16`: `11/11`
- `S21`: `9/10`
- `S24`: `9/9`

## Artifact index

- Station wave summary:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-17/S08_station_wave_migration_summary_2026-02-17.md`
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-17/S08_station_wave_migration_summary_2026-02-17.json`
- Two-pass execution result:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-17/S08_station_wave_two_pass_execution_result_2026-02-17.json`
- Semantic reports and summary JSONs:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-17/S08_station_wave_*_semantic_validation_2026-02-17.{md,summary.json}`
- Updated Faroe scoreboard:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-17/Faroe_fw_7station_coverage_scoreboard_2026-02-17.md`
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-17/Faroe_fw_7station_coverage_scoreboard_2026-02-17.json`

## Recommended next step

Proceed with `S04` station wave next (remaining `6` cohorts), then re-publish the Faroe coverage scoreboard.
