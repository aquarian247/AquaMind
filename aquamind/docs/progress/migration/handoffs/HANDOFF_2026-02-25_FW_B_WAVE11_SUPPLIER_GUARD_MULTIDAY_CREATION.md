# HANDOFF 2026-02-25 - FW B wave11 supplier-guard for multi-day creation starts

## Scope
- Encode new FishTalk evidence for non-movers `93` and `140`.
- Preserve multi-day batch-creation support while suppressing stitched foreign start clusters.
- Replay `93`/`140` first, then recompute board impact from the prior mismatch set.

## FishTalk evidence encoded
- `93` (`NH FEB 25`, `FW21 Couldoran`)
  - True start anchor is `2025-02-12` in `H001-H046`.
  - Non-mover mismatch cluster was `H047-H056` at `2025-02-24`.
  - Extract evidence: this later cluster has a disjoint `SupplierID` from the component-start anchor supplier.
- `140` (`Bakkafrost feb 2024`, `S16 Glyvradalur`)
  - Valid multi-origin start across multiple dates/objects (`2024-02-07` plus `2024-02-16`).
  - Extract evidence: both start clusters share the same supplier lineage.

## Deterministic rule implemented
- Added supplier lineage extraction for `Ext_Inputs_v2` populations.
- In `pilot_migrate_component.py`, added a guarded exact-start-zero rule for early creation-window rows:
  - only for closed members in seed stages (`Egg&Alevin`, `Fry`, `Parr`, `Smolt`) within creation window,
  - only when exact-start status is `0`,
  - only when member supplier IDs are disjoint from component-start supplier IDs,
  - and re-enforced after downstream supersede/bridge heuristics.
- This preserves legitimate multi-day creation starts with supplier continuity (`140`) while suppressing stitched foreign starts (`93` cluster `H047-H056`).

## Files changed
- `scripts/migration/tools/etl_loader.py`
- `scripts/migration/tools/pilot_migrate_component.py`
- `aquamind/docs/progress/migration/handoffs/HANDOFF_2026-02-25_FW_B_WAVE11_SUPPLIER_GUARD_MULTIDAY_CREATION.md`

## Replay execution
- Replayed:
  - `NH FEB 25|1|2025`
  - `Bakkafrost feb 2024|1|2024`
- Both migrations completed successfully (`11/11` scripts per batch).

## Targeted result (`93`, `140`)
- Source board: `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave10_next5_20260225_090255.json`
- Old mismatches: `18`
- Remaining mismatches: `8`
- Delta: `-10`
- Per batch:
  - `93`: `10 -> 0` (cleared)
  - `140`: `8 -> 8` (unchanged, still non-mover)

## Board impact (row-level recheck of prior mismatch set)
- Method:
  - Rechecked every prior mismatch row from wave10 board against current assignment counts using the same captured expected counts.
  - Source board has complete mismatch-row coverage (`examples == mismatches` for every batch), so the prior mismatch set is fully covered.
- Totals:
  - prior mismatches: `184`
  - remaining mismatches: `174`
  - delta: `-10`
- Remaining taxonomy:
  - `A=0`, `B=170`, `C=4`, `D=0`

## Updated top culprits (post-wave11 row recheck)
1. `140` (`Bakkafrost feb 2024`) - `8`
2. `152` (`Bakkafrost S-21 sep24`) - `7`
3. `153` (`StofnFiskur S-21 apr 25`) - `7`
4. `154` (`StofnFiskur S-21 juli25`) - `7`
5. `155` (`Stofnfiskur S-21 feb24`) - `7`

## Artifacts generated
- Targeted replay summary:
  - `scripts/migration/output/fw_b_class_targeted_replay_wave11_supplier_guard_20260225_113208.json`
  - `scripts/migration/output/fw_b_class_targeted_replay_wave11_supplier_guard_20260225_113208.md`
- Board row recheck:
  - `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave11_supplier_guard_row_recheck_20260225_113208.json`
  - `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave11_supplier_guard_row_recheck_20260225_113208.md`
  - `scripts/migration/output/fw_policy_scope_tiebreak_postwave_wave11_supplier_guard_row_recheck_20260225_113208.csv`
- FishTalk culprits:
  - `scripts/migration/output/fw_fishtalk_culprits_wave11_supplier_guard_top20_20260225_113221.csv`
  - `scripts/migration/output/fw_fishtalk_culprits_wave11_supplier_guard_top20_20260225_113221.md`

## Go / No-go
- Decision: **FW not yet ready** for marine continuation.
- Rationale: class-A remains `0`, but residual class-B volume is still high (`170` in row-rechecked prior mismatch set), with `140` still a non-mover.

## Recommended next step
- Run canonical full FW board recompute with the same policy evaluator used in prior waves to confirm no new mismatch introductions outside the prior mismatch set.
- Then run next targeted wave on:
  - `140, 152, 153, 154, 155`
- For `140`, add one more deterministic refinement specifically for same-supplier multi-anchor start windows that begin on distinct dates and object hierarchies (tray/rack + container).
