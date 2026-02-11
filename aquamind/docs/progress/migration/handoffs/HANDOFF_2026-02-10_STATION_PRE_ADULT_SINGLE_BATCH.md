# Migration Handoff (2026-02-10 Station/Pre-Adult Single-Batch Focus)

## Scope
- Single-batch hardening only: `Benchmark Gen. Juni 2024|2|2024`.
- Station guard enforced: `--expected-site "S24 Strond"`.
- Runtime separation preserved: migration changes only in tooling/scripts (no FishTalk-coupling added to runtime API/UI).

## 2026-02-10 Follow-up Evidence Pass (Sea Linkage + Stage Inflation)

### Additional tooling/report change in this pass
File:
- `scripts/migration/tools/migration_semantic_validation_report.py`

Changes:
- Added `Outside-Component Destination Evidence` section:
  - classifies external SubTransfers edges by role,
  - summarizes direct external and reachable descendant populations by `ProdStage`/`Site`/`SiteGroup`,
  - emits explicit `marine_linkage_evidence` boolean.
- Added `Active Container Latest Holder Evidence` section:
  - for each active migrated assignment container, resolves latest non-zero source status holder,
  - reports whether latest holder is still in selected component or outside it.
- Added stage accumulation diagnostics in lifecycle table:
  - `active_population_total`,
  - `peak_concurrent_population`,
  - `full_to_entry_ratio`,
  - `full_to_peak_ratio`.

Why:
- Enables non-ambiguous evidence checks for "transferred to sea?" and "why are Parr/Smolt totals inflated?" without adding FishTalk logic to runtime API/UI.

### Linkage-improvement update in this pass
File:
- `scripts/migration/tools/migration_semantic_validation_report.py`

Changes:
- Added deterministic SubTransfer predecessor-graph fallback for stage-entry linkage when direct linkage is missing.
- Fallback traces explicit predecessor roles only:
  - `DestPopAfter <- SourcePopBefore`
  - `DestPopAfter <- DestPopBefore`
  - `SourcePopAfter <- SourcePopBefore`
- Fallback is bounded by `--lineage-fallback-max-depth` (default `14`) and remains component-scoped via selected component stage mappings.
- Added linkage diagnostics fields:
  - `lineage_fallback_max_depth`
  - `transition_lineage_graph_count`
  - per-transition `lineage_graph_used`

Why:
- Converts evidence-backed incomplete transitions to bridge-aware without introducing inferred FishTalk parsing into runtime.

## New migration-tooling changes in this step

### 1) Assignment count/biomass consistency + active-state gating
File:
- `scripts/migration/tools/pilot_migrate_component.py`

Changes:
- Added latest-status non-zero evidence map per population (`CurrentCount > 0` or `CurrentBiomassKg > 0` at each population’s latest status timestamp).
- Updated active assignment selection:
  - requires non-zero latest status evidence,
  - keeps latest non-zero population per container,
  - forces inactive when `population_count <= 0`.
- Updated assignment biomass/weight derivation:
  - derive status average weight (`CurrentBiomassKg / CurrentCount * 1000`) when available,
  - recompute assignment biomass from final chosen assignment count to keep count/biomass consistent,
  - populate `avg_weight_g` from status-derived average (fallback: biomass/count when possible).

Why:
- Eliminates impossible implied container weights caused by mixing conserved counts with unscaled status biomass.
- Prevents rows with latest zero status from appearing active.

### 2) Migration history metadata robustness
File:
- `scripts/migration/history.py`

Changes:
- `save_with_history()` now catches `update_change_reason()` exceptions, matching the existing tolerant behavior in `get_or_create_with_history()`.

Why:
- Prevents migration aborts on metadata-only history edge cases.

## Exact replay commands used

### 1) Wipe migration DB
```bash
PYTHONPATH=/Users/aquarian247/Projects/AquaMind \
SKIP_CELERY_SIGNALS=1 \
python /Users/aquarian247/Projects/AquaMind/scripts/migration/clear_migration_db.py
```

### 2) Single batch migration (station-guarded)
```bash
PYTHONPATH=/Users/aquarian247/Projects/AquaMind \
SKIP_CELERY_SIGNALS=1 \
python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/pilot_migrate_input_batch.py \
  --batch-key "Benchmark Gen. Juni 2024|2|2024" \
  --expected-site "S24 Strond" \
  --use-csv /Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract \
  --skip-environmental
```

Output summary:
- `Scripts completed: 12/12`
- Batch created as `Benchmark Gen. Juni 2024` with `359` assignments, `87` transfer workflows/actions, `607` growth samples.

### 3) Semantic validation report (same batch)
```bash
PYTHONPATH=/Users/aquarian247/Projects/AquaMind \
SKIP_CELERY_SIGNALS=1 \
python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/migration_semantic_validation_report.py \
  --component-key 5DC4DA59-A891-4BBB-BB2E-0CC95C633F20 \
  --report-dir /Users/aquarian247/Projects/AquaMind/scripts/migration/output/input_batch_migration/Benchmark_Gen._Juni_2024_2_2024 \
  --use-csv /Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract \
  --stage-entry-window-days 2 \
  --lineage-fallback-max-depth 14 \
  --check-regression-gates \
  --max-non-bridge-zero-assignments 2 \
  --output /Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-06/semantic_validation_benchmark_gen_juni_2024_2026-02-10_station_focus.md \
  --summary-json /Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-06/semantic_validation_benchmark_gen_juni_2024_2026-02-10_station_focus.summary.json
```

### 4) Counts report
```bash
PYTHONPATH=/Users/aquarian247/Projects/AquaMind \
SKIP_CELERY_SIGNALS=1 \
python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/migration_counts_report.py
```

## Verified outputs

### Regression gate outcome (semantic report)
- Non-bridge zero assignments: `0` (threshold `2`)
- Transfer actions with `transferred_count <= 0`: `0`
- Positive transition deltas without mixed-batch evidence: `0`
- Overall gate result: `PASS`
- Transition basis (after linkage improvement): `4/4` bridge-aware, `0/4` entry-window.
- Bridge-aware transitions using lineage-graph fallback: `4`.

### Linkage baseline vs improved (same code path)
Controlled comparison (semantic script only):
- Baseline: `--lineage-fallback-max-depth 0`
- Improved: `--lineage-fallback-max-depth 14`

Observed:
- Basis counts:
  - depth `0`: `entry_window=4`, `fishgroup_bridge_aware=0`
  - depth `14`: `entry_window=0`, `fishgroup_bridge_aware=4`
- Entry-window reasons:
  - depth `0`: `incomplete_linkage=4`
  - depth `14`: `incomplete_linkage=0`, `bridge_aware=4`
- Per transition linkage coverage (`linked destinations / entry populations`):
  - `Egg&Alevin -> Fry`: `0/12` -> `12/12`
  - `Fry -> Parr`: `3/9` -> `9/9`
  - `Parr -> Smolt`: `1/3` -> `3/3`
  - `Smolt -> Post-Smolt`: `1/4` -> `4/4`

Note:
- `Egg&Alevin -> Fry` now links fully, but bridge-aware basis reports a large drop warning (`unexplained_drop_vs_known_losses=404430`) due low conserved-count coverage in linked destinations (`to_population=89748`).

### Sea transfer evidence (non-ambiguous)
From semantic report `Outside-Component Destination Evidence`:
- `marine_linkage_evidence: NO`
- Direct external destination populations: `100`
  - `ProdStage`: `Hatchery:100`
  - `Site`: `S24 Strond:100`
- Reachable outside descendants: `227`
  - `ProdStage`: `Hatchery:227`
  - `Site`: `S24 Strond:227`

Interpretation:
- This replay has no SubTransfers-based evidence of FW->Sea linkage for the selected stitched component.
- It does show outside-component linkage inside the same station/hatchery context.

### Active container latest-holder evidence
From semantic report `Active Container Latest Holder Evidence`:
- Containers checked: `13`
- Latest holder still in selected component: `4` (`G1`-`G4`)
- Latest holder outside selected component: `9` (`H1`-`H4`, `I1`, `I2`, `I4`, `J2`, `J3`)
- Unknown latest holder: `0`
- All latest holders classify to `Site=S24 Strond`, `ProdStage=Hatchery`.

Interpretation:
- Container reuse/outside-component occupancy is present, but source evidence still does not classify these holders as marine.

### Parr/Smolt/Post-Smolt inflation decomposition
From stage diagnostics in semantic report:

| Stage | Entry population | Peak concurrent population | Full summed population | Active population | Full/entry | Full/peak |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Parr | 2,879,144 | 4,031,711 | 11,211,209 | 0 | 3.89 | 2.78 |
| Smolt | 531,460 | 3,566,911 | 10,048,836 | 0 | 18.91 | 2.82 |
| Post-Smolt | 407,372 | 2,503,456 | 5,170,561 | 1,619,290 | 12.69 | 2.07 |

Interpretation:
- Inflation is in `full summed population` (sum across all historical assignment rows in stage), not in `entry`/`peak concurrent` baselines.
- This is consistent with cumulative segment history, not a transfer-time guess and not a date parsing issue.

### Growth timeline check (date span)
Command:
```bash
PYTHONPATH=/Users/aquarian247/Projects/AquaMind \
SKIP_CELERY_SIGNALS=1 \
python - <<'PY'
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','aquamind.settings')
os.environ.setdefault('SKIP_CELERY_SIGNALS','1')
from scripts.migration.safety import configure_migration_environment, assert_default_db_is_migration_db
configure_migration_environment()
import django
django.setup()
assert_default_db_is_migration_db()
from apps.batch.models import Batch, GrowthSample
from django.db.models import Min, Max, Count
b = Batch.objects.get(batch_number='Benchmark Gen. Juni 2024')
agg = GrowthSample.objects.filter(assignment__batch=b).aggregate(
    min_date=Min('sample_date'),
    max_date=Max('sample_date'),
    count=Count('id'),
)
print(agg)
if agg['min_date'] and agg['max_date']:
    span_days = (agg['max_date'] - agg['min_date']).days
    print('span_days', span_days, 'span_weeks', round(span_days / 7, 2))
PY
```

Output:
- `min_date=2024-09-05`
- `max_date=2025-10-23`
- `count=607`
- `span_weeks=59.0`

Interpretation:
- Migrated growth sample dates are approximately 59 weeks wide; a chart showing ~600 weeks likely reflects axis/index handling, not source sample-date span.

Report files:
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-06/semantic_validation_benchmark_gen_juni_2024_2026-02-10_station_focus.md`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-06/semantic_validation_benchmark_gen_juni_2024_2026-02-10_station_focus.summary.json`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-06/station_focus_assignment_diagnostics_benchmark_gen_juni_2024_2026-02-10.md`

### Container assignment diagnostics (post-fix)
From migration DB (`aquamind_db_migr_dev`) after final replay:
- Active assignments in `Post-Smolt`: `13`
- Active implied average weight range: `125.18g` to `300.10g`
- High-weight low-count outliers (`implied_weight >= 1000g` and `population_count <= 5000`): `0`
- Growth samples date range: `2024-09-05` to `2025-10-23` (`607` rows)

## Compact findings table

| batch | non-bridge zero assignments (before -> after) | gate result (before -> after) | transition basis changes |
| --- | --- | --- | --- |
| Benchmark Gen. Juni 2024 | 24 -> 0 | FAIL -> PASS | bridge-aware 0/4 -> 4/4, entry-window 4/4 -> 0/4 (lineage fallback depth 14) |

## Open risks / unresolved items
1. Linkage coverage is complete (`4/4` bridge-aware), but `Egg&Alevin -> Fry` bridge-aware delta warns (`drop exceeds known removals by 404430`), indicating low conserved-count coverage for linked destinations.
2. Lifecycle-stage population chart inflation concern remains for full-summed historical assignments (entry-window population remains the trusted migration sanity baseline).
3. Growth chart “600+ weeks” concern is not supported by migrated dates (samples are within 2024-09 to 2025-10); likely chart-axis interpretation over dense per-sample points.

## Next steps
1. Keep single-batch mode and evaluate whether conserved-count provenance for the `Egg&Alevin -> Fry` linked destination set can be improved without relaxing zero/transfer guards.
2. After linkage improvement is stable, replay the same rules on one additional station/pre-adult batch before returning to multi-batch cohort checks.
