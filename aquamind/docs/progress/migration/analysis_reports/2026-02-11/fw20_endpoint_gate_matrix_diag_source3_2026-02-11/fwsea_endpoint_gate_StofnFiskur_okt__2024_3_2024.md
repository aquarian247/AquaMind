# FWSEA Endpoint Pairing Acceptance Gate

## Scope

- Component key: `F7D08CC6-083F-4CB4-9271-ECABFA6D3F2C`
- Component id: `StofnFiskur_okt._2024_3_2024`
- Component population count: 222
- CSV directory: `/Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract`
- Expected direction: `sales_to_input`

## Endpoint Metrics

- InternalDelivery rows touching component populations: 2
- Rows with component populations on both sides: 0
- Candidate rows (single-side touch with counterpart populations): 2
- Deterministic rows: 2
- Ambiguous rows: 0
- Deterministic coverage: 1.000
- Marine-target deterministic rows: 2
- Marine-target deterministic ratio: 1.000
- Max targets per source endpoint: 1
- Sources with multiple targets: 0
- Incomplete-linkage fallback count (semantic summary): 2

## Gate Results

| Gate | Passed | Details |
| --- | --- | --- |
| evidence | NO | candidate_rows=2, min=10 |
| uniqueness | YES | ambiguous_rows=0, max=0 |
| coverage | YES | coverage=1.000, min=0.900 |
| stability | YES | max_targets_per_source=1, max=1 |
| marine_target | YES | ratio=1.000, min=1.000 |
| overall | FAIL | endpoint pairing acceptance gate |

## Direction Counts

- sales_to_input: 2

## Reason Counts

- deterministic: 2

## Dominant Stage Pair Counts

- fw->marine: 2
