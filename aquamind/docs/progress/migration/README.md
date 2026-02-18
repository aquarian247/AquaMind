# FishTalk -> AquaMind Migration Docs (Index)

This folder is the canonical home for migration documentation.

## Low-context bootstrap (default for new agents)
Read only these 2 docs first:
1. handoffs/HANDOFF_2026-02-13_S21_ASSIGNMENT_HISTORY_CALIBRATION.md
2. DATA_MAPPING_DOCUMENT.md

Read a 3rd doc only when the task explicitly concerns FWSEA linkage or SQL tracing:
- handoffs/HANDOFF_2026-02-11_FWSEA_LINKAGE_INVESTIGATION.md

Avoid preloading `analysis_reports/*` at startup; open only the report directly tied to the discrepancy being debugged.

## Extended reference set
1. MIGRATION_CANONICAL.md - runbook + current status
2. MIGRATION_LESSONS_LEARNED.md - what works vs what does not
3. FISHTALK_SCHEMA_ANALYSIS.md - source schema corrections/notes (schema reference)
4. MIGRATION_BEST_PRACTICES.md - audit/idempotency standards
5. MIGRATION_TIMELINE_SUMMARY_2026-01-28.md - consolidated timeline

## Latest handoff
- handoffs/HANDOFF_2026-02-13_S21_ASSIGNMENT_HISTORY_CALIBRATION.md - current assignment parity calibration baseline (S21)
- handoffs/HANDOFF_2026-02-11_FWSEA_LINKAGE_INVESTIGATION.md - FWSEA linkage investigation track
- handoffs/HANDOFF_2026-02-06.md - full-action batch migration baseline
- handoffs/HANDOFF_2026-02-06_FOLLOWUP.md - FW station guard + stage sanity follow-up

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
     --expected-site \"<Station Name>\" \\
     --use-csv scripts/migration/data/extract/
4) Full action replays (per component, CSV)
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
5) Validate
   - python scripts/migration/tools/migration_semantic_validation_report.py \\
     --component-key <component_key> \\
     --report-dir <component_report_dir> \\
     --use-csv scripts/migration/data/extract \\
     --stage-entry-window-days 2
   - python scripts/migration/tools/migration_counts_report.py
   - python scripts/migration/tools/migration_verification_report.py
6) Environmental at scale (optional)
   - python scripts/migration/tools/build_environmental_sqlite.py \\
     --input-dir scripts/migration/data/extract/ \\
     --output-path scripts/migration/data/extract/environmental_readings.sqlite --replace
   - python scripts/migration/tools/pilot_migrate_environmental_all.py \\
     --use-sqlite scripts/migration/data/extract/environmental_readings.sqlite --workers 16

## Current status snapshot (2026-02-06)
- Full action migration validated for 4 batches (2 FW, 2 Sea) with semantic reports in:
  - `analysis_reports/2026-02-05/`
  - `analysis_reports/2026-02-06/` (rerun/follow-up reports for `SF NOV 23` and `Stofnfiskur S-21 nov23`)
- FW→Sea linkage is still unresolved; FW and Sea components are replayed separately.
- Weight samples use `Ext_WeightSamples_v2` only and are treated as grams (re-run required to fix old data).
- Infra names are normalized at bootstrap (strip `FT` prefix and trailing `FW`/`Sea`).
- Input-batch and component migration now support strict station guards (`--expected-site`) to prevent station drift.
- Semantic stage sanity now reports stage-entry deltas (default 2-day window) to reduce in-stage redistribution double-counting.

## Archive (historical only)
See archive/README.md. This includes handovers, session prompts, old plans, status reports, and pilot notes.
