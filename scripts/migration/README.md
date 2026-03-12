# FishTalk -> AquaMind Migration Scripts

## Start here (canonical docs)
- aquamind/docs/progress/migration/README.md
- aquamind/docs/progress/migration/MIGRATION_CANONICAL.md
- aquamind/docs/progress/migration/MIGRATION_LESSONS_LEARNED.md

## Current, supported pipeline (input-based + CSV ETL)
1) Setup / safety
   - python scripts/migration/setup_master_data.py
   - Always target migr_dev (safety.py enforces this)
2) Bulk extract FishTalk -> CSV
   - python scripts/migration/tools/bulk_extract_fishtalk.py --output scripts/migration/data/extract/
3) Build input-based batches
   - python scripts/migration/tools/input_based_stitching_report.py --output-dir scripts/migration/output/input_stitching
4) Migrate a batch (recommended)
   - PYTHONPATH=/path/to/AquaMind SKIP_CELERY_SIGNALS=1 \
     python scripts/migration/tools/pilot_migrate_input_batch.py \
     --batch-key "<InputName>|<InputNumber>|<YearClass>" \
     --expected-site "<Station Name>" \
     --use-csv scripts/migration/data/extract/ \
     --expand-subtransfer-descendants \
     --transfer-edge-scope source-in-scope
4b) Guarded FW->Sea continuation (selected provisional candidates only)
   - PYTHONPATH=/path/to/AquaMind SKIP_CELERY_SIGNALS=1 \
     python scripts/migration/tools/pilot_migrate_input_batch.py \
     --batch-key "<SeaInputName>|<InputNumber>|<YearClass>" \
     --use-csv scripts/migration/data/extract/ \
     --migration-profile fw_default \
     --full-lifecycle \
     --include-fw-batch "<FWInputName>|<InputNumber>|<YearClass>" \
     --batch-number "<Existing FW batch number>" \
     --sea-anchor-population-id "<SeaPopulationID>" \
     --expand-subtransfer-descendants \
     --transfer-edge-scope source-in-scope
5) Full action replays (per component, CSV)
   - python scripts/migration/tools/pilot_migrate_component_transfers.py
   - python scripts/migration/tools/pilot_migrate_component_feeding.py
   - python scripts/migration/tools/pilot_migrate_component_mortality.py
   - python scripts/migration/tools/pilot_migrate_component_culling.py
   - python scripts/migration/tools/pilot_migrate_component_escapes.py
   - python scripts/migration/tools/pilot_migrate_component_treatments.py
   - python scripts/migration/tools/pilot_migrate_component_lice.py
   - python scripts/migration/tools/pilot_migrate_component_health_journal.py
   - python scripts/migration/tools/pilot_migrate_component_growth_samples.py
   - python scripts/migration/tools/pilot_migrate_component_harvest.py
6) Validate
   - python scripts/migration/tools/migration_semantic_validation_report.py \
     --component-key <component_key> \
     --report-dir <component_report_dir> \
     --use-csv scripts/migration/data/extract \
     --stage-entry-window-days 2
     # optional regression gate mode:
     # --check-regression-gates --summary-json <path>
   - python scripts/migration/tools/migration_pilot_regression_check.py \
     --analysis-dir aquamind/docs/progress/migration/analysis_reports/2026-02-06 \
     --use-csv scripts/migration/data/extract
   - python scripts/migration/tools/migration_counts_report.py
   - python scripts/migration/tools/migration_verification_report.py

Environmental at scale (optional):
- python scripts/migration/tools/build_environmental_sqlite.py --input-dir scripts/migration/data/extract/ --output-path scripts/migration/data/extract/environmental_readings.sqlite --replace
- python scripts/migration/tools/pilot_migrate_environmental_all.py --use-sqlite scripts/migration/data/extract/environmental_readings.sqlite --workers 16

## Active entrypoints
- scripts/migration/setup_master_data.py
- scripts/migration/tools/pilot_migrate_health_master_data.py
- scripts/migration/clear_migration_db.py
- scripts/migration/safety.py
- scripts/migration/history.py
- scripts/migration/tools/bulk_extract_fishtalk.py
- scripts/migration/tools/input_based_stitching_report.py
- scripts/migration/tools/pilot_migrate_input_batch.py
- scripts/migration/tools/pilot_migrate_component*.py
- scripts/migration/tools/migration_counts_report.py
- scripts/migration/tools/migration_verification_report.py
- scripts/migration/tools/migration_semantic_validation_report.py
- scripts/migration/tools/migration_pilot_regression_check.py
- scripts/migration/tools/build_environmental_sqlite.py
- scripts/migration/tools/pilot_migrate_environmental_all.py

## Legacy + analysis
- scripts/migration/legacy/ contains deprecated frameworks and tools (no shims in current paths).
- scripts/migration/analysis/ contains experimental or one-off analysis scripts.

## Configuration
- scripts/migration/migration_config.json defines SQL profiles and connection settings.
- scripts/migration/config.py loads the config for tools that read from SQL Server.

## Notes
- Use SKIP_CELERY_SIGNALS=1 for all migration runs.
- Use --use-csv for performance and repeatability.
- SubTransfers transfer replay now expands root-source chains before scope filtering. Use `source-in-scope` as the FW default; `internal-only` is for intentionally dropping expanded destinations outside the migrated component.
- Weight samples are in grams (FishTalk) and should not be treated as kg.
- Use `--expected-site` for both `pilot_migrate_input_batch.py` and `pilot_migrate_component.py` when station identity must be strict.
- Linked FW->Sea continuation now treats sea cohorts as new marine-side inputs and is **anchor-scoped by default**. Do not ingest a full sea component for provisional rows unless an explicit operator override has been approved.
- Mortality/culling/escape replay synchronizes assignment population count to: `baseline_population_count - known removals` per population mapping.
