# Benchmark Gen. Desembur 2024: conservative orphan-zero suppression (post-smolt preserved)

Date: 2026-02-12  
Component: `1636C683-E8F2-476D-BC21-0170CA7DCEE8`  
Batch: `Benchmark Gen. Desembur 2024`

## Context

After initial orphan-zero suppression, assignment history noise dropped strongly, but post-smolt hall traversal became too sparse in UI review (mostly `H` hall visible). For S24, qualified hall-stage mapping includes `G/H/I/J -> Post-Smolt`, so preserving messy post-smolt hall transitions is preferable to aggressive pruning.

## Tooling change

File changed: `scripts/migration/tools/pilot_migrate_component.py`

Orphan-zero suppression rule was narrowed to **preserve post-smolt rows**:

- keep suppression for orphan zero rows with no stage tokens, no SubTransfers edge touch, no count evidence
- **but do not suppress when resolved lifecycle stage is `Post-Smolt`**

Effective condition added:

```python
and stage.name != "Post-Smolt"
```

This remains migration-tooling-only; runtime API/UI remains unchanged.

## Canonical rerun commands

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
  --output "/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-12/semantic_validation_benchmark_gen_desembur_2024_2026-02-12_orphan_zero_conservative_postsmolt.md" \
  --summary-json "/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-12/semantic_validation_benchmark_gen_desembur_2024_2026-02-12_orphan_zero_conservative_postsmolt.summary.json"
```

## Results

- Migration log: `Suppressed orphan zero-count assignment rows ...: 7`
- Assignment materialization:
  - `assignment_count = 214`
  - `active_count = 12`
  - `zero_inactive = 67`
  - `Post-Smolt assignment rows = 39` (restored from over-pruned state)
- Suppressed population names now limited to:
  - `F04` (3 rows), `F02` (1 row), `E02` (3 rows)

Transfer/semantic gates vs 2026-02-11 baseline:

| Metric | Baseline | Conservative |
|---|---:|---:|
| transfer_actions.total_count | 36 | 36 |
| transfer_actions.zero_count | 0 | 0 |
| stage_sanity.zero_assignment_total_count | 77 | 67 |
| stage_sanity.zero_assignment_non_bridge_count | 0 | 0 |
| regression_gates.passed | true | true |
| transition_entry_window_reason_counts | `{bridge_aware:3, incomplete_linkage:1}` | unchanged |

## Interpretation

- Conservative suppression avoids erasing post-smolt hall traversal signal (`G/H/I/J`) in messy real-world movement chains.
- Deterministic migration gates and transfer integrity remain stable.
- Remaining zero post-smolt rows are still visible and can be used for manual/diagnostic interpretation without promoting FW->Sea policy.

## Decision

- **GO** for conservative orphan-zero suppression with post-smolt preservation.
- **NO-GO** for runtime changes.
- **NO-GO** for any FW->Sea policy promotion based on this batch alone.

