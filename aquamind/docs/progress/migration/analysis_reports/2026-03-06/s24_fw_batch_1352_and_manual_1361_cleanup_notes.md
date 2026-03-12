# S24 FW Validation Note: Batch 1352 + Manual Batch 1361 Cleanup

Date: 2026-03-06

## Summary

- Removed experimental manual batch `1361` (`Stofnfiskur Mars 2023`) from `aquamind_db_migr_dev`.
- Validated that `1352` (`Stofnfiskur desembur 2023 - Vár 2024`) was part of the March FW scoped replay.
- Confirmed that `1352` already had the correct S24 hall-stage structure:
  - `Hall A -> Egg&Alevin`
  - `Hall B -> Fry`
  - `Hall C/D -> Parr`
  - `Hall E/F -> Smolt`
  - `Hall G/H/I/J -> Post-Smolt`
- Confirmed a real scoped defect in `1352`: the `Egg&Alevin` assignments existed, but all egg-stage counts were `0` despite completed creation actions with positive egg counts.
- Repaired `1352` in `migr_dev` by backfilling zeroed egg-stage destination assignments from completed creation actions.

## Batch 1361 Cleanup

Removed from `migr_dev`:

- `122` batch assignments
- `40` transfer workflows
- `1` creation workflow
- `43` transfer actions
- `39` creation actions
- `246` `ExternalIdMap` rows
- related simple-history rows for the deleted batch/workflows/actions/assignments

Cleanup result: no residual rows remained for batch `1361`.

## Batch 1352 Findings

### Before repair

- `Egg&Alevin` rows existed in `Hall A`, but:
  - `egg_positive_rows = 0`
  - `egg_total_pop = 0`
- At the same time, the batch had:
  - `39` completed creation actions
  - `egg_total = 3,500,512`

This proved the problem was not missing source data. The creation workflow had the right egg counts, but the linked destination assignments had been left at zero.

### Repair applied

For batch `1352`, any completed creation action whose destination assignment still had `population_count <= 0` was backfilled from `egg_count_actual`, with matching `ExternalIdMap.metadata.baseline_population_count` updates.

### After repair

- `updated_assignments = 39`
- `Egg&Alevin`:
  - `egg_positive_rows = 39`
  - `egg_total_pop = 3,500,512`

Hall-stage distribution after repair:

- `Hall A / Egg&Alevin -> 3,500,512`
- `Hall B / Fry -> 3,308,215`
- `Hall C / Parr -> 7,038,797`
- `Hall D / Parr -> 5,080,405`
- `Hall E / Smolt -> 5,132,094`
- `Hall F / Smolt -> 2,884,474`
- `Hall G / Post-Smolt -> 664,377`
- `Hall H / Post-Smolt -> 2,680,139`
- `Hall I / Post-Smolt -> 2,123,316`
- `Hall J / Post-Smolt -> 2,026,980`
- marine continuation row retained:
  - `Adult / A13 Borðoyavík -> 29,528`

## Code changes

Updated:

- `scripts/migration/tools/pilot_migrate_component.py`

Changes:

- Completed creation actions now backfill zeroed destination assignment counts from authoritative `egg_count_actual`.
- Qualified hall-stage mappings are now configured to take precedence over token-stage resolution for sites with explicit canonical hall maps, including `S24 Strond`.

## Interpretation

- The March FW scope handoff is **not invalidated wholesale** by batch `1361`, because `1361` was an out-of-scope manual experiment.
- But scoped FW success metrics were too coarse to catch the `1352` egg-stage failure.
- The S24 issue observed here is a **real FW migration defect**, but it is narrower than “all S24 halls are wrong”:
  - hall-stage placement for `1352` was already correct,
  - egg-stage assignment counts were missing.

## Bulk repair follow-up

### Canonical correction

- `S24 Strond` hall-stage mapping is canonical in `DATA_MAPPING_DOCUMENT.md`:
  - `A Høll -> Egg&Alevin`
  - `B Høll -> Fry`
  - `C/D Høll -> Parr`
  - `E/F Høll -> Smolt`
  - `G/H/I/J Høll -> Post-Smolt`

This means the observed `1352` issue was not a stage-to-hall mapping error.

### Broad creation-assignment repair attempt

- Added `scripts/migration/tools/repair_creation_assignment_counts.py` to repair zeroed `Egg&Alevin` destination assignments from completed creation actions.
- Dry run identified `22` affected batches and `216` candidate assignment updates.
- Real apply repaired the pure zero-total cohorts correctly, including:
  - `1122` `Bakkafrost feb 2024 - Vár 2024`
  - `1344` `Stofnfiskur Des 23 - Vár 2024`
  - `1348` `Stofnfiskur S-21 feb24 - Vár 2024`
  - `1349` `Stofnfiskur S-21 juni24 - Summar 2024`
  - `1352` remained correct and was untouched by the bulk script

### Over-repair discovered and rolled back

- A subset of batches already had populated `Egg&Alevin` rows for the same FishTalk source container, but on parallel AquaMind assignments.
- The first repair pass used AquaMind container identity and therefore over-repaired these mixed-shape cohorts.
- Unsafe updates were rolled back for:
  - `1123` `Benchmark Gen. Septembur 2024 - Vetur 2024`
  - `1130` `Stofnfiskur Juni 24 - Summar 2024`
  - `1133` `Stofnfiskur feb 2025 - Vár 2025`
  - `1320` `Bakkafrost feb 2025 - Vár 2025`
  - `1329` `Benchmark Gen. Mars 2025 - Vár 2025`

### Repair script hardening

- The repair script now uses `ExternalIdMap.metadata.container_id` as the physical-source container key instead of AquaMind `container_id`.
- After that hardening, the guarded dry run no longer re-flags the previously over-repaired mixed-shape cohorts except:
  - `1133` (`3` assignments still plausibly missing)
  - `1329` (`38` assignments still plausibly missing)

These two remaining cohorts are still materially under their creation totals even after the guarded projection, so they need a smarter FW-specific reconstruction rather than the narrow zeroed-assignment repair.

### Important exceptions

- `1116` `24Q1 LHS ex-LC`
- `1330` `Gjógv/Fiskaaling mars 2023 - Heyst 2023`

These were flagged by the first pass, but their creation actions land on `Parr` assignments, not `Egg&Alevin` assignments, so they are outside this repair class.
