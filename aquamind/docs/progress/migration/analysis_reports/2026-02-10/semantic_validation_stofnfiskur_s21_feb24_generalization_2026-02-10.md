# Semantic Validation Generalization Note (2026-02-10)

## Scope
- Batch key: `Stofnfiskur S-21 feb24|1|2024`
- Station guard: `S21 Viðareiði`
- Objective: validate that the same migration tooling/rules used for recent station/pre-adult work also holds for another FW batch without batch-specific script forks.

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
  --batch-key "Stofnfiskur S-21 feb24|1|2024" \
  --expected-site "S21 Viðareiði" \
  --use-csv /Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract \
  --skip-environmental
```

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

```bash
PYTHONPATH=/Users/aquarian247/Projects/AquaMind \
SKIP_CELERY_SIGNALS=1 \
python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/migration_counts_report.py \
  --batch-number "Stofnfiskur S-21 feb24"
```

## Results (S21 Feb24 run)
- Migration pipeline: `12/12` scripts completed.
- Regression gates: `PASS`.
- Non-bridge zero assignments: `0` (threshold `2`).
- Transfer actions with `transferred_count <= 0`: `0`.
- Transition basis: bridge-aware `4/4`, entry-window `0/4`.
- Bridge-aware transitions using lineage graph fallback: `2`.
- Incomplete-linkage fallback transitions: `0`.

## Cross-batch comparison (same tooling behavior)

| Batch report | Gate result | Non-bridge zero assignments | Transition basis (bridge-aware / entry-window) | Incomplete-linkage transitions |
| --- | --- | ---: | --- | ---: |
| Benchmark Gen. Juni 2024 (`2026-02-10 station focus`) | PASS | 0 | 4 / 0 | 0 |
| Stofnfiskur S-21 nov23 (`2026-02-06`) | PASS | 2 | 2 / 2 | 2 |
| Stofnfiskur S-21 feb24 (`2026-02-10 station focus`) | PASS | 0 | 4 / 0 | 0 |

Interpretation:
- The same migration + semantic rule set now yields full bridge-aware transition coverage on this additional recent FW batch.
- No batch-specific migration script branch was introduced for this run.

## Deterministic external-linkage evidence (from semantic report)
- `marine_linkage_evidence`: `false`
- Direct external destination populations: `49`
  - by production stage: `Hatchery:49`
  - by site: `S21 Viðareiði:49`
- Reachable outside descendants: `129`
  - by production stage: `Hatchery:129`
  - by site: `S21 Viðareiði:129`
- Active-container latest holder evidence:
  - containers checked: `11`
  - latest holder in selected component: `0`
  - latest holder outside selected component: `11`

Interpretation:
- Deterministic SubTransfer-based evidence for this stitched component shows outside-component occupancy/linkage within station context, but no marine classification evidence.

## Heuristic FW->Sea signal (non-gating)
Source file: `aquamind/docs/progress/migration/analysis_reports/2026-02-03/fw_to_sea_heuristic_candidates_postsmolt_2026-02-03.csv`

For `FWPopulationName=Stofnfiskur S-21 feb24`:
- Candidate rows: `288`
- Distinct SeaPopulationName values: `19`
- Candidate SeaStartTime range: `2025-03-11 00:30:28` to `2025-10-08 00:39:14`

Interpretation:
- This is heuristic evidence only, not deterministic transfer graph proof for the selected stitched component, and should not be used as a regression gate.

## Generated artifacts
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/semantic_validation_stofnfiskur_s21_feb24_2026-02-10_station_focus.md`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/semantic_validation_stofnfiskur_s21_feb24_2026-02-10_station_focus.summary.json`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/logs/migrate_s21_feb24_2026-02-10.log`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/logs/semantic_validation_stofnfiskur_s21_feb24_2026-02-10.log`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-10/logs/counts_s21_feb24_2026-02-10.log`
