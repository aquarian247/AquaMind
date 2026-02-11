# FWSEA Endpoint Pairing Acceptance Gate

## Scope

- Component key: `B884F78F-1E92-49C0-AE28-39DFC2E18C01`
- Component id: `Stofnfiskur_S-21_nov23_5_2023`
- Component population count: 288
- CSV directory: `/Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract`
- Expected direction: `sales_to_input`

## Endpoint Metrics

- InternalDelivery rows touching component populations: 12
- Rows with component populations on both sides: 0
- Candidate rows (single-side touch with counterpart populations): 12
- Deterministic rows: 11
- Ambiguous rows: 1
- Deterministic coverage: 0.917
- Marine-target deterministic rows: 11
- Marine-target deterministic ratio: 1.000
- Max targets per source endpoint: 1
- Sources with multiple targets: 0

## Gate Results

| Gate | Passed | Details |
| --- | --- | --- |
| evidence | YES | candidate_rows=12, min=10 |
| uniqueness | NO | ambiguous_rows=1, max=0 |
| coverage | YES | coverage=0.917, min=0.900 |
| stability | YES | max_targets_per_source=1, max=1 |
| marine_target | YES | ratio=1.000, min=1.000 |
| overall | FAIL | endpoint pairing acceptance gate |

## Direction Counts

- sales_to_input: 12

## Reason Counts

- deterministic: 11
- source_candidate_count_out_of_bounds: 1

## Dominant Stage Pair Counts

- fw->marine: 12
