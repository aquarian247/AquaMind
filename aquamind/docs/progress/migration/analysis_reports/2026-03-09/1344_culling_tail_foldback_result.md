# 1344 Culling-Tail Fold-Back Result

Date: 2026-03-09

Component:
- `7311DFA1-6535-4D97-B708-BD4ED79AB8F9`
- AquaMind batch id `1344`
- Batch number `Stofnfiskur Des 23 - Vár 2024`

Applied change:
- `pilot_migrate_component.py` now folds same-container, same-stage residual `SourcePopAfter` populations back into the predecessor assignment when they:
  - exist only as a residual tail,
  - have culling activity,
  - have no non-culling operational activity,
  - are fully consumed by culling.
- `pilot_migrate_component_culling.py` then reattaches the culling `MortalityEvent` to the folded predecessor assignment.

Execution:
- Replayed component in `migr_dev` with `--merge-existing-component-map`.
- Replay emitted:
  - `Culling-only same-container residual tails eligible for fold-back: 17`
  - `Folded culling-only same-container residual tails into predecessor assignments: 17`
- Replayed culling for the same component.

Observed result in `migr_dev`:
- The small standalone fry-tail assignments at `501`, `502`, `503`, `505`, `506`, `507`, `510`, and `511` no longer carry the culling rows.
- The culling events are now attached to the long predecessor fry assignments:
  - `501`: culling `2622`
  - `502`: culling `4214`
  - `503`: culling `1000`
  - `505`: culling `2500`
  - `506`: culling `2500`
  - `507`: culling `1500`
  - `510`: culling `4615`
  - `511`: culling `4000`
- Multi-day predecessor rows were extended correctly where needed:
  - `505`, `506`, `507` now depart `2024-05-10` instead of `2024-05-08`

Remaining caveat:
- Zero-count bridge rows still remain for some of these containers, for example `35205`, `35209`, `35213`, `35224`, `35228`, `35232`, `35233`, `35234`, `35240`, `35244`.
- Those are not the culling-tail rows; they are separate zero-count bridge artifacts.
- The culling-tail semantic problem is fixed. Zero-count bridge suppression is a separate cleanup policy.

Files changed:
- [pilot_migrate_component.py](/Users/aquarian247/Projects/AquaMind/scripts/migration/tools/pilot_migrate_component.py)
- [pilot_migrate_component_culling.py](/Users/aquarian247/Projects/AquaMind/scripts/migration/tools/pilot_migrate_component_culling.py)
- [population_assignment_mapping.py](/Users/aquarian247/Projects/AquaMind/scripts/migration/tools/population_assignment_mapping.py)
- [scripts/migration/tools/README.md](/Users/aquarian247/Projects/AquaMind/scripts/migration/tools/README.md)
- [MIGRATION_CANONICAL.md](/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/MIGRATION_CANONICAL.md)
