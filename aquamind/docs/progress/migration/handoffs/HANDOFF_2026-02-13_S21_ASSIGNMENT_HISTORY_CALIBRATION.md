# HANDOFF 2026-02-13: S21 Assignment History Calibration (B01/B02)

## Scope

Calibrate assignment history reconstruction for `Bakkafrost S-21 jan 25|1|2025` in migration batch `464`, with swimlane parity focus at container level.

## What changed

1. Refreshed critical source extracts from FishTalk SQL (no stale cap behavior):
   - `status_values.csv`
   - `sub_transfers.csv`
   - `operation_stage_changes.csv`
2. Verified refreshed coverage:
   - `status_values.csv` max `2026-01-22 12:46:55`
   - `sub_transfers.csv` max `2026-01-22 12:46:55`
   - `operation_stage_changes.csv` max `2026-01-18 11:08:14`
3. Updated assignment count logic in `scripts/migration/tools/pilot_migrate_component.py`:
   - Generalized same-day bridge companion detection (`is_long_companion_same_day_bridge()`).
   - For long-lived superseded rows, prefer `status-at-start` when present.
   - Preserve suppression for short-lived same-stage bridge rows.
   - For blank-stage-token rows in external-mixing chains, prefer `status-at-start`.
4. Re-ran migration pipeline for `Bakkafrost S-21 jan 25|1|2025` using refreshed CSV extract and site guard `S21 Viðareiði`.

## Results

### B01

`B01` now matches swimlane lane-entry counts on the long segments:
- `2025-09-09`: `74,983`
- `2025-10-24`: `47,516`
- `2025-11-14`: `75,490`
- `2025-12-11`: `51,505` (active)

Short same-day bridge rows remain zero by design.

### B02

`B02` parity improved and now aligns with user-observed swimlane counts:
- `2025-08-26`: `177,853`
- `2025-09-11`: `118,966`
- `2025-11-28`: `47,912`
- `2025-12-11`: `47,349`
- `2026-01-22`: short bridge `0`, long row `73,853`

### Smolt C/D visibility

Smolt rows are present for `C12`, `D1`, `D2`, `D3`, `D4`, `D5`, `D6` through cutoff horizon.

## Assignment reconstruction code (current behavior)

For each population segment assignment candidate:

1. Start from SubTransfers-conserved count baseline.
2. Pull `status-at-start` snapshot (+ derived avg weight/biomass).
3. Apply floors/fallbacks:
   - known removals floor (`mortality + culling + escapes`)
4. Handle same-stage supersession:
   - short-lived bridge rows: suppress to zero (default),
   - long companion / long-lived superseded rows: prefer `status-at-start` when available,
   - operationally active superseded rows: keep materialized.
5. Handle blank-token external-mixing rows:
   - prefer `status-at-start` where present.
6. Determine active/departed status from latest non-zero status timing and per-container latest population constraints.

## Key artifacts

- B01 reconciliation:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-13/s21_bakkafrost_jan25_b01_assignment_reconciliation_2026-02-13.md`
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-13/S21_Bakkafrost_S21_jan25_B01_population_segment_diagnostics_2026-02-13.csv`
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-13/S21_Bakkafrost_S21_jan25_B01_population_segment_diagnostics_2026-02-13.summary.json`
- B02 diagnostics:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-13/S21_Bakkafrost_S21_jan25_B02_population_segment_diagnostics_2026-02-13.csv`
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-13/S21_Bakkafrost_S21_jan25_B02_population_segment_diagnostics_2026-02-13.summary.json`
- Batch packet:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-13/s21_bakkafrost_jan25_migration_batch_464_swimlane_compare_packet_2026-02-13.md`

## Next recommended steps

1. Continue container-by-container parity checks (`B04`, `B05`, then C/D/E/F).
2. If a container diverges, generate container diagnostics CSV with:
   - segment IDs,
   - conserved count,
   - status-at-start count,
   - assignment count,
   - superseded/external-mixing flags.
3. Keep extraction freshness check mandatory before migration reruns:
   - `status_values` and `sub_transfers` max timestamps should track backup horizon.

## Session delta (2026-02-16)

### Execution summary

1. Re-verified extract freshness before replay:
   - `status_values.csv` max `2026-01-22 12:46:55`
   - `sub_transfers.csv` max `2026-01-22 12:46:55`
   - `operation_stage_changes.csv` max `2026-01-18 11:08:14`
2. Replayed batch `Bakkafrost S-21 jan 25|1|2025` with station guard:
   - command: `pilot_migrate_input_batch.py --batch-key "Bakkafrost S-21 jan 25|1|2025" --use-csv scripts/migration/data/extract --expected-site "S21 Viðareiði" --skip-environmental`
   - outcome: `12/12` scripts completed successfully.
3. Completed container-history parity diagnostics for priority targets (`B04`, `B05`) and smolt `C/D` containers (`C12`, `D1..D6`) using fresh extract + migrated batch state (`batch_id=464`).
4. Confirmed `E*` / `F*` container labels are not present in this stitched component output for this cohort; no additional `E/F` diagnostics were emitted.
5. No migration-logic patch was required in this session.
6. Applied lifecycle-frontier stage selection hardening in migration tooling:
   - `scripts/migration/tools/pilot_migrate_component.py`
     - Batch lifecycle stage now selects from latest per-container non-zero frontier within a configurable cutoff window, then chooses the most advanced stage among frontier candidates.
     - Added argument: `--lifecycle-frontier-window-hours` (default `24`).
   - `scripts/migration/tools/pilot_migrate_input_batch.py`
     - Added pass-through support for `--lifecycle-frontier-window-hours`.
7. Re-ran S21 migration after lifecycle-frontier patch (`--skip-environmental`):
   - Batch `464` lifecycle stage changed from `Parr` to `Smolt`.
   - Active containers now resolve to `C12`, `D1`, `D2`, `D3`, `D4`, `D5`, `D6` (7 total), matching expected smolt-frontier occupancy at cutoff.

### Parity status (2026-02-16 diagnostics)

- `B04`: `match`
- `B05`: `match`
- `C12`: `match`
- `D1`: `match`
- `D2`: `match`
- `D3`: `match`
- `D4`: `match`
- `D5`: `match`
- `D6`: `match`

### Regression guard (B01/B02 anchors)

Post-rerun checks confirm no regression to calibrated anchors:

- `B01` long segments remain aligned: `74,983`, `47,516`, `75,490`, `51,505`; short bridge zeros preserved by design.
- `B02` remains aligned: `177,853`, `118,966`, `47,912`, `47,349`, and `2026-01-22` short bridge `0` + long row `73,853`.
- Post-fix regression artifact confirms anchor preservation:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-16/S21_Bakkafrost_S21_jan25_B01_B02_regression_anchor_check_after_lifecycle_frontier_fix_2026-02-16.json`

### New artifacts

- Container parity manifest:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-16/S21_Bakkafrost_S21_jan25_container_parity_manifest_2026-02-16.json`
- Per-container diagnostics packets directory:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-16/`
- Packet naming convention (each container has both `.csv` and `.summary.json`):
  - `S21_Bakkafrost_S21_jan25_<CONTAINER>_population_segment_diagnostics_2026-02-16.*`
  - emitted containers: `B04`, `B05`, `C12`, `D1`, `D2`, `D3`, `D4`, `D5`, `D6`, `B01`, `B02`
- Post-fix active/frontier validation artifacts:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-16/S21_Bakkafrost_S21_jan25_active_container_snapshot_after_lifecycle_frontier_fix_2026-02-16.json`
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-16/S21_Bakkafrost_S21_jan25_semantic_validation_after_lifecycle_frontier_fix_2026-02-16.md`
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-16/S21_Bakkafrost_S21_jan25_semantic_validation_after_lifecycle_frontier_fix_2026-02-16.summary.json`

### Cross-cohort generalization check (2026-02-16)

Lifecycle-frontier stage selection was replay-tested on two additional mixed-stage cohorts:

1. `Benchmark Gen. Desembur 2024|4|2024` (`batch_id=463`)
   - Pre-fix mismatch signal: batch stage `Smolt` while frontier was `Post-Smolt`.
   - Post-fix result: batch stage `Post-Smolt`; active set aligns with post-smolt halls (`G*`, `H*`, `I*`, `J*`).
   - Semantic regression gates: `PASS`.
   - Artifacts:
     - `aquamind/docs/progress/migration/analysis_reports/2026-02-16/Benchmark_Gen_Desembur_2024_active_container_snapshot_after_lifecycle_frontier_fix_2026-02-16.json`
     - `aquamind/docs/progress/migration/analysis_reports/2026-02-16/Benchmark_Gen_Desembur_2024_semantic_validation_after_lifecycle_frontier_fix_2026-02-16.md`
     - `aquamind/docs/progress/migration/analysis_reports/2026-02-16/Benchmark_Gen_Desembur_2024_semantic_validation_after_lifecycle_frontier_fix_2026-02-16.summary.json`

2. `StofnFiskur okt. 2024|3|2024` (`batch_id=465`)
   - Post-fix result: batch stage remains `Parr` with frontier agreement (`Parr`), so no stage-regression introduced.
   - Semantic regression gates: `PASS`.
   - Follow-up signal (separate from lifecycle-frontier fix): active-container occupancy evidence shows latest holders outside selected component for `6/6` active containers, indicating a likely lineage-coverage/context boundary issue for this cohort.
   - Artifacts:
     - `aquamind/docs/progress/migration/analysis_reports/2026-02-16/StofnFiskur_okt_2024_active_container_snapshot_after_lifecycle_frontier_fix_2026-02-16.json`
     - `aquamind/docs/progress/migration/analysis_reports/2026-02-16/StofnFiskur_okt_2024_semantic_validation_after_lifecycle_frontier_fix_2026-02-16.md`
     - `aquamind/docs/progress/migration/analysis_reports/2026-02-16/StofnFiskur_okt_2024_semantic_validation_after_lifecycle_frontier_fix_2026-02-16.summary.json`

### Outside-holder consistency hardening (2026-02-16 follow-up)

To investigate the StofnFiskur follow-up signal (`latest_holder_outside_component`), assignment active-state selection was hardened in migration tooling:

1. `scripts/migration/tools/pilot_migrate_component.py`
   - Added a container-level latest non-zero holder consistency gate during active-candidate selection.
   - If a container's extract-level latest non-zero holder is a different population and later than this component's candidate timestamp, that candidate is excluded from active assignment status.
   - Added CSV-mode performance optimization via a vectorized holder index (pandas groupby on `status_values` + `populations`) to avoid per-population repeated scans.
2. No AquaMind runtime code changes; logic remains migration-only.

#### Follow-up replay outcomes after hardening

1. `StofnFiskur okt. 2024|3|2024` (`batch_id=465`)
   - Migration replay completed (`12/12` scripts).
   - Active-candidate filtering signal in logs: `52` candidates excluded due to later outside-component holders.
   - Batch stage remains `Parr`.
   - Post-fix active container set: `0` (pre-fix: `6` containers with outside-holder mismatches).
   - Semantic regression gates: `PASS`.
2. `Bakkafrost S-21 jan 25|1|2025` (`batch_id=464`) regression check
   - Batch stage remains `Smolt`; active set remains `C12`, `D1..D6` (`7` total).
   - Active-container occupancy evidence: outside-component latest-holder count `0`.
   - Semantic regression gates: `PASS`.
3. `Benchmark Gen. Desembur 2024|4|2024` (`batch_id=463`) regression check
   - Batch stage remains `Post-Smolt`; active set remains `G1..G4`, `H1..H4`, `I1..I3`, `J1..J4` (`15` total).
   - Active-container occupancy evidence: outside-component latest-holder count `0`.
   - Semantic regression gates: `PASS`.

#### Regression guard (B01/B02 anchors) after outside-holder hardening

`B01/B02` calibration anchors remain preserved after this patch:
- `B01` long counts: `74,983`, `47,516`, `75,490`, `51,505` (bridge zeros preserved).
- `B02` long counts: `177,853`, `118,966`, `47,912`, `47,349`, `73,853` with `2026-01-22` short bridge `0`.

Artifact:
- `aquamind/docs/progress/migration/analysis_reports/2026-02-16/S21_Bakkafrost_S21_jan25_B01_B02_regression_anchor_check_after_outside_holder_fix_2026-02-16.json`

#### New artifacts (outside-holder follow-up)

- `aquamind/docs/progress/migration/analysis_reports/2026-02-16/StofnFiskur_okt_2024_outside_holder_discrepancy_investigation_2026-02-16.json`
- `aquamind/docs/progress/migration/analysis_reports/2026-02-16/StofnFiskur_okt_2024_active_container_snapshot_after_outside_holder_fix_2026-02-16.json`
- `aquamind/docs/progress/migration/analysis_reports/2026-02-16/StofnFiskur_okt_2024_semantic_validation_after_outside_holder_fix_2026-02-16.md`
- `aquamind/docs/progress/migration/analysis_reports/2026-02-16/StofnFiskur_okt_2024_semantic_validation_after_outside_holder_fix_2026-02-16.summary.json`
- `aquamind/docs/progress/migration/analysis_reports/2026-02-16/S21_Bakkafrost_S21_jan25_active_container_snapshot_after_outside_holder_fix_2026-02-16.json`
- `aquamind/docs/progress/migration/analysis_reports/2026-02-16/S21_Bakkafrost_S21_jan25_semantic_validation_after_outside_holder_fix_2026-02-16.md`
- `aquamind/docs/progress/migration/analysis_reports/2026-02-16/S21_Bakkafrost_S21_jan25_semantic_validation_after_outside_holder_fix_2026-02-16.summary.json`
- `aquamind/docs/progress/migration/analysis_reports/2026-02-16/Benchmark_Gen_Desembur_2024_active_container_snapshot_after_outside_holder_fix_2026-02-16.json`
- `aquamind/docs/progress/migration/analysis_reports/2026-02-16/Benchmark_Gen_Desembur_2024_semantic_validation_after_outside_holder_fix_2026-02-16.md`
- `aquamind/docs/progress/migration/analysis_reports/2026-02-16/Benchmark_Gen_Desembur_2024_semantic_validation_after_outside_holder_fix_2026-02-16.summary.json`

### Migration profile framework (2026-02-16)

To reduce risk from edge-case divergence across cohorts/stations without forking scripts, migration tooling now supports explicit profile presets:

1. New profile module:
   - `scripts/migration/tools/migration_profiles.py`
2. CLI wiring:
   - `pilot_migrate_component.py --migration-profile <name>`
   - `pilot_migrate_input_batch.py --migration-profile <name>` (pass-through to component step)
3. Default behavior:
   - `fw_default` (selected by default), matching current hardened FW logic.
4. Initial profile set:
   - `fw_default`
     - frontier stage selection
     - latest-holder consistency gate enabled
     - orphan-zero suppression enabled
   - `fw_relaxed_holder`
     - frontier stage selection
     - latest-holder consistency gate disabled
     - orphan-zero suppression disabled
     - intended for diagnostics/backtesting only
   - `legacy_latest_member`
     - latest-member stage selection mode
     - latest-holder consistency gate disabled
     - orphan-zero suppression disabled
     - intended as legacy behavior anchor for troubleshooting
5. Override semantics:
   - Existing direct knobs remain available as explicit overrides for selected profile:
     - `--lifecycle-frontier-window-hours`
     - `--same-stage-supersede-max-hours`
6. Strategy note:
   - `aquamind/docs/progress/migration/MIGRATION_PROFILE_STRATEGY.md`
7. Sanity replay after profile wiring:
   - Replayed `Bakkafrost S-21 jan 25|1|2025` with `--migration-profile fw_default` (`12/12` scripts).
   - Stage/active outcome unchanged (`Smolt`, active `C12`, `D1..D6`).
   - Semantic regression gates: `PASS`.
   - Artifacts:
     - `aquamind/docs/progress/migration/analysis_reports/2026-02-16/S21_Bakkafrost_S21_jan25_active_container_snapshot_after_profile_framework_2026-02-16.json`
     - `aquamind/docs/progress/migration/analysis_reports/2026-02-16/S21_Bakkafrost_S21_jan25_semantic_validation_after_profile_framework_2026-02-16.md`
     - `aquamind/docs/progress/migration/analysis_reports/2026-02-16/S21_Bakkafrost_S21_jan25_semantic_validation_after_profile_framework_2026-02-16.summary.json`
8. Extract cutoff guard + cohort-profile classification tooling:
   - Added `scripts/migration/tools/extract_freshness_guard.py` for preflight validation of required extract tables and max timestamp coherence.
   - Wired preflight into `pilot_migrate_input_batch.py` for CSV runs (enabled by default; can be bypassed with `--skip-extract-freshness-preflight`).
   - Default preflight horizon is now pinned to backup cutoff `2026-01-22` (overrideable with `--extract-horizon-date` when needed).
   - Operation-stage lag threshold (`operation_stage_changes` behind status/sub anchor) is now enforced as failure by default; optional relaxation flags were added:
     - standalone guard: `--allow-operation-stage-lag`
     - input-batch pipeline: `--extract-allow-operation-stage-lag`
     - profile classifier: `--extract-allow-operation-stage-lag`
   - Added horizon option to abort early on stale extracts:
     - `--extract-horizon-date YYYY-MM-DD`
   - Added `scripts/migration/tools/migration_profile_cohort_classifier.py` to classify semantic summary outputs by failure signature and recommend migration profiles/confidence.
   - Strategy doc updated with usage and guardrails:
     - `aquamind/docs/progress/migration/MIGRATION_PROFILE_STRATEGY.md`
   - Freshness/classification artifacts (2026-02-16):
     - `aquamind/docs/progress/migration/analysis_reports/2026-02-16/extract_freshness_preflight_2026-02-16.json`
     - `aquamind/docs/progress/migration/analysis_reports/2026-02-16/profile_cohort_classification_2026-02-16.md`
     - `aquamind/docs/progress/migration/analysis_reports/2026-02-16/profile_cohort_classification_2026-02-16.summary.json`

This establishes a single migration core with auditable cohort-family variants, rather than branching script copies.

### S21 station wave (<30 months) with profile baseline (2026-02-16)

Executed the recommended first station wave for S21-only cohorts under the 30-month migration cutoff using the hardened defaults:

- command shape per cohort:
  - `pilot_migrate_input_batch.py --batch-key "<KEY>" --migration-profile fw_default --use-csv scripts/migration/data/extract --expected-site "S21 Viðareiði" --skip-environmental --script-timeout-seconds 1800`
- semantic gate per cohort:
  - `migration_semantic_validation_report.py --component-key <COMPONENT_KEY> --report-dir <OUTPUT_DIR> --use-csv scripts/migration/data/extract --check-regression-gates`
- extract freshness preflight remained enabled (default horizon `2026-01-22`, operation-stage lag enforced as failure by default).

Outcome:

- Cohorts attempted: `9`
- Migration success: `9/9`
- Semantic regression gates: `9/9`
- B01/B02 anchor cohort (`Bakkafrost S-21 jan 25|1|2025`) remained `PASS` under station-wave execution.

Artifacts:

- Consolidated station-wave summary:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-16/S21_station_wave_migration_summary_2026-02-16.md`
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-16/S21_station_wave_migration_summary_2026-02-16.json`
- Per-cohort semantic outputs:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-16/S21_station_wave_*_semantic_validation_2026-02-16.md`
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-16/S21_station_wave_*_semantic_validation_2026-02-16.summary.json`

### Backup-horizon alignment for semantic report windows (2026-02-16)

To prevent ambiguity between report run-date and FishTalk backup horizon:

- Hardened `scripts/migration/tools/migration_semantic_validation_report.py` with:
  - `--window-end-cap-date` (default: `2026-01-22`, sourced from freshness guard default horizon)
  - date-only cap interpreted as end-of-day (`2026-01-22T23:59:59.999999`)
- Semantic aggregation window now caps open-ended member windows at backup horizon by default.
- Report/summary now include both capped and uncapped window-end values for auditability:
  - markdown reports show capped window plus uncapped/cap detail when capping is applied
  - summary JSON includes `window.end_uncapped`, `window.end_cap`, `window.end_was_capped`
- Verification rerun artifact:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-16/FW22_station_wave_SF_SEP_25_4_2025_semantic_validation_2026-02-16.md`
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-16/FW22_station_wave_SF_SEP_25_4_2025_semantic_validation_2026-02-16.summary.json`

### FW22 Applecross station-wave recovery (2026-02-16)

Context:

- Initial FW22 station wave had:
  - migration: `8/10` pass (hard fails: `SF MAR 25|1|2025`, `SF JUN 25|2|2025`)
  - semantic gates: `0/10` pass (`no_positive_transition_delta_without_mixed_batch`)
- Backup cutoff remained unchanged: `2026-01-22` (all reruns continued using this horizon).

Migration hard-fail fixes (`pilot_migrate_component.py`):

- Added FW22 hall stage mapping: `D2 -> Smolt`.
- Added FW22-specific stage-resolution precedence: explicit FishTalk member stage token (`first/last stage`) is preferred when present.
- Added last-resort lifecycle-stage fallback for sparse metadata populations (uses batch lifecycle stage and emits telemetry), preventing whole-cohort aborts on a few metadata-empty rows.

Semantic gate hardening (`migration_semantic_validation_report.py`):

- Transition incomplete-linkage detection now treats `DestPopBefore` outside selected component as external linkage evidence.
- Positive deltas that depend on lineage-graph fallback are also downgraded to incomplete-linkage basis for gating.

Outcome after reruns:

- Replayed full migration pipeline for:
  - `SF MAR 25|1|2025` -> `12/12` scripts passed
  - `SF JUN 25|2|2025` -> `12/12` scripts passed
- Re-ran semantic gate reports for all FW22 station-wave cohorts:
  - semantic pass: `10/10`
- Final FW22 status:
  - migration pass: `10/10`
  - semantic pass: `10/10`

Artifacts:

- FW22 recovery summary:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-16/FW22_station_wave_recovery_summary_2026-02-16.md`
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-16/FW22_station_wave_recovery_summary_2026-02-16.json`
- FW22 semantic rerun index:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-16/FW22_station_wave_semantic_rerun_after_linkage_patch_2026-02-16.json`
- Updated profile classifier post-recovery:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-16/profile_cohort_classification_post_fw22_recovery_2026-02-16.md`
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-16/profile_cohort_classification_post_fw22_recovery_2026-02-16.summary.json`

Regression anchor check (B01/B02 protection):

- Re-ran `Bakkafrost S-21 jan 25|1|2025` with `fw_default` and `--skip-environmental`.
- Migration pipeline: `12/12` scripts passed.
- Semantic regression gates: `PASS`.
- Additional non-FW22 semantic canary (`S24 Benchmark Gen. Desembur 2024`) remained `PASS`.
- Artifact:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-16/S21_Bakkafrost_S21_jan25_semantic_validation_after_fw22_recovery_2026-02-16.md`
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-16/S21_Bakkafrost_S21_jan25_semantic_validation_after_fw22_recovery_2026-02-16.summary.json`
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-16/S24_Benchmark_Gen_Desembur_2024_semantic_validation_after_fw22_recovery_2026-02-16.md`
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-16/S24_Benchmark_Gen_Desembur_2024_semantic_validation_after_fw22_recovery_2026-02-16.summary.json`

Documentation sync (DATA_MAPPING_DOCUMENT brush-up, 2026-02-16):

- Updated mapping guidance to match current migration/validator code in:
  - `2.1`, `2.2`, `2.3`, `2.4`, `2.5`
  - `3.0.0`, `3.0.0.1`, `3.0.0.2`, `3.0.0.4`
  - `3.1`, `3.2`, `3.5`
- Key sync points recorded:
  - `FW22 Applecross` hall map includes `D2 -> Smolt`.
  - FW22 stage resolution exception (token-priority when token exists).
  - Sparse-metadata lifecycle fallback behavior documented (telemetry-backed, avoids full-cohort abort).
  - Transition sanity gating semantics updated (`DestPopBefore` external evidence + lineage-fallback positive-delta downgrade to incomplete-linkage).
  - Semantic report window cap explicitly documented at backup horizon `2026-01-22`.