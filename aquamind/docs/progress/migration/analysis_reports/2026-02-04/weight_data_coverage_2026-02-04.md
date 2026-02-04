# Weight Data Coverage (Manual Samples + Status Values)

Date: 2026-02-04
Cutoff: 2026-02-04 (only samples/statuses on or before this date)

Definitions:
- Manual weight samples: `ext_weight_samples_v2.OperationType = 10` (Weight sample).
- Biomass measurements: `OperationType = 32` (reported separately).
- Final weight (primary): latest `status_values` row on/before cutoff **with `CurrentCount > 0`** (avg_weight_g = CurrentBiomassKg*1000/CurrentCount).
- Final weight (fallback): latest manual weight sample if no positive-count status exists.

## FW SF NOV 23

- InputProjectID: `EC44DBBA-067D-4B34-89CD-630BAFFC5BE9`
- InputProject name/year: SF NOV 23 / 2023
- Populations in FishGroupHistory: 130

Manual weight samples (OperationType 10):
- Samples: 159
- Populations with ≥1 manual sample: 26
- Sample date range: 2024-02-19 → 2024-12-27

Biomass measurements (OperationType 32):
- Samples: 0
- Populations with ≥1 biomass measurement: 0

Status values:
- Rows: 6400
- Populations with ≥1 status row: 130
- Status date range: 2023-11-16 → 2024-12-30
- Populations whose *latest* status row has `CurrentCount = 0`: 3

Final weight availability (as of cutoff):
- Populations with status-derived avg_weight_g (latest positive-count row): 130
- Fallback to latest manual weight sample: 0
- Missing both status + manual sample: 0

## FW Benchmark Gen. Juni 2024

- InputProjectID: `61088D52-8A7E-454B-96FC-7720B2244488`
- InputProject name/year: Benchmark Gen. Juni 2024 / 2024
- Populations in FishGroupHistory: 359

Manual weight samples (OperationType 10):
- Samples: 607
- Populations with ≥1 manual sample: 86
- Sample date range: 2024-09-05 → 2025-10-23

Biomass measurements (OperationType 32):
- Samples: 0
- Populations with ≥1 biomass measurement: 0

Status values:
- Rows: 9626
- Populations with ≥1 status row: 355
- Status date range: 2024-06-13 → 2025-10-31
- Populations whose *latest* status row has `CurrentCount = 0`: 26

Final weight availability (as of cutoff):
- Populations with status-derived avg_weight_g (latest positive-count row): 355
- Fallback to latest manual weight sample: 0
- Missing both status + manual sample: 4

Populations missing both (PopulationName, PopulationID):
- Benchmark Gen. Juni 2024 (CF14DF4F-DFE7-43A4-86F0-DF58DA4E26BA)
- Benchmark Gen. Juni 2024 (3E6B54BE-6838-4EC5-82AA-5C3C343C476C)
- Benchmark Gen. Juni 2024 (A788ED76-0931-47CA-A4E4-E35149A6E4CF)
- Benchmark Gen. Juni 2024 (14B06AF6-CE6F-43E0-8713-62F9F0375376)

## Sea Summar 2024

- InputProjectID: `433A6D50-7B57-4309-8D16-776C5D1DE1B5`
- InputProject name/year: Summar 2024 / 2024
- Populations in FishGroupHistory: 106

Manual weight samples (OperationType 10):
- Samples: 0
- Populations with ≥1 manual sample: 0
- Sample date range: N/A → N/A

Biomass measurements (OperationType 32):
- Samples: 0
- Populations with ≥1 biomass measurement: 0

Status values:
- Rows: 5798
- Populations with ≥1 status row: 106
- Status date range: 2024-08-06 → 2025-10-15
- Populations whose *latest* status row has `CurrentCount = 0`: 41

Final weight availability (as of cutoff):
- Populations with status-derived avg_weight_g (latest positive-count row): 106
- Fallback to latest manual weight sample: 0
- Missing both status + manual sample: 0

## Sea Var 2024

- InputProjectID: `82A9B732-322F-4D4C-AD7C-E09ACC7F8545`
- InputProject name/year: Vár 2024 / 2024
- Populations in FishGroupHistory: 109

Manual weight samples (OperationType 10):
- Samples: 0
- Populations with ≥1 manual sample: 0
- Sample date range: N/A → N/A

Biomass measurements (OperationType 32):
- Samples: 0
- Populations with ≥1 biomass measurement: 0

Status values:
- Rows: 4541
- Populations with ≥1 status row: 109
- Status date range: 2024-03-10 → 2025-04-29
- Populations whose *latest* status row has `CurrentCount = 0`: 36

Final weight availability (as of cutoff):
- Populations with status-derived avg_weight_g (latest positive-count row): 109
- Fallback to latest manual weight sample: 0
- Missing both status + manual sample: 0

