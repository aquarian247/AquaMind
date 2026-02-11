# Migration Handoff (2026-02-10 S03 Generalization + Deterministic FW->Sea Evidence)

## Scope
- Continue single-batch-first hardening with station/pre-adult focus.
- Batch replayed:
  - `Stofnfiskur Juni 24|2|2024`
- Station guard:
  - `--expected-site "S03 Norðtoftir"`
- Runtime separation preserved:
  - no FishTalk-specific runtime API/UI coupling added.

## Code changes in this pass

### Added script
- `/Users/aquarian247/Projects/AquaMind/scripts/migration/analysis/fw_to_sea_deterministic_evidence.py`

Purpose:
- Generate deterministic outside-component linkage evidence from:
  - stitched component members (`population_members.csv`),
  - SubTransfers graph (`sub_transfers.csv`),
  - explicit grouped-organisation destination context (`Site`, `SiteGroup`, `ProdStage`).

Criteria:
- `marine_linkage_evidence` is `true` only when destination `ProdStage` explicitly contains `Marine` (case-insensitive).
- No heuristic naming/date matching is used.

## Exact commands and outcomes

### 1) Clean DB
```bash
PYTHONPATH=/Users/aquarian247/Projects/AquaMind \
SKIP_CELERY_SIGNALS=1 \
python /Users/aquarian247/Projects/AquaMind/scripts/migration/clear_migration_db.py
```

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

Output highlights:
- Component key: `EDF931F2-51CC-4A10-9002-128E7BF8067C`
- Pipeline completion: `12/12`
- Success marker: `[SUCCESS] Migration completed!`

### 3) Semantic validation with regression gates
```bash
PYTHONPATH=/Users/aquarian247/Projects/AquaMind \
SKIP_CELERY_SIGNALS=1 \
python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/migration_semantic_validation_report.py \
  --component-key EDF931F2-51CC-4A10-9002-128E7BF8067C \
  --report-dir /Users/aquarian247/Projects/AquaMind/scripts/migration/output/input_batch_migration/Stofnfiskur_Juni_24_2_2024 \
  --use-csv /Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract \
  --check-regression-gates \
  --output /Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/semantic_validation_stofnfiskur_juni24_2026-02-10_station_focus.md \
  --summary-json /Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/semantic_validation_stofnfiskur_juni24_2026-02-10_station_focus.summary.json
```

Output highlights:
- Exit code `0` with report + summary written.
- Gates: `PASS`
- Non-bridge zero assignments: `0`
- Zero-count transfer actions: `0`
- Transition basis: bridge-aware `2/3`, entry-window `1/3`
- Incomplete-linkage transitions: `1` (`Fry -> Parr`)

### 4) Counts check
```bash
PYTHONPATH=/Users/aquarian247/Projects/AquaMind \
SKIP_CELERY_SIGNALS=1 \
python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/migration_counts_report.py \
  --batch-number "Stofnfiskur Juni 24"
```

Output highlights:
- assignments `145`
- transfer workflows/actions `57/57`
- feeding events `3927`
- mortality events `3734`
- treatments `64`

### 5) Deterministic FW->Sea evidence extractor run (new)
```bash
python /Users/aquarian247/Projects/AquaMind/scripts/migration/analysis/fw_to_sea_deterministic_evidence.py \
  --report-dir /Users/aquarian247/Projects/AquaMind/scripts/migration/output/input_batch_migration/Stofnfiskur_Juni_24_2_2024 \
  --component-key EDF931F2-51CC-4A10-9002-128E7BF8067C \
  --csv-dir /Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract \
  --output-md /Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/fw_to_sea_deterministic_stofnfiskur_juni24_2026-02-10.md \
  --output-json /Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/fw_to_sea_deterministic_stofnfiskur_juni24_2026-02-10.json
```

Output highlights:
- Direct external destination populations: `59`
- Reachable outside descendants: `70`
- Direct destination context: `ProdStage=Hatchery:59`, `Site=S03 Norðtoftir:59`
- `marine_linkage_evidence`: `false`

## Cross-batch status (same tooling body)

| batch | non-bridge zero assignments before/after | gate result before/after | transition basis changes (if any) |
| --- | --- | --- | --- |
| Stofnfiskur Juni 24 | n/a -> 0 | n/a -> PASS | n/a -> bridge-aware 2/3, entry-window 1/3 (incomplete-linkage 1) |
| Stofnfiskur S-21 feb24 (reference) | n/a -> 0 | n/a -> PASS | n/a -> bridge-aware 4/4, entry-window 0/4 |
| Benchmark Gen. Juni 2024 (reference) | 24 -> 0 | FAIL -> PASS | bridge-aware 0/4 -> 4/4 |

## Deterministic FW->Sea evidence comparison (new script outputs)

| batch | direct external populations | reachable outside descendants | direct destination prod stage | direct destination site | marine linkage evidence |
| --- | ---: | ---: | --- | --- | --- |
| Benchmark Gen. Juni 2024 | 100 | 227 | Hatchery:100 | S24 Strond:100 | NO |
| Stofnfiskur S-21 feb24 | 49 | 129 | Hatchery:49 | S21 Viðareiði:49 | NO |
| Stofnfiskur Juni 24 | 59 | 70 | Hatchery:59 | S03 Norðtoftir:59 | NO |

Interpretation:
- Deterministic extraction currently shows outside-component continuity but no explicit marine `ProdStage` evidence across these three station-focused FW batches.

## Artifacts written
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/semantic_validation_stofnfiskur_juni24_2026-02-10_station_focus.md`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/semantic_validation_stofnfiskur_juni24_2026-02-10_station_focus.summary.json`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/semantic_validation_stofnfiskur_juni24_generalization_2026-02-10.md`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/fw_to_sea_deterministic_stofnfiskur_juni24_2026-02-10.md`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/fw_to_sea_deterministic_stofnfiskur_juni24_2026-02-10.json`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/fw_to_sea_deterministic_stofnfiskur_s21_feb24_2026-02-10.md`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/fw_to_sea_deterministic_stofnfiskur_s21_feb24_2026-02-10.json`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/fw_to_sea_deterministic_benchmark_gen_juni_2024_2026-02-10.md`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/fw_to_sea_deterministic_benchmark_gen_juni_2024_2026-02-10.json`

## Unresolved risks
1. `Stofnfiskur Juni 24` still has one `incomplete_linkage` transition fallback (`Fry -> Parr`).
2. Deterministic FW->Sea evidence remains absent because destination context is still hatchery-classified for outside-component links in tested FW batches.

## Next steps
1. Do one focused linkage-improvement pass for `Fry -> Parr` on `Stofnfiskur Juni 24` (migration tooling only).
2. Extend deterministic extractor with optional transfer-operation context joins (still non-heuristic) to test whether additional explicit marine markers exist beyond grouped-organisation `ProdStage`.
