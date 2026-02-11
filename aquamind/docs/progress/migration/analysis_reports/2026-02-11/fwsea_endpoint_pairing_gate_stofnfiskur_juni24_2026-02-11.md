# FWSEA Endpoint Pairing Acceptance Gate

## Scope

- Component key: `EDF931F2-51CC-4A10-9002-128E7BF8067C`
- Component id: `Stofnfiskur_Juni_24_2_2024`
- Component population count: 145
- CSV directory: `scripts/migration/data/extract`
- Expected direction: `sales_to_input`

## Endpoint Metrics

- InternalDelivery rows touching component populations: 15
- Rows with component populations on both sides: 0
- Candidate rows (single-side touch with counterpart populations): 15
- Deterministic rows: 15
- Ambiguous rows: 0
- Deterministic coverage: 1.000
- Marine-target deterministic rows: 15
- Marine-target deterministic ratio: 1.000
- Max targets per source endpoint: 1
- Sources with multiple targets: 0

## Gate Results

| Gate | Passed | Details |
| --- | --- | --- |
| evidence | YES | candidate_rows=15, min=10 |
| uniqueness | YES | ambiguous_rows=0, max=0 |
| coverage | YES | coverage=1.000, min=0.900 |
| stability | YES | max_targets_per_source=1, max=1 |
| marine_target | YES | ratio=1.000, min=1.000 |
| overall | PASS | endpoint pairing acceptance gate |

## Direction Counts

- sales_to_input: 15

## Reason Counts

- deterministic: 15

## Dominant Stage Pair Counts

- fw->marine: 15
