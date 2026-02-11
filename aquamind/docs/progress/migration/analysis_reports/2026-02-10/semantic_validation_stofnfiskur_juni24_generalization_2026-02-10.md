# Semantic Validation Generalization Note (2026-02-10, S03 Norðtoftir)

## Scope
- Batch key: `Stofnfiskur Juni 24|2|2024`
- Station guard: `S03 Norðtoftir`
- Objective: second recent FW station/pre-adult replay using the same migration command body and validation gates.

## Replay commands
```bash
PYTHONPATH=/Users/aquarian247/Projects/AquaMind \
SKIP_CELERY_SIGNALS=1 \
python /Users/aquarian247/Projects/AquaMind/scripts/migration/clear_migration_db.py
```

```bash
PYTHONPATH=/Users/aquarian247/Projects/AquaMind \
SKIP_CELERY_SIGNALS=1 \
python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/pilot_migrate_input_batch.py \
  --batch-key "Stofnfiskur Juni 24|2|2024" \
  --expected-site "S03 Norðtoftir" \
  --use-csv /Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract \
  --skip-environmental
```

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

```bash
PYTHONPATH=/Users/aquarian247/Projects/AquaMind \
SKIP_CELERY_SIGNALS=1 \
python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/migration_counts_report.py \
  --batch-number "Stofnfiskur Juni 24"
```

## Results (S03 run)
- Migration pipeline: `12/12` scripts completed.
- Regression gates: `PASS`.
- Non-bridge zero assignments: `0` (threshold `2`).
- Transfer actions with `transferred_count <= 0`: `0`.
- Transition basis: bridge-aware `2/3`, entry-window `1/3`.
- Incomplete-linkage transitions: `1` (`Fry -> Parr` entry-window fallback).
- Bridge-aware transitions using lineage fallback: `2`.

## Deterministic FW->Sea evidence run

Script:
- `/Users/aquarian247/Projects/AquaMind/scripts/migration/analysis/fw_to_sea_deterministic_evidence.py`

Command:
```bash
python /Users/aquarian247/Projects/AquaMind/scripts/migration/analysis/fw_to_sea_deterministic_evidence.py \
  --report-dir /Users/aquarian247/Projects/AquaMind/scripts/migration/output/input_batch_migration/Stofnfiskur_Juni_24_2_2024 \
  --component-key EDF931F2-51CC-4A10-9002-128E7BF8067C \
  --csv-dir /Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract \
  --output-md /Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/fw_to_sea_deterministic_stofnfiskur_juni24_2026-02-10.md \
  --output-json /Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/fw_to_sea_deterministic_stofnfiskur_juni24_2026-02-10.json
```

Deterministic evidence result:
- Direct external destination populations: `59`
- Reachable outside descendants: `70`
- Destination context (direct): `ProdStage=Hatchery:59`, `Site=S03 Norðtoftir:59`
- `marine_linkage_evidence`: `false` (no explicit destination `ProdStage` containing `Marine`)

## Cross-batch comparison (same command body / same validator gates)

| Batch | Gate | Non-bridge zero assignments | Transition basis (bridge-aware / entry-window) | Incomplete-linkage transitions | Deterministic marine evidence |
| --- | --- | ---: | --- | ---: | --- |
| Benchmark Gen. Juni 2024 | PASS | 0 | 4 / 0 | 0 | NO |
| Stofnfiskur S-21 feb24 | PASS | 0 | 4 / 0 | 0 | NO |
| Stofnfiskur Juni 24 | PASS | 0 | 2 / 1 | 1 | NO |

Interpretation:
- The same migration tooling and gate rules continue to hold on a second recent FW station/pre-adult batch (S03), with no return of non-bridge zero-assignment failures.
- Remaining gap is linkage coverage on `Fry -> Parr` for this batch (`incomplete_linkage=1`), not a zero-assignment regression.

## Generated artifacts
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/semantic_validation_stofnfiskur_juni24_2026-02-10_station_focus.md`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/semantic_validation_stofnfiskur_juni24_2026-02-10_station_focus.summary.json`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/fw_to_sea_deterministic_stofnfiskur_juni24_2026-02-10.md`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/fw_to_sea_deterministic_stofnfiskur_juni24_2026-02-10.json`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/logs/migrate_stofnfiskur_juni24_2026-02-10.log`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/logs/semantic_validation_stofnfiskur_juni24_2026-02-10.log`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/logs/counts_stofnfiskur_juni24_2026-02-10.log`
