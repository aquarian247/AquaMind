# FWSEA Endpoint Pairing Acceptance Gate

## Scope

- Component key: `65370D45-A30A-4810-B8F0-06FE2DB4A001`
- Component id: `Benchmark_Gen._Septembur_2024_3_2024`
- Component population count: 162
- CSV directory: `/Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract`
- Expected direction: `sales_to_input`

## Endpoint Metrics

- InternalDelivery rows touching component populations: 15
- Rows with component populations on both sides: 0
- Candidate rows (single-side touch with counterpart populations): 15
- Deterministic rows: 13
- Ambiguous rows: 2
- Deterministic coverage: 0.867
- Marine-target deterministic rows: 13
- Marine-target deterministic ratio: 1.000
- Max targets per source endpoint: 1
- Sources with multiple targets: 0
- Incomplete-linkage fallback count (semantic summary): 0

## Gate Results

| Gate | Passed | Details |
| --- | --- | --- |
| evidence | YES | candidate_rows=15, min=10 |
| uniqueness | NO | ambiguous_rows=2, max=0 |
| coverage | NO | coverage=0.867, min=0.900 |
| stability | YES | max_targets_per_source=1, max=1 |
| marine_target | YES | ratio=1.000, min=1.000 |
| overall | FAIL | endpoint pairing acceptance gate |

## Direction Counts

- sales_to_input: 15

## Reason Counts

- deterministic: 13
- source_candidate_count_out_of_bounds: 2

## Dominant Stage Pair Counts

- fw->marine: 15
