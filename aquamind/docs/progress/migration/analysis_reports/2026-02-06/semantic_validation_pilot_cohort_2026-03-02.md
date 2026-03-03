# Semantic Validation Pilot Cohort Regression Check

- Components checked: 5
- Stage-entry window days: 2
- CSV extract: `/Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract`
- Non-bridge zero-assignment threshold: 2
- FWSEA endpoint gates: disabled (enforce=False)
- Aggregate transition basis usage: 5/6 bridge-aware (83.3%), 1/6 entry-window (16.7%).

| Batch | Component key | Transitions | Bridge-aware | Entry-window | Entry-window rate % | Positive delta alerts | Zero-count transfer actions | Non-bridge zero assignments | Gates |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| SF NOV 23 | `FA8EA452-AFE1-490D-B236-0150415B6E6F` | 3 | 2 | 1 | 33.3 | 0 | 0 | 0 | PASS |
| Stofnfiskur S-21 nov23 | `B884F78F-1E92-49C0-AE28-39DFC2E18C01` | 1 | 1 | 0 | 0.0 | 0 | 0 | 0 | PASS |
| Benchmark Gen. Juni 2024 | `5DC4DA59-A891-4BBB-BB2E-0CC95C633F20` | 2 | 2 | 0 | 0.0 | 0 | 0 | 0 | PASS |
| Summar 2024 | `81AC7D6F-3C81-4F36-9875-881C828F62E3` | 0 | 0 | 0 | 0.0 | 0 | 0 | 0 | PASS |
| Vár 2024 | `251B661F-E0A6-4AD0-9B59-40A6CE1ADC86` | 0 | 0 | 0 | 0.0 | 0 | 0 | 0 | PASS |

## Aggregate Totals

- Total transitions: 6
- Bridge-aware transitions: 5
- Entry-window transitions: 1
- Positive transition alerts (without mixed-batch rows): 0
- Zero-count transfer actions: 0
- Non-bridge zero assignments: 0

## Entry-window Reason Breakdown

| Reason | Transition count |
| --- | ---: |
| bridge_aware | 5 |
| incomplete_linkage | 1 |

## Overall Result

- Regression check: PASS