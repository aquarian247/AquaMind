# Stofnfiskur Juni 24 Lifecycle Discrepancy Investigation (2026-02-11)

## Scope
Investigate inflated/non-conservative lifecycle progression for migrated batch `Stofnfiskur Juni 24` (component `EDF931F2-51CC-4A10-9002-128E7BF8067C`) without introducing FishTalk coupling into runtime code.

## Runtime Status Confirmed
- Runtime lifecycle endpoint source is active:
  - `GET /api/v1/batch/container-assignments/lifecycle-progression/?batch=<id>&basis=stage_entry`
- Runtime stage-entry selector updated to choose earliest positive row per `(container, stage)` with fallback to earliest row.

## Deterministic Migration Findings

### 1) Assignment materialization inflation (migration tooling)
In `scripts/migration/tools/pilot_migrate_component.py`, status-driven overrides were promoting counts for:
- superseded same-stage rows with operational activity, and
- rows where `known_removals > conserved_count`.

This amplified rows with outside-component mixing evidence and inflated stage totals.

### 2) Removal-sync mutation destroyed stage-entry semantics
In each of:
- `scripts/migration/tools/pilot_migrate_component_mortality.py`
- `scripts/migration/tools/pilot_migrate_component_culling.py`
- `scripts/migration/tools/pilot_migrate_component_escapes.py`

assignment counts were being rewritten as:
- `assignment.population_count = baseline_population_count - lifetime_removals`

This transformed assignment rows from entry baselines into residual counts and invalidated stage-entry progression interpretation.

### 3) Remaining non-monotonicity is linkage-boundary uncertainty
Existing semantic evidence for this component shows:
- `Fry -> Parr` transition basis `entry_window`
- reason `incomplete_linkage`
- `entry_population_external_source_count = 2`
- positive delta (increase)

Source: `aquamind/docs/progress/migration/analysis_reports/2026-02-11/semantic_validation_stofnfiskur_juni_24_2026-02-11_faroe_fw_under30_canary5.summary.json`

This indicates stitched-component membership is not a fully closed cohort boundary.

## Tooling Changes Applied (migration-only)

1. `scripts/migration/tools/pilot_migrate_component.py`
- `known_removals > conserved_count` now floors to `known_removals` instead of promoting to full status snapshot.
- superseded operational rows now keep conservative floor (`max(count, known_removals)`) instead of full status snapshot.

2. `scripts/migration/tools/pilot_migrate_component_mortality.py`
3. `scripts/migration/tools/pilot_migrate_component_culling.py`
4. `scripts/migration/tools/pilot_migrate_component_escapes.py`
- Added `--sync-assignment-counts` (default off).
- Assignment count rewrite (`baseline - removals`) now runs only when explicitly enabled.
- Default behavior now preserves stage-entry assignment semantics.

## Re-run Commands Executed

```bash
PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 \
python /Users/aquarian247/Projects/AquaMind/scripts/migration/clear_migration_db.py

PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 \
python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/pilot_migrate_component.py \
  --component-key EDF931F2-51CC-4A10-9002-128E7BF8067C \
  --report-dir /Users/aquarian247/Projects/AquaMind/scripts/migration/output/input_batch_migration/Stofnfiskur_Juni_24_2_2024 \
  --batch-number "Stofnfiskur Juni 24" \
  --expected-site "S03 Norðtoftir"

PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 \
python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/pilot_migrate_component_transfers.py \
  --component-key EDF931F2-51CC-4A10-9002-128E7BF8067C \
  --report-dir /Users/aquarian247/Projects/AquaMind/scripts/migration/output/input_batch_migration/Stofnfiskur_Juni_24_2_2024

PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 \
python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/pilot_migrate_component_feeding.py \
  --component-key EDF931F2-51CC-4A10-9002-128E7BF8067C \
  --report-dir /Users/aquarian247/Projects/AquaMind/scripts/migration/output/input_batch_migration/Stofnfiskur_Juni_24_2_2024

PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 \
python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/pilot_migrate_component_growth_samples.py \
  --component-key EDF931F2-51CC-4A10-9002-128E7BF8067C \
  --report-dir /Users/aquarian247/Projects/AquaMind/scripts/migration/output/input_batch_migration/Stofnfiskur_Juni_24_2_2024

PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 \
python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/pilot_migrate_component_mortality.py \
  --component-key EDF931F2-51CC-4A10-9002-128E7BF8067C \
  --report-dir /Users/aquarian247/Projects/AquaMind/scripts/migration/output/input_batch_migration/Stofnfiskur_Juni_24_2_2024

PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 \
python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/pilot_migrate_component_culling.py \
  --component-key EDF931F2-51CC-4A10-9002-128E7BF8067C \
  --report-dir /Users/aquarian247/Projects/AquaMind/scripts/migration/output/input_batch_migration/Stofnfiskur_Juni_24_2_2024

PYTHONPATH=/Users/aquarian247/Projects/AquaMind SKIP_CELERY_SIGNALS=1 \
python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/pilot_migrate_component_escapes.py \
  --component-key EDF931F2-51CC-4A10-9002-128E7BF8067C \
  --report-dir /Users/aquarian247/Projects/AquaMind/scripts/migration/output/input_batch_migration/Stofnfiskur_Juni_24_2_2024
```

## Before/After Evidence (stage_entry basis)

Pre-change runtime baseline (batch `447`):
- Egg&Alevin: `1,708,576`
- Fry: `502,720`
- Parr: `2,108,165`
- Smolt: `437,559`
- Post-Smolt: `329,767`
- Total: `5,086,787`

Post-change rerun (batch `449`):
- Egg&Alevin: `1,760,038`
- Fry: `196,889`
- Parr: `299,007`
- Smolt: `104,377`
- Post-Smolt: `42,547`
- Total: `2,402,858`

Observed DB event integrity after rerun:
- Assignments: `145`
- Feeding events: `4013`
- Mortality events: `3821`
- Mortality total count: `432,863`

## Interpretation
- Inflation is substantially reduced by migration-tooling changes.
- Remaining `Fry -> Parr` increase persists and is explained by incomplete linkage / external-source evidence within stitched-component boundaries.
- This is a migration-boundary uncertainty issue, not runtime chart math.

## Next Deterministic Step
For strict non-increasing cohort progression, migrate this cohort using closed linked-batch/chain boundaries (or explicitly exclude external-source stage-entry rows under a deterministic migration rule), then re-run semantic validation and compare transition deltas.
