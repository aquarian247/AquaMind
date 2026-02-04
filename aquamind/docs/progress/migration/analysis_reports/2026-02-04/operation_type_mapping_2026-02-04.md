# OperationType Mapping (Empirical Sample)

Sample size per table: 200

## Table → OperationType counts

| Table | OperationType counts |
|---|---|
| `OperationProductionStageChange` | 5:135 (Input), 22:65 (Hatching) |
| `PopulationLink` | 5:148 (Input), 7:52 (Sale) |
| `PublicTransfers` | 1:168 (Transfer), 8:26 (Harvest), 5:4 (Input), 31:2 (Many to many transfer) |
| `SubTransfers` | 1:175 (Transfer), 8:17 (Harvest), 31:4 (Many to many transfer), 5:4 (Input) |

## OperationType → Tables

| OperationType | Tables (count) |
|---|---|
| 1 (Transfer) | `SubTransfers`:175, `PublicTransfers`:168 |
| 22 (Hatching) | `OperationProductionStageChange`:65 |
| 31 (Many to many transfer) | `SubTransfers`:4, `PublicTransfers`:2 |
| 5 (Input) | `PopulationLink`:148, `OperationProductionStageChange`:135, `PublicTransfers`:4, `SubTransfers`:4 |
| 7 (Sale) | `PopulationLink`:52 |
| 8 (Harvest) | `PublicTransfers`:26, `SubTransfers`:17 |

## Ext_WeightSamples_v2 OperationType counts

Source: `ext_weight_samples_v2.csv` (no OperationID, but OperationType present).

| OperationType | Count |
|---|---|
| 10 (Weight sample) | 138829 |
| 1 (Transfer) | 127105 |
| 8 (Harvest) | 22166 |
| 22 (Hatching) | 9961 |
| 32 (Biomass measurement) | 8035 |
| 7 (Sale) | 7715 |
| 5 (Input) | 5726 |
| 31 (Many to many transfer) | 5628 |
| 12 (Culling) | 603 |
| 26 (Combined sample) | 122 |