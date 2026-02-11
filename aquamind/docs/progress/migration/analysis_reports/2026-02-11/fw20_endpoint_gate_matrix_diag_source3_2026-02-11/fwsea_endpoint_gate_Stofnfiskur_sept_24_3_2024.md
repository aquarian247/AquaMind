# FWSEA Endpoint Pairing Acceptance Gate

## Scope

- Component key: `E9F7C414-399C-4F17-879F-087899496683`
- Component id: `Stofnfiskur_sept_24_3_2024`
- Component population count: 118
- CSV directory: `/Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract`
- Expected direction: `sales_to_input`

## Endpoint Metrics

- InternalDelivery rows touching component populations: 5
- Rows with component populations on both sides: 0
- Candidate rows (single-side touch with counterpart populations): 4
- Deterministic rows: 4
- Ambiguous rows: 0
- Deterministic coverage: 1.000
- Marine-target deterministic rows: 4
- Marine-target deterministic ratio: 1.000
- Max targets per source endpoint: 1
- Sources with multiple targets: 0
- Incomplete-linkage fallback count (semantic summary): 0

## Gate Results

| Gate | Passed | Details |
| --- | --- | --- |
| evidence | NO | candidate_rows=4, min=10 |
| uniqueness | YES | ambiguous_rows=0, max=0 |
| coverage | YES | coverage=1.000, min=0.900 |
| stability | YES | max_targets_per_source=1, max=1 |
| marine_target | YES | ratio=1.000, min=1.000 |
| overall | FAIL | endpoint pairing acceptance gate |

## Direction Counts

- sales_to_input: 5

## Reason Counts

- deterministic: 4
- no_counterpart_populations: 1

## Dominant Stage Pair Counts

- fw->marine: 4
