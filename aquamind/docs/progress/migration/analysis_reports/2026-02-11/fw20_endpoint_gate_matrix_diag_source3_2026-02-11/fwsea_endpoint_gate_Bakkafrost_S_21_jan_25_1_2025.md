# FWSEA Endpoint Pairing Acceptance Gate

## Scope

- Component key: `B52612BD-F18B-48A4-BF21-12B5FC246803`
- Component id: `Bakkafrost_S-21_jan_25_1_2025`
- Component population count: 183
- CSV directory: `/Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract`
- Expected direction: `sales_to_input`

## Endpoint Metrics

- InternalDelivery rows touching component populations: 1
- Rows with component populations on both sides: 0
- Candidate rows (single-side touch with counterpart populations): 1
- Deterministic rows: 0
- Ambiguous rows: 1
- Deterministic coverage: 0.000
- Marine-target deterministic rows: 0
- Marine-target deterministic ratio: 0.000
- Max targets per source endpoint: 0
- Sources with multiple targets: 0
- Incomplete-linkage fallback count (semantic summary): 0

## Gate Results

| Gate | Passed | Details |
| --- | --- | --- |
| evidence | NO | candidate_rows=1, min=10 |
| uniqueness | NO | ambiguous_rows=1, max=0 |
| coverage | NO | coverage=0.000, min=0.900 |
| stability | YES | max_targets_per_source=0, max=1 |
| marine_target | NO | ratio=0.000, min=1.000 |
| overall | FAIL | endpoint pairing acceptance gate |

## Direction Counts

- input_to_sales: 1

## Reason Counts

- direction_mismatch: 1

## Dominant Stage Pair Counts

- fw->fw: 1
