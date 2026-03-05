# FishTalk -> AquaMind Migration Docs (Index)

This folder is the canonical home for migration documentation.

## Low-context bootstrap (default for new agents)
Read only these 2 docs first:
1. handoffs/HANDOFF_2026-03-02_FW_MAPPED_SCOPE_REGRESSION_STABILIZATION_RESULTS.md
2. DATA_MAPPING_DOCUMENT.md

Read a 3rd doc only when task scope requires it:
- Scope replay/runbook questions: `MIGRATION_CANONICAL.md`
- FWSEA linkage/trace tasks: `handoffs/HANDOFF_2026-02-24_FWSEA_DETERMINISTIC_SALES_LINKAGE_SCORING_AND_B_CLASS_FT_NOTES.md`

Avoid preloading `analysis_reports/*` at startup; open only the report directly tied to the discrepancy being debugged.

## Extended reference set
1. MIGRATION_CANONICAL.md - runbook + current status
2. MIGRATION_LESSONS_LEARNED.md - what works vs what does not
3. FISHTALK_SCHEMA_ANALYSIS.md - source schema corrections/notes (schema reference)
4. MIGRATION_BEST_PRACTICES.md - audit/idempotency standards
5. MIGRATION_TIMELINE_SUMMARY_2026-01-28.md - consolidated timeline

## Latest handoff
- handoffs/HANDOFF_2026-03-05_FW_ENVIRONMENTAL_STABILIZATION_AND_FWSEA_READY_CHECK.md - FW environmental stabilization, zero remaining scoped parameter mismatches, FWSEA readiness split
- handoffs/HANDOFF_2026-03-04_SCOPE60_CORE_ENV_EXECUTION.md - scope-60 core/health/environmental residual execution completion
- handoffs/HANDOFF_2026-03-04_SCOPE60_VERIFICATION_INVENTORY_FEED.md - scope-60 verification and inventory/feed readout
- handoffs/HANDOFF_2026-03-03_SCOPE60_FEED_INFRA_LINEAGE_EXECUTION.md - scope-60 lineage-first feed/infra execution
- handoffs/HANDOFF_2026-03-03_SCOPE21_FEED_INFRA_RECOVERY.md - scope-21 feed/infra recovery and unresolved-class interpretation
- handoffs/HANDOFF_2026-03-03_S21_MICRO_DISCREPANCY_AUDIT_1120_1125_1126.md - S21 micro discrepancy audit; expected artifacts vs defects
- handoffs/HANDOFF_2026-03-02_FW_MAPPED_SCOPE_REGRESSION_STABILIZATION_RESULTS.md - mapped scope regression stabilization results, MIX interpretation, non-MIX lifecycle deep-dive, ranked fix plan
- handoffs/HANDOFF_2026-03-02_FW_MAPPED_SCOPE_REGRESSION_TRIAGE_AND_NEXT_AGENT_PROMPT.md - regression triage prompt and takeover objectives
- handoffs/HANDOFF_2026-02-24_FWSEA_DETERMINISTIC_SALES_LINKAGE_SCORING_AND_B_CLASS_FT_NOTES.md - deterministic FWSEA sales-link scoring module + FT B-class notes + A37 station resolution
- handoffs/HANDOFF_2026-02-24_FW_EXACT_START_TIEBREAK_WAVE_AND_POSTWAVE_BOARD.md - exact-start duplicate-timestamp tie-break wave + full FW post-wave board
- handoffs/HANDOFF_2026-02-23_FW_EXPECTED_NONZERO_REPLAY_WAVE_AND_POSTWAVE_SCOPE_BOARD.md - FW class-A replay clearance + full-scope post-wave residual board
- handoffs/HANDOFF_2026-02-23_S16_S21_S24_POLICY_WAVE_AND_MAPPING_LOCK.md - S16/S21/S24 controlled policy wave + mapping lock update
- handoffs/HANDOFF_2026-02-20_FW_FALSE_CLOSURE_WAVE_REPLAY.md - FW false-closure wave replay (42->5), hard-data calibration, residual taxonomy
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

## Latest evidence package
- `scripts/migration/output/fwsea_readonly_candidate_package_20260305_103924/` - latest FWSEA evidence package (candidate report, summary JSON, guarded continuation artifacts, next-queue state)

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
     --use-csv scripts/migration/data/extract/ \\
     --expand-subtransfer-descendants \\
     --transfer-edge-scope internal-only
3b) Migrate a scope/chunk (transfer-rich cohorts)
   - PYTHONPATH=/path/to/AquaMind SKIP_CELERY_SIGNALS=1 \\
     python scripts/migration/tools/pilot_migrate_input_batch.py \\
     --scope-file scripts/migration/output/input_stitching/<scope_chunk>.csv \\
     --use-csv scripts/migration/data/extract/ \\
     --migration-profile fw_default \\
     --skip-environmental \\
     --expand-subtransfer-descendants \\
     --transfer-edge-scope internal-only
3c) Guarded FW->Sea continuation (selected provisional candidates only)
   - PYTHONPATH=/path/to/AquaMind SKIP_CELERY_SIGNALS=1 \\
     python scripts/migration/tools/pilot_migrate_input_batch.py \\
     --batch-key "<SeaInputName>|<InputNumber>|<YearClass>" \\
     --use-csv scripts/migration/data/extract/ \\
     --migration-profile fw_default \\
     --full-lifecycle \\
     --include-fw-batch "<FWInputName>|<InputNumber>|<YearClass>" \\
     --batch-number "<Existing FW batch number>" \\
     --sea-anchor-population-id "<SeaPopulationID>" \\
     --transfer-edge-scope internal-only
   - Linked continuation is now blocked by default unless anchor scope is provided. Use full sea-component ingestion only with explicit operator override.
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

## Current status snapshot (2026-03-05)
- FW stabilization is materially complete:
  - mapped FW replay is stable with descendant expansion + `internal-only` transfer edges,
  - scope-60 feed/infra lineage is complete,
  - scope-60 core/health/environmental residuals are complete,
  - scoped FW environmental mapping now has `0` remaining parameter mismatches.
- Stage/lifecycle integrity is materially improved:
  - completed scoped FW cohorts are mostly realistic after replay,
  - S21 micro discrepancies were classified as expected representation artifacts, not conservation defects,
  - lifecycle progression reporting still needs interpretation care (`basis=stage_entry` is entry semantics, not peak concurrent stock).
- Feed/inventory is no longer "feeding-only":
  - lineage-scoped feed purchase/stock import is active,
  - scope-60 verification shows 1:1 purchase->stock cardinality and zero duplicate source identifiers for feed scope models.
- FW->Sea status is no longer simply "unresolved":
  - direct canonical FW->Sea population linkage for active cohorts remains sparse,
  - latest work treats sea cohorts as new marine-side inputs and matches them by endpoint evidence (FW terminal depletion/sales vs sea input/first-fill),
  - guarded anchor-scoped continuation is now the active experimental path; full sea-component continuation is blocked by default.
- Broad FW->Sea rollout is still blocked on:
  - lifecycle-plausibility policy for provisional links,
  - reconciliation of early experiment-state drift,
  - manual/shared-anchor/ring-text queue closure.
- Weight samples use `Ext_WeightSamples_v2` only and are treated as grams.
- Infra names remain normalized at bootstrap (strip `FT` prefix and trailing `FW`/`Sea`).
- Input-batch and component migration support strict station guards (`--expected-site`) to prevent station drift.

## Archive (historical only)
See archive/README.md. This includes handovers, session prompts, old plans, status reports, and pilot notes.
