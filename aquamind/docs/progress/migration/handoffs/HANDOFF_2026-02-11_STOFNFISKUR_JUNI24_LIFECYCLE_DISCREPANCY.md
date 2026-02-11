# Handoff - 2026-02-11 - Stofnfiskur Juni 24 Lifecycle Discrepancy

## Objective
Resolve inflated lifecycle progression counts for `Stofnfiskur Juni 24` without adding FishTalk coupling to runtime API/UI.

## What Changed

### Runtime (already in place)
- `/Users/aquarian247/Projects/AquaMind/apps/batch/api/viewsets/assignments.py`
  - `lifecycle_progression` endpoint `stage_entry` now prefers earliest positive population row per `(container, stage)`.

### Migration tooling (new in this run)
- `/Users/aquarian247/Projects/AquaMind/scripts/migration/tools/pilot_migrate_component.py`
  - conservative handling for `known_removals > conserved_count`
  - conservative handling for superseded operational rows
- `/Users/aquarian247/Projects/AquaMind/scripts/migration/tools/pilot_migrate_component_mortality.py`
- `/Users/aquarian247/Projects/AquaMind/scripts/migration/tools/pilot_migrate_component_culling.py`
- `/Users/aquarian247/Projects/AquaMind/scripts/migration/tools/pilot_migrate_component_escapes.py`
  - added `--sync-assignment-counts` (default off)
  - assignment count rewrite (`baseline - removals`) now opt-in only

## Commands Run

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

## Key Outputs
- `pilot_migrate_component.py`: `outside-component edges=131`, `same-stage superseded=79`, `operational superseded=51`.
- `pilot_migrate_component_mortality.py`: `created=3787`, `assignments_adjusted=0`, `assignment_sync=off`.
- `pilot_migrate_component_culling.py`: `created=34`, `assignments_adjusted=0`, `assignment_sync=off`.
- `pilot_migrate_component_escapes.py`: `created=0`, `assignments_adjusted=0`, `assignment_sync=off`.

## Current Batch State
- Batch id: `449`
- Assignments: `145`
- Feeding events: `4013`
- Mortality events: `3821`

`stage_entry` lifecycle progression (batch `449`):
- Egg&Alevin: `1,760,038`
- Fry: `196,889`
- Parr: `299,007`
- Smolt: `104,377`
- Post-Smolt: `42,547`
- Total: `2,402,858`

## Comparison Against Prior Baseline
Prior stage_entry (batch `447`) was:
- Egg&Alevin `1,708,576`
- Fry `502,720`
- Parr `2,108,165`
- Smolt `437,559`
- Post-Smolt `329,767`
- Total `5,086,787`

Net: major reduction in inflated lifecycle totals.

## Remaining Risk / Uncertainty
- A positive `Fry -> Parr` delta still remains.
- Existing semantic evidence shows transition basis `entry_window` with `incomplete_linkage` and external-source participation for this boundary.
- Interpretation: stitched component is not a fully closed cohort boundary.

## Recommended Next Step
- Run closed linked-batch/chain migration canary for this cohort and compare transition deltas versus component-stitched output.
- Keep runtime unchanged; continue migration-only deterministic resolution.
