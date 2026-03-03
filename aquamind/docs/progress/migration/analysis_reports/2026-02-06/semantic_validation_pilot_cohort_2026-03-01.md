# Semantic Validation Pilot Cohort Regression Check

- Components checked: 5
- Stage-entry window days: 2
- CSV extract: `/Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract`
- Non-bridge zero-assignment threshold: 2
- FWSEA endpoint gates: disabled (enforce=False)
- Aggregate transition basis usage: 4/11 bridge-aware (36.4%), 7/11 entry-window (63.6%).

| Batch | Component key | Transitions | Bridge-aware | Entry-window | Entry-window rate % | Positive delta alerts | Zero-count transfer actions | Non-bridge zero assignments | Gates |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| SF NOV 23 | `FA8EA452-AFE1-490D-B236-0150415B6E6F` | 3 | 2 | 1 | 33.3 | 0 | 0 | 1 | PASS |
| Stofnfiskur S-21 nov23 | `B884F78F-1E92-49C0-AE28-39DFC2E18C01` | 4 | 2 | 2 | 50.0 | 0 | 0 | 2 | PASS |
| Benchmark Gen. Juni 2024 | `5DC4DA59-A891-4BBB-BB2E-0CC95C633F20` | 4 | 0 | 4 | 100.0 | 0 | 0 | 106 | FAIL |
| Summar 2024 | `81AC7D6F-3C81-4F36-9875-881C828F62E3` | 0 | 0 | 0 | 0.0 | 0 | 0 | 61 | FAIL |
| Vár 2024 | `251B661F-E0A6-4AD0-9B59-40A6CE1ADC86` | 0 | 0 | 0 | 0.0 | 0 | 0 | 60 | FAIL |

## Aggregate Totals

- Total transitions: 11
- Bridge-aware transitions: 4
- Entry-window transitions: 7
- Positive transition alerts (without mixed-batch rows): 0
- Zero-count transfer actions: 0
- Non-bridge zero assignments: 230

## Entry-window Reason Breakdown

| Reason | Transition count |
| --- | ---: |
| incomplete_linkage | 5 |
| bridge_aware | 4 |
| no_bridge_path | 2 |

## Overall Result

- Regression check: FAIL (components with failures: Benchmark Gen. Juni 2024, SF NOV 23, Stofnfiskur S-21 nov23, Summar 2024, Vár 2024)