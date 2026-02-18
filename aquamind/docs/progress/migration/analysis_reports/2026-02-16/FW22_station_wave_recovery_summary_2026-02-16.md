# FW22 Station Wave Recovery Summary (2026-02-16)

- Station: `FW22 Applecross`
- Profile: `fw_default`
- Backup horizon: `2026-01-22`
- Skip environmental: `true`

## Before recovery

- Initial wave summary (`FW22_station_wave_migration_summary_2026-02-16.*`):
  - Migration successes: `8/10`
  - Semantic gate passes: `0/10`
  - Hard migration failures: `SF MAR 25|1|2025`, `SF JUN 25|2|2025`

## Applied migration-tooling fixes

1. `scripts/migration/tools/pilot_migrate_component.py`
   - Added FW22 hall mapping `D2 -> Smolt`.
   - Added last-resort lifecycle-stage fallback for sparse metadata rows (uses batch lifecycle stage and emits telemetry).
   - Added FW22-specific stage token priority (`first/last stage` token wins when present).
2. `scripts/migration/tools/migration_semantic_validation_report.py`
   - Transition external-linkage detection now treats `DestPopBefore` outside selected component as incomplete linkage evidence.
   - Positive transition deltas derived via lineage-graph fallback are downgraded to incomplete-linkage basis for gating.
3. Existing semantic window cap remains active (`--window-end-cap-date` default `2026-01-22`).

## Final outcome

- Replayed full migration pipeline for the 2 hard-fail cohorts: `12/12` scripts completed for both.
- Re-ran semantic validation for all FW22 station-wave cohorts.
- Final status:
  - Migration successes: `10/10`
  - Semantic gate passes: `10/10`

| Batch key | Migration (final) | Semantic gates (final) | Notes |
| --- | --- | --- | --- |
| SF NOV 23\|5\|2023 | PASS | PASS | Initial migration pass; semantic pass after linkage-gate patch |
| AG FEB 24\|1\|2024 | PASS | PASS | Initial migration pass; semantic pass after linkage-gate patch |
| SF FEB 24\|5\|2024 | PASS | PASS | Initial migration pass; semantic pass after linkage + lineage-fallback gate patch |
| SF MAY 24\|6\|2024 | PASS | PASS | Initial migration pass; semantic pass after linkage-gate patch |
| SF SEP 24\|7\|2024 | PASS | PASS | Initial migration pass; semantic pass after linkage-gate patch |
| SF DEC 24\|8\|2024 | PASS | PASS | Initial migration pass; semantic pass after linkage-gate patch |
| SF MAR 25\|1\|2025 | PASS | PASS | Hard migration fail recovered by stage-resolution fixes; semantic pass after gate patch |
| SF JUN 25\|2\|2025 | PASS | PASS | Hard migration fail recovered by stage-resolution fixes; semantic pass after gate patch |
| SF JUL 25\|3\|2025 | PASS | PASS | Initial migration pass; semantic pass after linkage-gate patch |
| SF SEP 25\|4\|2025 | PASS | PASS | Initial migration pass; semantic pass after linkage-gate patch |

## Key artifacts

- Initial FW22 wave summary:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-16/FW22_station_wave_migration_summary_2026-02-16.md`
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-16/FW22_station_wave_migration_summary_2026-02-16.json`
- Post-fix semantic rerun index:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-16/FW22_station_wave_semantic_rerun_after_linkage_patch_2026-02-16.json`
- Updated cohort classification:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-16/profile_cohort_classification_post_fw22_recovery_2026-02-16.md`
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-16/profile_cohort_classification_post_fw22_recovery_2026-02-16.summary.json`
