# HANDOFF 2026-02-11 - FW20 Remediation (Tooling-Only)

## Scope
- Continue migration hardening with runtime separation preserved.
- Fix remaining failures from the 2026-02-11 FW20 station cohort run:
  - `Stofnfiskur mai 2025|3|2025` (`S16 Glyvradalur`) semantic gate fail.
  - `Stofnfiskur feb 2025|1|2025` (`S16 Glyvradalur`) semantic gate fail.
  - `BF mars 2025|2|2025` (`S08 Gjógv`) stage-resolution abort.

## Code Changes (migration tooling only)

### 1) Direct-linkage transition basis support
- File: `/Users/aquarian247/Projects/AquaMind/scripts/migration/tools/migration_semantic_validation_report.py`
- Change:
  - Stage transition count basis now uses linked source/destination populations when full linkage coverage exists, even when no temporary bridge hop is present.
  - These rows are tagged `entry_window_reason=direct_linkage` while still using `basis=fishgroup_bridge_aware`.
  - Existing downgrade behavior is preserved: positive bridge-derived deltas with outside-component incoming sources downgrade to `entry_window_reason=incomplete_linkage`.
- Why:
  - Removes false positive transition alerts caused by full direct linkage being forced into entry-window fallback.

### 2) Unmapped hall deterministic fallback
- File: `/Users/aquarian247/Projects/AquaMind/scripts/migration/tools/pilot_migrate_component.py`
- Change:
  - Added component-local hall-stage fallback for unresolved halls:
    - Build `(site, container_group)` stage observations from token-mapped member rows (`first_stage`/`last_stage`).
    - If observations are unanimous, use that stage as fallback for unresolved rows in that tuple.
    - Mixed/no evidence still fails fast.
- Why:
  - Resolves deterministic stage gaps like `S08 Gjógv / R-Høll` in `BF mars 2025` without adding runtime coupling.

## Validation Commands Executed

### Targeted 3-batch fix check
- Runner script: `/tmp/run_fw3_fixcheck_2026-02-11.py`
- Per batch command shape:
  1. `PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 python /Users/aquarian247/Projects/AquaMind/scripts/migration/clear_migration_db.py`
  2. `PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/pilot_migrate_input_batch.py --batch-key <BATCH_KEY> --expected-site <SITE> --use-csv /Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract --skip-environmental --parallel-workers 6 --parallel-blas-threads 1 --script-timeout-seconds 1200`
  3. `PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/migration_semantic_validation_report.py --component-key <COMPONENT_KEY> --report-dir <REPORT_DIR> --use-csv /Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract --check-regression-gates --output <REPORT_MD> --summary-json <REPORT_JSON>`
  4. `PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/migration_counts_report.py --batch-number <BATCH_NAME>`

## Targeted Results (completed)
- Summary TSV: `/tmp/fw3_fixcheck_2026-02-11/fw3_fixcheck_summary.tsv`
- Summary JSON: `/tmp/fw3_fixcheck_2026-02-11/fw3_fixcheck_summary.json`
- Consolidated markdown: `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/semantic_validation_fw3_fixcheck_2026-02-11.md`
- Before/after compact table: `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fw3_fixcheck_before_after_2026-02-11.md`

Outcome:
- `3/3` targeted batches now pass regression gates.
- `Stofnfiskur mai 2025`: `no_positive_transition_delta_without_mixed_batch` fail removed; transition reason includes `direct_linkage`.
- `Stofnfiskur feb 2025`: same fail removed; transition reason includes `direct_linkage` and one remaining `incomplete_linkage` fallback.
- `BF mars 2025`: migration no longer aborts at unresolved stage (`R-Høll`), and semantic gates pass.

Compact findings table:

| batch | non-bridge zero assignments before/after | gate result before/after | transition basis changes |
| --- | --- | --- | --- |
| Stofnfiskur mai 2025 | `0 -> 0` | `FAIL -> PASS` | `1/1 -> 2/0` (`no_bridge_path` fallback removed; `direct_linkage=1`) |
| Stofnfiskur feb 2025 | `0 -> 0` | `FAIL -> PASS` | `0/3 -> 1/2` (`no_bridge_path` fallback removed; `direct_linkage=1`, `incomplete_linkage=1`) |
| BF mars 2025 | `n/a (migration abort) -> 0` | `FAIL -> PASS` | `n/a -> 2/1` (stage-resolution abort removed; one transition remains `incomplete_linkage`, excluded from hard fail) |

## Documentation Updated
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/DATA_MAPPING_DOCUMENT.md`
  - Added component-local hall fallback behavior.
  - Updated stage-resolution guidance.
  - Added 2026-02-11 progress note with fixcheck evidence.
  - Added semantic direct-linkage basis note.
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/FISHTALK_SCHEMA_ANALYSIS.md`
  - Added replay clarification for 2026-02-11 direct-linkage transition basis and component-local hall fallback.

## Cohort Rerun Status
- Full 20-batch rerun was started with same profile to confirm no regressions:
  - runner: `/tmp/run_fw20_station_parallel_2026-02-11.py`
  - pre-fix backups saved under `/tmp/fw20_station_parallel_2026-02-11/pre_fix_backup/`
- Run was intentionally stopped after initial batches to avoid leaving a long unattended process in this pass.
- Existing full-cohort summary files remain the pre-fix baseline (`2026-02-11 02:20:34` timestamps):
  - `/tmp/fw20_station_parallel_2026-02-11/fw20_parallel_summary.tsv`
  - `/tmp/fw20_station_parallel_2026-02-11/fw20_parallel_summary.json`
  - `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/semantic_validation_fw20_station_parallel_2026-02-11.md`

## Unresolved Risks
1. Stage progression charts in UI can still show inflated historical totals due full-sum aggregation semantics vs entry-window semantics; this is outside migration tooling scope in this pass.
2. `Ext_GroupedOrganisation_v2.ProdStage` remains coarse (`Hatchery` for mixed lifecycle assignments); deterministic FW->Sea explicit linkage remains limited by source evidence.
3. Component-local hall fallback depends on token evidence quality; mixed or missing token evidence still requires explicit hall mapping or additional deterministic rule approval.

## Next Steps
1. Complete FW20 full rerun and append before/after gate delta using `/tmp/compare_fw20_before_after_2026-02-11.py`.
2. If FW20 rerun is stable, execute next wider cohort run with same script body and station guards.
3. Keep runtime code unchanged; if history chart inflation is prioritized, handle as AquaMind API/frontend aggregation workstream separately from migration logic.
