# HANDOFF 2026-02-17: FW24 Two-Pass Scottish Station Wave

## Scope

Execute the next Scottish station wave after FW21 using the established two-pass policy:

- strict station pass first (`--expected-site`, no mismatch override),
- controlled mixed-site recovery second (`--allow-station-mismatch`) for strict-blocked cohorts,
- semantic regression gates on all successful migrations.

Station selected from extract-derived `<30 months` cohorts (cutoff from horizon `2026-01-22`): `FW24 KinlochMoidart`.

## Non-negotiables honored

- Backup cutoff/horizon pinned to `2026-01-22`.
- Runtime remains FishTalk-agnostic (no runtime code changes).
- Source-specific handling stays in migration tooling/validation/reporting.
- Profile baseline remains `fw_default`.

## Wave execution summary

### Pass 1: Strict station guard

- Station: `FW24 KinlochMoidart`
- Cohorts attempted: `7`
- Migration success: `1/7`
- Semantic gate pass: `1/7`

Strict-only pass cohort:

- `SF APR 25|1|2025`

Strict-blocked cohorts (station preflight mismatch):

- `24Q1 LHS|1|2024`
- `SF SEP 23|4|2023`
- `NH DEC 23|5|2023`
- `AG JAN 24|2|2024`
- `SF MAY 24|3|2024`
- `SF AUG 24|4|2024`

All strict-blocked rows showed member-derived mixed sites `FW22 Applecross` + `FW24 KinlochMoidart`.

### Pass 2: Controlled mixed-site recovery

- Recovery cohort count: `6`
- Migration success: `6/6`
- Semantic gate pass: `6/6`

Recovery semantic gate closure:

- `SF SEP 23|4|2023` initially failed with `transition_alert_count=1` on `no_positive_transition_delta_without_mixed_batch`.
- Validation tooling was updated to downgrade positive bridge-aware deltas to `incomplete_linkage` when bridge-consolidation shape (`many linked sources -> fewer linked destinations`) indicates missing lineage context without mixed-batch evidence.
- Post-patch semantic rerun for `SF SEP 23|4|2023` now passes (deterministic rerun, same component/window).

Recovery operational notes:

- `SF MAY 24|3|2024` required `--batch-number "SF MAY 24 3"` due batch-number collision.
- `SF AUG 24|4|2024` required `--batch-number "SF AUG 24 4"` due batch-number collision.

## B01/B02 regression statement

**No new B01/B02 regression signal introduced by FW24 wave execution.**

S21 canary B01/B02 status from prior handoff remains unchanged (`NO REGRESSION OBSERVED`).

## Artifact index

- FW24 two-pass execution result:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-17/FW24_station_wave_two_pass_execution_result_2026-02-17.json`
- FW24 strict pass summary:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-17/FW24_station_wave_migration_summary_2026-02-17.md`
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-17/FW24_station_wave_migration_summary_2026-02-17.json`
- FW24 controlled recovery summary:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-17/FW24_allow_station_mismatch_recovery_summary_2026-02-17.md`
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-17/FW24_allow_station_mismatch_recovery_summary_2026-02-17.json`
- FW24 transfer evidence matrix:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-17/FW24_transfer_evidence_matrix_2026-02-17.md`
- Recovery semantic rerun artifact:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-17/FW24_allow_mismatch_SF_SEP_23_4_2023_semantic_validation_2026-02-17.md`
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-17/FW24_allow_mismatch_SF_SEP_23_4_2023_semantic_validation_2026-02-17.summary.json`
- Validation tooling update:
  - `scripts/migration/tools/migration_semantic_validation_report.py`

## Recommended next step

Proceed to the next Scottish station wave using the same two-pass pattern:

1. strict pass (`--expected-site`, no mismatch override),
2. controlled mixed-site recovery (`--allow-station-mismatch`) for strict-blocked cohorts,
3. semantic regression gates for all successful migrations.

Follow-on execution handoff:

- `aquamind/docs/progress/migration/handoffs/HANDOFF_2026-02-17_FW13_TWO_PASS_STATION_WAVE.md`
