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

## Replay-safe invocation patterns (2026-03-02)

Use these patterns to avoid lifecycle-coverage regressions on transfer-rich cohorts.

- Single batch (input runner):
  - `python scripts/migration/tools/pilot_migrate_input_batch.py --batch-key "<InputName>|<InputNumber>|<YearClass>" --use-csv scripts/migration/data/extract --migration-profile fw_default --skip-environmental --expand-subtransfer-descendants --transfer-edge-scope internal-only`
- Scope/chunk replay:
  - `python scripts/migration/tools/pilot_migrate_input_batch.py --scope-file <scope.csv> --use-csv scripts/migration/data/extract --migration-profile fw_default --skip-environmental --expand-subtransfer-descendants --transfer-edge-scope internal-only`

Notes:
- Scope mode now forwards descendant/edge-scope flags to child runs. Keep those flags explicit in runbooks and logs.
- For scope runs, keep one output file per chunk (`replay_scope_chunk*_*.txt`) and run post-replay verification (`migration_counts_report.py`, `migration_verification_report.py`, `migration_pilot_regression_check.py`).
