# HANDOFF 2026-02-17: FW13 Two-Pass Scottish Station Wave

## Scope

Continue the Scottish `<30 months` station-wave rollout at `FW13 Geocrab` using the established two-pass policy:

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

- Station: `FW13 Geocrab`
- Cohorts attempted: `2`
- Migration success: `2/2`
- Semantic gate pass: `2/2`

Cohorts:

- `SF SEP 23|13|2024` (required `--batch-number "SF SEP 23 13"` due pre-existing batch-number collision)
- `24Q1 LHS ex-LC|13|2023`

### Pass 2: Controlled mixed-site recovery

- Not required (`0` strict mismatch blockers).

## B01/B02 regression statement

**No new B01/B02 regression signal introduced by FW13 wave execution.**

S21 canary B01/B02 status from prior handoffs remains unchanged (`NO REGRESSION OBSERVED`).

## Artifact index

- FW13 two-pass execution result:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-17/FW13_station_wave_two_pass_execution_result_2026-02-17.json`
- FW13 strict pass summary:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-17/FW13_station_wave_migration_summary_2026-02-17.md`
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-17/FW13_station_wave_migration_summary_2026-02-17.json`
- FW13 per-cohort semantic outputs:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-17/FW13_station_wave_SF_SEP_23_13_2024_semantic_validation_2026-02-17.md`
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-17/FW13_station_wave_SF_SEP_23_13_2024_semantic_validation_2026-02-17.summary.json`
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-17/FW13_station_wave_24Q1_LHS_ex_LC_13_2023_semantic_validation_2026-02-17.md`
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-17/FW13_station_wave_24Q1_LHS_ex_LC_13_2023_semantic_validation_2026-02-17.summary.json`

## Recommended next step

Scottish freshwater `<30 months` station-wave set is now covered (`FW21`, `FW22`, `FW24`, `FW13`).

Next execution options:

1. run analogous two-pass rollout for the next non-FW station family (if in current migration scope), or
2. run focused FT evidence confirmation for FW24 mixed-site cohorts now marked PASS under controlled mismatch policy.
