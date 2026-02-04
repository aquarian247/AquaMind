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
     --use-csv scripts/migration/data/extract/
5) Validate
   - python scripts/migration/tools/migration_counts_report.py
   - python scripts/migration/tools/migration_verification_report.py

Environmental at scale (optional):
- python scripts/migration/tools/build_environmental_sqlite.py --input-dir scripts/migration/data/extract/ --output-path scripts/migration/data/extract/environmental_readings.sqlite --replace
- python scripts/migration/tools/pilot_migrate_environmental_all.py --use-sqlite scripts/migration/data/extract/environmental_readings.sqlite --workers 16

## Active entrypoints
- scripts/migration/setup_master_data.py
- scripts/migration/clear_migration_db.py
- scripts/migration/safety.py
- scripts/migration/history.py
- scripts/migration/tools/bulk_extract_fishtalk.py
- scripts/migration/tools/input_based_stitching_report.py
- scripts/migration/tools/pilot_migrate_input_batch.py
- scripts/migration/tools/pilot_migrate_component*.py
- scripts/migration/tools/migration_counts_report.py
- scripts/migration/tools/migration_verification_report.py
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
