# Marine Guarded Dry-Run Compliance (2026-02-18)

## Scope

Validate that marine migration execution defaults align with legacy transport-workflow guardrails before running a real wave.

- Sea cohort (age-tier `linked_fw_in_scope`): `Vetur 2024|1|2024`
- Explicit linked FW inclusion: `Benchmark Gen. Septembur 2024|3|2024`

## Executed dry-run

```bash
python3 scripts/migration/tools/pilot_migrate_input_batch.py \
  --batch-key "Vetur 2024|1|2024" \
  --full-lifecycle --full-lifecycle-rebuild \
  --include-fw-batch "Benchmark Gen. Septembur 2024|3|2024" \
  --allow-station-mismatch \
  --skip-environmental --skip-feed-inventory \
  --use-csv "scripts/migration/data/extract" \
  --dry-run
```

## Dry-run result

- Extract freshness preflight: `PASS`
- Pipeline planning result: `PASS` (script list rendered, no write execution due to `--dry-run`)
- Transfer guardrail confirmation in output:
  - `Transfer migration will skip synthetic stage-transition workflows/actions (edge-backed only).`
- Station preflight mismatch was expected under full-lifecycle inclusion and allowed by explicit override:
  - `--allow-station-mismatch`

## Rule-by-rule compliance checklist

1. **Do not synthesize BatchTransferWorkflow/TransferAction just to create FW->Sea linkage**  
   - **PASS**: transfer migrator defaults to skip synthetic stage-transition generation.  
   - Evidence: `scripts/migration/tools/pilot_migrate_component_transfers.py` default `set_defaults(skip_synthetic_stage_transitions=True)`.

2. **A batch may have zero transfer workflows**  
   - **PASS**: no migration path forces synthetic transfer workflows by default; dry-run does not require them.

3. **Keep `planning.transfer_workflow` NULL unless real source event maps to real workflow**  
   - **PASS**: planning signal fallback now blocks auto-linking for legacy FishTalk-migrated workflows.  
   - Evidence: `apps/planning/signals.py` (`_is_legacy_migration_workflow`, `_resolve_completed_transfer_activity`).

4. **Do not create `StageTransitionEnvironmental` rows without real workflow id**  
   - **PASS**: no migration script path creates `StageTransitionEnvironmental` rows directly.  
   - Evidence: no `StageTransitionEnvironmental.objects.create/get_or_create/update_or_create` calls under `scripts/migration/`.

5. **Migrate canonical history via assignments/lifecycle timelines; missing transfer events are expected**  
   - **PASS**: execution path remains assignment and lifecycle-first (`pilot_migrate_component.py` + full-lifecycle members), transfer actions remain edge-backed by default.

6. **Infrastructure containers: one location context only (`hall` OR `area` OR `carrier`)**  
   - **PASS**: model-level constraint and validation enforce exactly one location context.  
   - Evidence: `apps/infrastructure/models/container.py` check constraint `container_in_hall_area_or_carrier` and `clean()` validation.

## Recommended immediate next action

Run the same command without `--dry-run` to execute the guarded marine wave with current defaults:

```bash
python3 scripts/migration/tools/pilot_migrate_input_batch.py \
  --batch-key "Vetur 2024|1|2024" \
  --full-lifecycle --full-lifecycle-rebuild \
  --include-fw-batch "Benchmark Gen. Septembur 2024|3|2024" \
  --allow-station-mismatch \
  --skip-environmental --skip-feed-inventory \
  --use-csv "scripts/migration/data/extract"
```
