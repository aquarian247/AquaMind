# FWSEA Endpoint Pairing Acceptance Gate

## Scope

- Component key: `829BEAC3-83F0-47F7-AFC3-140AE3A234ED`
- Component id: `Bakkafrost_S-21_okt_25_5_2025`
- Component population count: 13
- CSV directory: `/Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract`
- Expected direction: `sales_to_input`

## Endpoint Metrics

- InternalDelivery rows touching component populations: 0
- Rows with component populations on both sides: 0
- Candidate rows (single-side touch with counterpart populations): 0
- Deterministic rows: 0
- Ambiguous rows: 0
- Deterministic coverage: 0.000
- Marine-target deterministic rows: 0
- Marine-target deterministic ratio: 0.000
- Max targets per source endpoint: 0
- Sources with multiple targets: 0
- Incomplete-linkage fallback count (semantic summary): 0

## Gate Results

| Gate | Passed | Details |
| --- | --- | --- |
| evidence | NO | candidate_rows=0, min=4 |
| uniqueness | YES | ambiguous_rows=0, max=0 |
| coverage | NO | coverage=0.000, min=0.900 |
| stability | YES | max_targets_per_source=0, max=1 |
| marine_target | NO | ratio=0.000, min=1.000 |
| overall | FAIL | endpoint pairing acceptance gate |

## Direction Counts


## Reason Counts


## Dominant Stage Pair Counts

