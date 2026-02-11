# Migration Handoff (2026-02-10 S03 Linkage Refinement v3)

## Scope
- Focus batch: `Stofnfiskur Juni 24|2|2024`
- Station guard: `S03 Norðtoftir`
- Component key: `EDF931F2-51CC-4A10-9002-128E7BF8067C`
- Constraint preserved: migration-tooling only (no runtime FishTalk coupling).

## Code changes applied
1. `scripts/migration/tools/pilot_migrate_component.py`
- Added S03 hall mapping: `KLEKING -> Egg&Alevin` in `S03_HALL_STAGE_MAP`.

2. `scripts/migration/tools/migration_semantic_validation_report.py`
- Kept bridge-aware transitions by default when linkage is complete.
- Added narrow downgrade rule: if bridge-derived delta is positive, mixed-batch rows are absent, and entry populations show outside-component incoming sources, mark transition as `entry_window` with `entry_window_reason=incomplete_linkage`.
- This prevents false-positive bridge alerts without demoting unrelated transitions.

## Exact rerun commands (fresh evidence)

### 1) Clean DB
```bash
PYTHONPATH=/Users/aquarian247/Projects/AquaMind \
SKIP_CELERY_SIGNALS=1 \
python /Users/aquarian247/Projects/AquaMind/scripts/migration/clear_migration_db.py
```
Output marker: `✅ Database cleared!`

### 2) Guarded migration replay
```bash
PYTHONPATH=/Users/aquarian247/Projects/AquaMind \
SKIP_CELERY_SIGNALS=1 \
python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/pilot_migrate_input_batch.py \
  --batch-key "Stofnfiskur Juni 24|2|2024" \
  --expected-site "S03 Norðtoftir" \
  --use-csv /Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract \
  --skip-environmental
```
Output markers:
- `Scripts completed: 12/12`
- `[SUCCESS] Migration completed!`

### 3) Semantic validation (regression gates)
```bash
PYTHONPATH=/Users/aquarian247/Projects/AquaMind \
SKIP_CELERY_SIGNALS=1 \
python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/migration_semantic_validation_report.py \
  --component-key EDF931F2-51CC-4A10-9002-128E7BF8067C \
  --report-dir /Users/aquarian247/Projects/AquaMind/scripts/migration/output/input_batch_migration/Stofnfiskur_Juni_24_2_2024 \
  --use-csv /Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract \
  --check-regression-gates \
  --output /Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/semantic_validation_stofnfiskur_juni24_2026-02-10_station_focus_kleking_fix_v3.md \
  --summary-json /Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/semantic_validation_stofnfiskur_juni24_2026-02-10_station_focus_kleking_fix_v3.summary.json
```
Output markers:
- `Wrote report ...station_focus_kleking_fix_v3.md`
- `Wrote summary JSON ...station_focus_kleking_fix_v3.summary.json`

### 4) Counts report
```bash
PYTHONPATH=/Users/aquarian247/Projects/AquaMind \
SKIP_CELERY_SIGNALS=1 \
python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/migration_counts_report.py \
  --batch-number "Stofnfiskur Juni 24"
```
Output highlights:
- assignments `145`
- transfer workflows/actions `57/57`
- feeding `3927`
- mortality events `3734`
- treatments `64`

## Result summary
- Gates: `PASS`
- Non-bridge zero assignments: `0`
- Zero-count transfer actions: `0`
- Transition basis: `3/4` bridge-aware, `1/4` entry-window
- Incomplete-linkage transitions: `1` (`Fry -> Parr`)
- Positive-delta gate alerts: `0` (excluded incomplete-linkage rows: `1`)

## Compact findings table

| batch | non-bridge zero assignments before/after | gate result before/after | transition basis changes |
| --- | --- | --- | --- |
| Stofnfiskur Juni 24 (S03 station-focus, v2 -> v3) | `0 -> 0` | `PASS -> PASS` | `bridge-aware 0/4, entry-window 4/4` -> `bridge-aware 3/4, entry-window 1/4` (`incomplete_linkage 4 -> 1`) |

## Outputs produced
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/semantic_validation_stofnfiskur_juni24_2026-02-10_station_focus_kleking_fix_v3.md`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/semantic_validation_stofnfiskur_juni24_2026-02-10_station_focus_kleking_fix_v3.summary.json`

## Unresolved risks
1. `Fry -> Parr` remains `incomplete_linkage` with positive entry-window delta; this indicates unresolved outside-component mixing for that transition.
2. FW->Sea linkage remains unproven by deterministic extract evidence (`marine_linkage_evidence=false` in current extractor outputs).
3. Lifecycle/progression chart inflation risk is still likely in API/frontend aggregation layers, separate from migration replay counts.

## Recommended next steps
1. Run the same S03 linkage logic on one additional FW station batch within 30 months and compare transition-basis distribution (`bridge-aware` vs `incomplete_linkage`) before broader reruns.
2. Add a deterministic semantic diagnostic that prints exact external source population IDs for each downgraded transition to speed root-cause closure on remaining `Fry -> Parr` gaps.
3. Keep FW and Sea unlinked in migration; use deterministic FW->Sea evidence output only for operator-assisted post-migration reconciliation.
