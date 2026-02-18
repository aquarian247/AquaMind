# Benchmark Gen. Desembur 2024: assignment-history orphan-zero suppression

> Superseded by conservative refinement: `benchmark_gen_desembur_assignment_history_postsmolt_preserve_2026-02-12.md`

Date: 2026-02-12  
Component: `1636C683-E8F2-476D-BC21-0170CA7DCEE8`  
Batch name: `Benchmark Gen. Desembur 2024`

## Question

Why does the batch show `Smolt` while assignment history shows many newer `Departed` rows (especially zero-count rows in Nov-Jan), and can migration logic reduce this noise without changing runtime behavior?

## Deterministic findings

1. Baseline migrated batch had many zero inactive rows:
   - `assignment_count=221`
   - `active_count=12`
   - `zero_count_inactive=74`
2. Zero-row family split for this batch:
   - `37` rows had blank source stage tokens (`first_stage=''` and `last_stage=''`)
   - Those same `37` rows had **no SubTransfers edge touch** for source/dest-before/after IDs
3. These `37` rows are migration-side orphan bridge-like artifacts that inflate assignment history but do not carry count evidence.

## Migration logic change (tooling-only)

Patched `scripts/migration/tools/pilot_migrate_component.py` to suppress assignment writes only when all conditions are true:

- assignment would be inactive
- `population_count <= 0`
- source stage tokens are blank
- population is not touched by any component SubTransfers edge
- no known removals
- no status-count evidence

No runtime API/UI code was changed.

## Validation run (canonical path)

Commands:

```bash
PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 \
python /Users/aquarian247/Projects/AquaMind/scripts/migration/clear_migration_db.py

PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 \
python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/pilot_migrate_component.py \
  --component-key "1636C683-E8F2-476D-BC21-0170CA7DCEE8" \
  --report-dir "/Users/aquarian247/Projects/AquaMind/scripts/migration/output/input_batch_migration/Benchmark_Gen._Desembur_2024_4_2024" \
  --use-csv "/Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract" \
  --batch-number "Benchmark Gen. Desembur 2024" \
  --expected-site "S24 Strond"

PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 \
python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/pilot_migrate_component_transfers.py \
  --component-key "1636C683-E8F2-476D-BC21-0170CA7DCEE8" \
  --report-dir "/Users/aquarian247/Projects/AquaMind/scripts/migration/output/input_batch_migration/Benchmark_Gen._Desembur_2024_4_2024" \
  --use-csv "/Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract" \
  --use-subtransfers --skip-synthetic-stage-transitions

PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 \
python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/migration_semantic_validation_report.py \
  --component-key "1636C683-E8F2-476D-BC21-0170CA7DCEE8" \
  --report-dir "/Users/aquarian247/Projects/AquaMind/scripts/migration/output/input_batch_migration/Benchmark_Gen._Desembur_2024_4_2024" \
  --use-csv "/Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract" \
  --output "/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-12/semantic_validation_benchmark_gen_desembur_2024_2026-02-12_orphan_zero_suppression_subtransfers.md" \
  --summary-json "/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-12/semantic_validation_benchmark_gen_desembur_2024_2026-02-12_orphan_zero_suppression_subtransfers.summary.json"
```

Observed:

- Component migration printed:
  - `Suppressed orphan zero-count assignment rows ...: 37`
- Transfer replay (canonical SubTransfers path):
  - `actions created=36, skipped=0`
- Post-run assignment materialization:
  - `assignment_count: 221 -> 184`
  - `zero_count_inactive: 74 -> 37`
  - late Nov-Jan zero departed tails removed from assignment history

Semantic summary comparison (`2026-02-11` baseline vs patched canonical rerun):

| Metric | Baseline | Patched |
|---|---:|---:|
| transfer_actions.total_count | 36 | 36 |
| transfer_actions.zero_count | 0 | 0 |
| stage_sanity.zero_assignment_total_count | 77 | 37 |
| stage_sanity.zero_assignment_bridge_count | 37 | 37 |
| stage_sanity.zero_assignment_non_bridge_count | 0 | 0 |
| regression_gates.passed | true | true |
| stage_sanity.transition_count | 4 | 4 |
| transition_entry_window_reason_counts | `{bridge_aware:3, incomplete_linkage:1}` | unchanged |

## Decision

- **GO**: keep orphan-zero suppression in migration tooling.
- **NO-GO**: no runtime/UI changes.
- **NO-GO**: no FW/Sea policy change from this fix; this is assignment-history noise reduction only.

