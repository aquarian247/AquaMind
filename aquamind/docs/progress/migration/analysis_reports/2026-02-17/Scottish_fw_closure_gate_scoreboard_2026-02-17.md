# Scottish Freshwater Closure Gate Scoreboard (2026-02-17)

## Scope

Consolidated closeout gate for Scottish freshwater migration under fixed backup cutoff `2026-01-22` and profile baseline `fw_default`.

## Station-Wave Final Scoreboard

| Station | Wave model | Strict/initial migration | Strict/initial semantic | Recovery/rerun | Final migration | Final semantic | Final status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `FW13 Geocrab` | Two-pass | `2/2` | `2/2` | Not needed | `2/2` | `2/2` | PASS |
| `FW21 Couldoran` | Two-pass | `3/7` | `3/7` | `4/4` recovered | `7/7` | `7/7` | PASS |
| `FW22 Applecross` | Initial + recovery rerun | `8/10` | `0/10` | semantic/migration rerun applied | `10/10` | `10/10` | PASS |
| `FW24 KinlochMoidart` | Two-pass | `1/7` | `1/7` | `6/6` recovered | `7/7` | `7/7` | PASS |

**Overall station-wave totals:** `26/26` migration PASS, `26/26` semantic PASS.

## Full Environmental Canary Gate

| Canary | Batch key | Migration | Semantic | Runtime |
| --- | --- | --- | --- | --- |
| Faroe S21 canary | `Bakkafrost S-21 jan 25|1|2025` | PASS | PASS | PASS |
| FW22 canary | `SF MAR 25|1|2025` | PASS | PASS | PASS |

## B01/B02 Regression Anchor

- Anchor artifact: `aquamind/docs/progress/migration/analysis_reports/2026-02-16/S21_Bakkafrost_S21_jan25_B01_B02_regression_anchor_check_after_outside_holder_fix_2026-02-16.json`
- `B01_pass=true`, `B02_pass=true`, `overall_pass=true`
- Closeout interpretation: **no new B01/B02 regression signal**.

## Archived-Station Follow-Up (Operator Sweep + Validation)

- Operator broad scan window (`Aug 2023 -> current`) found one archived-station signal.
- Follow-up signal: `23Q3 SF` at `FW14 Harris Lochs` (`LA09-LA16`).
- Observed footprint in validated slice:
  - `transfer_in_count=449242`
  - `transfer_out_count=0`
  - `culling_count=12305`
  - `mortality_count=28729`
- Classification: **culled/depleted segment**, not unresolved cross-station migration blocker.

## Closeout Gate Verdict

**PASS** - Scottish freshwater migration phase is closed for current active stations and horizon.

Gate criteria satisfied:

1. all active Scottish FW stations reached final migration + semantic PASS,
2. full environmental canaries passed migration + semantic + runtime,
3. B01/B02 anchor remains green,
4. no unresolved archived-station blocker in current scope.

## Marine Entry Focus (Next Natural Step)

Sea cohorts are expected to be operationally simpler (mostly same-ring progression). The difficult part is FW->Sea ingress pairing.

Execution policy for next wave:

1. Use canonical linkage first (`PublicTransfers` / `Ext_Transfers_v2` + lineage where present).
2. When canonical edges are absent, generate **non-canonical candidate pairs** using temporal + geography semantics:
   - FW source segment terminal/depletion date = `X`
   - Sea destination segment fill/start date in `[X, X+2 days]`
   - same geography scope, `S* -> A*` boundary only
   - exclude `L* -> S*` broodstock flows and FW->FW flows
3. Mark candidate links as **provisional evidence** for migration-tooling review/gating, never runtime truth.
4. Promote candidates only after cohort-level semantic gate pass and spot-check review.
