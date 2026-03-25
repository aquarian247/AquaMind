# Migration Tools (Active vs Deprecated)

## Active tools (current pipeline)
- bulk_extract_fishtalk.py - bulk CSV extract from FishTalk
- targeted_action_extract.py - scoped Action/ActionMetaData extract by OperationID or date window
- input_based_stitching_report.py - input-based batch discovery
- pilot_migrate_input_batch.py - end-to-end input-batch migration
- pilot_migrate_component.py - core batch + infrastructure
- extract_freshness_guard.py - detect stale/cutoff CSV extracts before migration
- migration_profiles.py - cohort-profile presets for migration behavior
- migration_profile_cohort_classifier.py - group semantic summaries into profile recommendations
- pilot_migrate_component_transfers.py - transfer workflows
- build_fw_u30_broadening_queue.py - derive cutoff-correct FW-only <30m two-geography scope classification + transfer queue
- rerun_component_transfer_queue.py - execute transfer-only component queue with per-batch logs and summary
- hall_stage_rules.py - shared qualified hall-stage canonicalization rules used by source-side report builders
- audit_priority_hall_stage_reports.py - detect priority-hall stage drift in generated report dirs
- backfill_priority_hall_stage_queue.py - backfill priority-hall stage corrections into report dirs and mapped AquaMind batches
- audit_priority_hall_assignment_stages.py - verify live mapped assignment lifecycle stages against priority-hall expectations
- pilot_migrate_component_feeding.py - feeding events
- pilot_migrate_component_mortality.py - mortality events
- pilot_migrate_component_treatments.py - treatments
- pilot_migrate_component_lice.py - lice counts
- pilot_migrate_component_health_journal.py - health journal (UserSample)
- pilot_migrate_component_environmental.py - environmental readings
- pilot_migrate_component_feed_inventory.py - feed inventory (component scope)
- pilot_migrate_component_growth_samples.py - growth samples
- pilot_migrate_health_master_data.py - health lookup/master data
- pilot_migrate_infrastructure.py - optional infra pre-load
- pilot_migrate_environmental_all.py - environmental at scale
- build_environmental_sqlite.py - environmental SQLite index
- migration_counts_report.py - count verification
- migration_verification_report.py - reconciliation report
- fwsea_deterministic_linkage_report.py - deterministic FW->Sea operation-level evidence report (InternalDelivery + ActionMetaData(184/220) + PopulationLink/SubTransfers diagnostics)
- fwsea_sales_linkage_scoring_extract.py - deterministic FW->Sea sales-action scoring extract (customer/ring/trip + exact-time status sales count/biomass)
- fwsea_sales_directional_parity_extract.py - directional FW->Sea parity extract (container-out vs paired ring/input-in count deltas from InternalDelivery operation pairs)
- fwsea_endpoint_pairing_gate.py - endpoint uniqueness/stability acceptance gate for FWSEA policy-readiness (tooling-only)
- fwsea_endpoint_gate_matrix.py - run endpoint gate across cohort semantic summaries and publish pass/fail matrix
- fwsea_trace_target_pack.py - build deterministic SQL trace target packs from matrix blocker classifications (operation IDs + signatures)
- fwsea_xe_trace_capture.py - arm/disarm/analyze SQL Server Extended Events capture for FWSEA trace packs
- cohort_subtransfer_transition_report.py - derive deterministic SB->DA stage-transition topology for a cohort from ExtInputs + SubTransfers lineage
- dump_schema.py - schema snapshot utility
- fix_system_admin_rbac.py - RBAC fix
- pilot_migrate_feed_inventory.py - optional global feed inventory pass
- pilot_migrate_scenario_models.py - TGC/FCR/temperature models
- pilot_migrate_post_batch_processing.py - post-migration processing

## Deprecated tools (moved)
Deprecated tools live under scripts/migration/legacy/tools/:
- project_based_stitching_report.py
- population_stitching_report.py
- subtransfer_chain_stitching.py
- pilot_migrate_project_batch.py
- pilot_migrate_batch_parallel.py
- pilot_migrate_batch_expansion.py
- pilot_migrate_environmental_bulk.py

## Analysis/experimental (moved out of tools)
- scripts/migration/analysis/analyze_batch_cohorts.py
- scripts/migration/analysis/analyze_yearclass_from_names.py
- scripts/migration/analysis/validate_yearclass_approach.py
- scripts/migration/analysis/input_full_lifecycle_stitching.py

## Replay-safe invocation patterns (2026-03-25)

Use these patterns to avoid lifecycle-coverage regressions on transfer-rich cohorts.

- Single batch (input runner):
  - `python scripts/migration/tools/pilot_migrate_input_batch.py --batch-key "<InputName>|<InputNumber>|<YearClass>" --use-csv scripts/migration/data/extract --migration-profile fw_default --skip-environmental --expand-subtransfer-descendants --transfer-edge-scope source-in-scope`
- Scope/chunk replay:
  - `python scripts/migration/tools/pilot_migrate_input_batch.py --scope-file <scope.csv> --use-csv scripts/migration/data/extract --migration-profile fw_default --skip-environmental --expand-subtransfer-descendants --transfer-edge-scope source-in-scope`
- Guarded FW->Sea continuation (selected provisional rows only):
  - `python scripts/migration/tools/pilot_migrate_input_batch.py --batch-key "<SeaInputName>|<InputNumber>|<YearClass>" --use-csv scripts/migration/data/extract --migration-profile fw_default --full-lifecycle --include-fw-batch "<FWInputName>|<InputNumber>|<YearClass>" --batch-number "<Existing FW batch number>" --sea-anchor-population-id "<SeaPopulationID>" --expand-subtransfer-descendants --transfer-edge-scope source-in-scope`

Notes:
- Scope mode now forwards descendant/edge-scope flags to child runs. Keep those flags explicit in runbooks and logs.
- SubTransfers edge handling is root-source first. The transfer migrator expands `SourcePopBefore -> SourcePopAfter -> DestPopAfter` chains into root-source conservation edges before any scope filter is applied. This is required to preserve split legs like `806 -> 903/904`.
- Same-container same-stage residual tails that exist only to be fully culled are now folded back into the predecessor assignment during component migration. Keep culling on the predecessor assignment; do not preserve a separate AquaMind assignment row just because FishTalk emitted a short-lived `SourcePopAfter` tail.
- For qualified priority-hall sites (`S24`, `S03`, `S08`, `S16`, `S21`, `FW22 Applecross`), manual swimlane review is not a sufficient stage-integrity check. Use the deterministic audit/backfill loop instead:
  - `python scripts/migration/tools/audit_priority_hall_stage_reports.py --csv-dir scripts/migration/data/extract --output-prefix scripts/migration/output/<prefix>`
  - `python scripts/migration/tools/backfill_priority_hall_stage_queue.py --queue-csv scripts/migration/output/<priority_hall_backfill_queue>.csv --output-dir scripts/migration/output/<apply_dir>`
  - `python scripts/migration/tools/audit_priority_hall_assignment_stages.py --output-path scripts/migration/output/<final_assignment_audit>.json`
- Linked FW->Sea continuation now blocks full sea-component ingestion by default. Provide `--sea-anchor-population-id` and optional `--sea-block-population-id`; use `--allow-full-sea-component-for-continuation` only for explicitly approved non-provisional cases.
- For scope runs, keep one output file per chunk (`replay_scope_chunk*_*.txt`) and run post-replay verification (`migration_counts_report.py`, `migration_verification_report.py`, `migration_pilot_regression_check.py`).
- To classify remaining FW cleanup work, use `python scripts/migration/tools/build_fw_hardening_queue.py --output-json <path> --output-md <path>`. This computes the transfer-rerun queue from the current patched SubTransfers logic instead of relying on handoff prose.
