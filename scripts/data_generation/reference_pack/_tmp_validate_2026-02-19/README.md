# Realistic Asset Reference Pack

Generated at: `2026-02-19T15:18:29` UTC

Purpose:
- Provide familiar migrated infrastructure names and related mapping hints for test data generation updates.
- Give another agent/session a single machine-readable package to consume directly.

Files:
- `infrastructure_geographies.csv`: geography-level inventory.
- `infrastructure_stations.csv`: freshwater stations with source org-unit identifiers.
- `infrastructure_halls.csv`: halls grouped under stations.
- `infrastructure_areas.csv`: sea areas with source org-unit identifiers.
- `infrastructure_containers.csv`: containers with location context (`hall` or `area` or `carrier`), `volume_m3`, `max_biomass_kg`, and source metadata.
- `hall_stage_mapping_static.csv`: static hall->stage map used by migration tooling for known sites.
- `hall_stage_mapping_observed_dominant.csv`: dominant observed stage by hall from migrated assignment history.
- `hall_stage_mapping_observed_full.csv`: full per-hall stage distribution from assignment history.
- `batch_name_reference.csv`: recent batch names and metadata suitable for realistic naming in synthetic data scripts.
- `asset_reference_summary.json`: export counts and basic diagnostics.

Suggested consumption order for script updates:
1. Use `infrastructure_containers.csv` as the primary source of familiar names and capacities.
2. Use `hall_stage_mapping_static.csv` first where available; fall back to `hall_stage_mapping_observed_dominant.csv`.
3. Use `batch_name_reference.csv` to seed realistic batch naming and geography hints.
4. Keep generated data deterministic by pinning selected IDs/names in your config templates.

Notes:
- Some names include Faroese characters; files are UTF-8 encoded.
- `max_biomass_kg` can be zero for migrated containers when source data did not provide a value.
