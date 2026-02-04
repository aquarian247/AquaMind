# FishTalk -> AquaMind Migration Docs (Index)

This folder is the canonical home for migration documentation.

## Start here (current, canonical)
1. MIGRATION_CANONICAL.md - runbook + current status
2. MIGRATION_LESSONS_LEARNED.md - what works vs what does not
3. DATA_MAPPING_DOCUMENT.md - field-level mapping blueprint
4. FISHTALK_SCHEMA_ANALYSIS.md - source schema corrections/notes
5. MIGRATION_BEST_PRACTICES.md - audit/idempotency standards
6. MIGRATION_TIMELINE_SUMMARY_2026-01-28.md - consolidated timeline

## Supporting documents
- INFRA_ETL_PLAN.md - infrastructure ETL plan (staging-based)
- sql/infra_staging_extracts.sql - staging extract SQL for infra
- model_audit/model_audit_checklist.md - data-model audit plan (Population vs Batch)
- model_audit/model_audit_evidence_2026-01-28.md - evidence from CSV extracts

## Working artifacts (organized)
- batch_overviews/ - batch-level overviews (FW history summaries)
- station_traces/ - station-level trace outputs
- analysis_reports/ - linkage scans, backtraces, targeted scans
- handoffs/ - session handoffs and next-agent briefs

## Command map (current pipeline)
1) Bulk extract FishTalk -> CSV
   - python scripts/migration/tools/bulk_extract_fishtalk.py --output scripts/migration/data/extract/
2) Build input-based batches
   - python scripts/migration/tools/input_based_stitching_report.py --output-dir scripts/migration/output/input_stitching
3) Migrate a batch (recommended)
   - PYTHONPATH=/path/to/AquaMind SKIP_CELERY_SIGNALS=1 \\
     python scripts/migration/tools/pilot_migrate_input_batch.py \\
     --batch-key \"<InputName>|<InputNumber>|<YearClass>\" \\
     --use-csv scripts/migration/data/extract/
4) Validate
   - python scripts/migration/tools/migration_counts_report.py
   - python scripts/migration/tools/migration_verification_report.py
5) Environmental at scale (optional)
   - python scripts/migration/tools/build_environmental_sqlite.py \\
     --input-dir scripts/migration/data/extract/ \\
     --output-path scripts/migration/data/extract/environmental_readings.sqlite --replace
   - python scripts/migration/tools/pilot_migrate_environmental_all.py \\
     --use-sqlite scripts/migration/data/extract/environmental_readings.sqlite --workers 16

## Archive (historical only)
See archive/README.md. This includes handovers, session prompts, old plans, status reports, and pilot notes.
