# HANDOFF 2026-02-19: Linked Marine Regression Fix + Realistic Asset Compatibility

## Session objective

Stabilize linked FW->Sea batch integrity (`553-556`) after regression symptoms, then enable realistic test-data generation using migrated infrastructure names and capacities.

## Outcome status

- Linked batch remediation R2: complete.
- Semantic regression gates for `553-556`: PASS.
- Transfer history for linked batches: present and non-zero where expected.
- Container overridden volume mapping (`ContainerPhysics` parameter `6` -> `volume_m3`): integrated in extraction + migration loaders.
- Realistic asset reference pack export + compatibility layer (`--reference-pack`) for schedule/event generation: complete and smoke-tested.

## Documentation status

Docs are now up to date for this session with explicit supersession notes:

- New report:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-18/marine_linked_batch_integrity_regression_fix_r2_553_556_2026-02-19.md`
- Supersession note added to:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-18/marine_linked_batch_integrity_remediation_553_556_2026-02-18.md`
- Prior pilot handoff annotated to point at this update:
  - `aquamind/docs/progress/migration/handoffs/HANDOFF_2026-02-18_MARINE_INGRESS_LINKAGE_PILOT.md`

## Key code changes in this session window

### Migration integrity / rerun safety

- `scripts/migration/tools/pilot_migrate_component.py`
  - Added stale assignment-state pruning before component rebuild to prevent old member mappings and dependent records from polluting reruns.
- `scripts/migration/tools/population_assignment_mapping.py` and dependent event migration scripts
  - Component-scoped assignment external-id usage (`component_key:population_id`) enforced across assignment lookups.

### Container volume migration fidelity

- `scripts/migration/tools/bulk_extract_fishtalk.py`
- `scripts/migration/extractors/infrastructure.py`
- `scripts/migration/loaders/infrastructure.py`
- `scripts/migration/tools/pilot_migrate_infrastructure.py`
  - Extract and load FishTalk overridden volume (`OverriddenVolumeM3`) into `infrastructure.container.volume_m3`, including updates for existing containers.

### Realistic asset compatibility layer for data generation

- Added:
  - `scripts/data_generation/export_realistic_asset_pack.py`
- Generated:
  - `scripts/data_generation/reference_pack/latest/*`
  - `scripts/data_generation/reference_pack/snapshots/2026-02-19_1430Z/*`
- Updated schedule planner:
  - `scripts/data_generation/generate_batch_schedule.py`
  - New `--reference-pack` flag.
  - Dynamic freshwater allocation from one or multiple halls in the pack.
  - Flexible sea-ring allocation for non-uniform ring counts.
  - Geography filtering to only use geographies with both FW and sea assets in pack mode.
- Updated event engine:
  - `scripts/data_generation/03_event_engine_core.py`
  - Uses schedule-provided hall/container names directly (no hardcoded Hall-A/B/C assumptions).
  - Dynamic egg/fish distribution across actual container counts.

## Current linked batch integrity snapshot (post-R2)

Refer to:

- `aquamind/docs/progress/migration/analysis_reports/2026-02-18/marine_linked_batch_integrity_regression_fix_r2_553_556_2026-02-19.md`

Quick state:

- IDs unchanged: `553`, `554`, `555`, `556`.
- Transfer workflows/actions now present for all four linked batches.
- `inactive && departure_date IS NULL`: `0` for all four.
- Regression gates: pass for all four (`linked_integrity_fix_r2` summaries).

## Generated validation artifacts (R2)

- `scripts/migration/output/input_batch_migration/Vetur_2024_1_2024/semantic_validation_Vetur_2024_1_2024.linked_integrity_fix_r2.md`
- `scripts/migration/output/input_batch_migration/Vetur_2024_1_2024/semantic_validation_Vetur_2024_1_2024.linked_integrity_fix_r2.json`
- `scripts/migration/output/input_batch_migration/Vetur_2024_2025_1_2024/semantic_validation_Vetur_2024_2025_1_2024.linked_integrity_fix_r2.md`
- `scripts/migration/output/input_batch_migration/Vetur_2024_2025_1_2024/semantic_validation_Vetur_2024_2025_1_2024.linked_integrity_fix_r2.json`
- `scripts/migration/output/input_batch_migration/Heyst_2023_1_2024/semantic_validation_Heyst_2023_1_2024.linked_integrity_fix_r2.md`
- `scripts/migration/output/input_batch_migration/Heyst_2023_1_2024/semantic_validation_Heyst_2023_1_2024.linked_integrity_fix_r2.json`
- `scripts/migration/output/input_batch_migration/Vetur_2025_1_2025/semantic_validation_Vetur_2025_1_2025.linked_integrity_fix_r2.md`
- `scripts/migration/output/input_batch_migration/Vetur_2025_1_2025/semantic_validation_Vetur_2025_1_2025.linked_integrity_fix_r2.json`

## Suggested first steps in fresh session

1. GUI verify `553-556` lifecycle/transfer/history tabs against the R2 report.
2. Continue controlled-provisional queue (`unlinked_sea`) only after operator confirmation per policy.
3. Keep using explicit FW seed linkage (`--include-fw-batch`) for linked runs.
4. For realistic test data, run schedule generation with `--reference-pack scripts/data_generation/reference_pack/latest`.

## Open risks / caveats

- `source_supported_only` stage policy means not all batches show all theoretical pre-adult stages unless source support exists.
- Canonical S->A transfer edges remain sparse in source extracts; provisional linkage should continue to be marked tooling evidence (not runtime truth).
- Realistic reference pack currently reflects migrated inventory; if infra reruns change names/capacities, regenerate pack and snapshot before further test-data generation.
