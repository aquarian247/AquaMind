# FWSEA Endpoint Pairing Acceptance Gate

## Scope

- Component key: `D3FB15A0-71E5-4EEE-8CAE-39C7BE1DD484`
- Component id: `Stofnfiskur_Aug_2024_4_2024`
- Component population count: 183
- CSV directory: `/Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract`
- Expected direction: `sales_to_input`

## Endpoint Metrics

- InternalDelivery rows touching component populations: 10
- Rows with component populations on both sides: 0
- Candidate rows (single-side touch with counterpart populations): 10
- Deterministic rows: 10
- Ambiguous rows: 0
- Deterministic coverage: 1.000
- Marine-target deterministic rows: 10
- Marine-target deterministic ratio: 1.000
- Max targets per source endpoint: 1
- Sources with multiple targets: 0
- Incomplete-linkage fallback count (semantic summary): 0

## Gate Results

| Gate | Passed | Details |
| --- | --- | --- |
| evidence | YES | candidate_rows=10, min=4 |
| uniqueness | YES | ambiguous_rows=0, max=0 |
| coverage | YES | coverage=1.000, min=0.900 |
| stability | YES | max_targets_per_source=1, max=1 |
| marine_target | YES | ratio=1.000, min=1.000 |
| overall | PASS | endpoint pairing acceptance gate |

## Direction Counts

- sales_to_input: 10

## Reason Counts

- deterministic: 10

## Dominant Stage Pair Counts

- fw->marine: 10
