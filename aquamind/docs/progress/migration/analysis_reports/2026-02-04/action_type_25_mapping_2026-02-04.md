# ActionType 25 Mapping (Empirical)

Date: 2026-02-04
Source: live query against FishTalk `Action` + `Operations` + `PublicOperationTypes`

## OperationType distribution for ActionType 25

| OperationType | PublicOperationTypes.Text | Count |
|---|---|---|
| 10 | Weight sample | 140,893 |
| 1 | Transfer | 127,942 |
| 24 | Lice sample | 111,322 |
| 26 | Combined sample | 108,311 |
| 12 | Culling | 53,362 |
| 8 | Harvest | 22,321 |
| 22 | Hatching | 10,173 |
| 32 | Biomass measurement | 8,055 |
| 7 | Sale | 7,932 |
| 5 | Input | 5,726 |
| 31 | Many to many transfer | 5,676 |
| 52 | User defined sample | 2,160 |
| 27 | Fat and color sample | 804 |
| 28 | Salt tolerance sample | 104 |
| 13 | Escape | 15 |

## ActionID table coverage

A scan of ActionID-based domain tables shows **no matches** for ActionType 25 beyond `ActionMetaData`:
- Matches in `ActionMetaData`: 1,483,882
- Matches in other ActionID tables (Feeding, Mortality, Treatment, Culling, HarvestResult, UserSample, etc): **0**

## Interpretation

ActionType 25 appears to be a **generic/operation-level Action** that accompanies multiple OperationTypes where detailed data is stored elsewhere:
- Transfers: `SubTransfers` (no ActionID)
- Weight/biomass/lice/combined samples: `ext_weight_samples_v2`, `PublicLiceSamples`, `PublicLiceSampleData`, and other sample tables (no ActionID)
- Hatching: `OperationProductionStageChange` (no ActionID)

For replay, ActionType 25 should be treated as **metadata-only** unless a specific domain table can be linked via OperationID.

