# HANDOFF 2026-02-17: Scottish FW Closure + Marine Entry

## Scope

Finalize Scottish freshwater migration closeout and define the immediate execution path into sea-based cohorts.

## Non-negotiables honored

- Backup cutoff remains pinned to `2026-01-22`.
- AquaMind runtime remains FishTalk-agnostic.
- Source-specific behavior remains in migration tooling, validation, and reporting.
- Profile baseline remains `fw_default`.

## Scottish FW closure gate result

Active Scottish freshwater stations are now covered end-to-end:

- `FW13 Geocrab`
- `FW21 Couldoran`
- `FW22 Applecross`
- `FW24 KinlochMoidart`

Final gate status:

- Station-wave totals: `26/26` migration PASS, `26/26` semantic PASS.
- Full environmental canaries: `2/2` migration PASS, semantic PASS, runtime PASS.
- Regression anchor (`B01/B02`): PASS (`overall_pass=true`).

## Archived-station follow-up

Operator broad scan of archived stations (`Aug 2023` to current) produced one signal only:

- `23Q3 SF` at `FW14 Harris Lochs` (`LA09-LA16`)

Validation summary for that segment:

- `transfer_in_count=449242`
- `transfer_out_count=0`
- `culling_count=12305`
- `mortality_count=28729`

Interpretation: culled/depleted segment, not an unresolved transfer blocker.

## B01/B02 regression statement

**No new B01/B02 regression signal introduced by Scottish FW closure.**

Anchor artifact remains green:

- `aquamind/docs/progress/migration/analysis_reports/2026-02-16/S21_Bakkafrost_S21_jan25_B01_B02_regression_anchor_check_after_outside_holder_fix_2026-02-16.json`

## Marine-entry execution policy (next natural step)

Sea cohorts are expected to be operationally simpler (mostly same-ring progression over the growout window). The primary remaining complexity is FW->Sea ingress pairing when explicit transfer links are sparse.

Use the following evidence ladder:

1. **Canonical first:** `PublicTransfers` / `Ext_Transfers_v2` + lineage (`SubTransfers`) wherever available.
2. **If canonical is absent:** use temporal+geography candidate pairing (tooling-only, non-canonical):
   - FW terminal/depletion signal date `X`
   - Sea entry signal in `[X, X+2 days]`
   - same geography and `S* -> A*` boundary only
   - exclude `L* -> S*` broodstock and FW->FW transitions
3. **Promotion gate:** treat pairings as provisional until semantic gates pass and spot-check review confirms plausibility.

## Recommended immediate execution

1. Pick first in-scope marine cohort wave.
2. Generate FW->Sea candidate matrix using the temporal+geography policy.
3. Run migration + semantic gating on that marine pilot set.
4. Publish marine wave handoff with candidate evidence and unresolved blockers.

## Artifact index

- Scottish FW closure scoreboard:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-17/Scottish_fw_closure_gate_scoreboard_2026-02-17.md`
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-17/Scottish_fw_closure_gate_scoreboard_2026-02-17.json`
- Mapping blueprint policy update:
  - `aquamind/docs/progress/migration/DATA_MAPPING_DOCUMENT.md` (v5.0)
- Prior station-wave handoffs:
  - `aquamind/docs/progress/migration/handoffs/HANDOFF_2026-02-17_SCOTTISH_CANARY_AND_FW21_WAVE.md`
  - `aquamind/docs/progress/migration/handoffs/HANDOFF_2026-02-17_FW24_TWO_PASS_STATION_WAVE.md`
  - `aquamind/docs/progress/migration/handoffs/HANDOFF_2026-02-17_FW13_TWO_PASS_STATION_WAVE.md`
