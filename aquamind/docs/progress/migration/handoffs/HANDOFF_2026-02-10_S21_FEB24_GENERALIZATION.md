# Migration Handoff (2026-02-10 S21 Feb24 Generalization)

## Scope
- Single-batch generalization check on recent FW station/pre-adult batch:
  - `Stofnfiskur S-21 feb24|1|2024`
- Station guard enforced:
  - `--expected-site "S21 Viðareiði"`
- Runtime-separation rule preserved:
  - no runtime API/UI FishTalk coupling added,
  - no migration logic moved into runtime.

## What changed in code
- No migration-tooling code changes in this pass.
- This pass is a clean replay + validation evidence step on current tooling state.

## Exact commands and outputs

### 1) Wipe migration DB
```bash
PYTHONPATH=/Users/aquarian247/Projects/AquaMind \
SKIP_CELERY_SIGNALS=1 \
python /Users/aquarian247/Projects/AquaMind/scripts/migration/clear_migration_db.py
```

Output (key):
- Database cleared (`Truncated ...` for migration-related tables).

### 2) Run station-guarded migration
```bash
PYTHONPATH=/Users/aquarian247/Projects/AquaMind \
SKIP_CELERY_SIGNALS=1 \
python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/pilot_migrate_input_batch.py \
  --batch-key "Stofnfiskur S-21 feb24|1|2024" \
  --expected-site "S21 Viðareiði" \
  --use-csv /Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract \
  --skip-environmental
```

Output (key):
- Input populations: `253`
- Component key: `BC782146-C921-4AD1-8021-0E1ED2228D7C`
- Transfer migration mode: synthetic stage-transition workflows/actions skipped.
- Pipeline completion: `Scripts completed: 12/12`
- Success marker: `[SUCCESS] Migration completed!`

### 3) Semantic validation with regression gates
```bash
PYTHONPATH=/Users/aquarian247/Projects/AquaMind \
SKIP_CELERY_SIGNALS=1 \
python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/migration_semantic_validation_report.py \
  --component-key BC782146-C921-4AD1-8021-0E1ED2228D7C \
  --report-dir /Users/aquarian247/Projects/AquaMind/scripts/migration/output/input_batch_migration/Stofnfiskur_S-21_feb24_1_2024 \
  --use-csv /Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract \
  --check-regression-gates \
  --output /Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/semantic_validation_stofnfiskur_s21_feb24_2026-02-10_station_focus.md \
  --summary-json /Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/semantic_validation_stofnfiskur_s21_feb24_2026-02-10_station_focus.summary.json
```

Output (key):
- Report + summary JSON written.
- Exit code: `0`

### 4) Counts check
```bash
PYTHONPATH=/Users/aquarian247/Projects/AquaMind \
SKIP_CELERY_SIGNALS=1 \
python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/migration_counts_report.py \
  --batch-number "Stofnfiskur S-21 feb24"
```

Output (key):
- `batch_batchcontainerassignment`: `253`
- `batch_batchtransferworkflow`: `107`
- `batch_transferaction`: `107`
- `batch_mortalityevent`: `3258`
- `inventory_feedingevent`: `3418`
- `health_treatment`: `26`

## Verified semantics
- Regression gates: `PASS`
- Non-bridge zero assignments: `0` (threshold `2`)
- Transfer actions with `transferred_count <= 0`: `0`
- Positive transition delta gate alerts: `0`
- Transition basis: bridge-aware `4/4`, entry-window `0/4`
- Lineage-graph fallback used on bridge-aware transitions: `2`
- Incomplete-linkage entry-window transitions: `0`

## Deterministic FW->Sea evidence status
From semantic report external-linkage evidence:
- `marine_linkage_evidence`: `false`
- Direct external destination populations: `49` (all `S21 Viðareiði`, `Hatchery`)
- Reachable outside descendants: `129` (all `S21 Viðareiði`, `Hatchery`)
- Active migrated containers checked: `11`
  - latest holder in selected component: `0`
  - latest holder outside selected component: `11`

Interpretation:
- Deterministic SubTransfer evidence shows outside-component continuity, but no marine classification evidence for this stitched component.

## Heuristic-only FW->Sea signal (non-gating)
From existing heuristic output:
- File: `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-03/fw_to_sea_heuristic_candidates_postsmolt_2026-02-03.csv`
- Rows where `FWPopulationName=Stofnfiskur S-21 feb24`: `288`
- Distinct `SeaPopulationName`: `19`
- Sea start range: `2025-03-11` to `2025-10-08`

Interpretation:
- Indicates plausible FW->Sea candidates, but remains heuristic and not deterministic gate evidence.

## Compact findings table

| batch | non-bridge zero assignments before/after | gate result before/after | transition basis changes (if any) |
| --- | --- | --- | --- |
| Stofnfiskur S-21 feb24 | n/a -> 0 | n/a -> PASS | n/a -> bridge-aware 4/4, entry-window 0/4 |
| Benchmark Gen. Juni 2024 (reference) | 24 -> 0 | FAIL -> PASS | bridge-aware 0/4 -> 4/4 (lineage fallback depth 14) |
| Stofnfiskur S-21 nov23 (reference) | n/a -> 2 | n/a -> PASS | bridge-aware 2/4, entry-window 2/4 (2 incomplete-linkage) |

Note:
- For `Stofnfiskur S-21 feb24`, there is no earlier station-focus baseline report in this pass to claim a measured before value.

## Unresolved risks
1. Deterministic FW->Sea linkage remains unresolved; current evidence is either station-internal deterministic links or heuristic candidates.
2. Lifecycle stage full-sum inflation (Parr/Smolt/Post-Smolt) still reflects cumulative assignment history and can be misread as active population.

## Next steps
1. Run one more recent FW station/pre-adult batch with the same command body and compare the same gate/transition basis metrics.
2. Add a deterministic, migration-tooling-only FW->Sea evidence extractor (no runtime coupling) based on transfer graph + explicit destination context fields, then re-evaluate marine linkage coverage.
