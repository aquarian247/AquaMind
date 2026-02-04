# Migration Tools (Active vs Deprecated)

## Active tools (current pipeline)
- bulk_extract_fishtalk.py - bulk CSV extract from FishTalk
- targeted_action_extract.py - scoped Action/ActionMetaData extract by OperationID or date window
- input_based_stitching_report.py - input-based batch discovery
- pilot_migrate_input_batch.py - end-to-end input-batch migration
- pilot_migrate_component.py - core batch + infrastructure
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
