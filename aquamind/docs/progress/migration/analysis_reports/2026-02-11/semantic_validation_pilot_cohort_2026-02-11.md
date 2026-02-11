# Semantic Validation Pilot Cohort Regression Check

- Components checked: 1
- Stage-entry window days: 2
- CSV extract: `/Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract`
- Non-bridge zero-assignment threshold: 2
- FWSEA endpoint gates: enabled (enforce=False)
- FWSEA endpoint thresholds: direction=sales_to_input, source<= 2, target<= 1, coverage>= 0.90, ambiguous<= 0, max-targets/source<= 1, candidate-rows>= 10
- Aggregate transition basis usage: 0/0 bridge-aware (0.0%), 0/0 entry-window (0.0%).

| Batch | Component key | Transitions | Bridge-aware | Entry-window | Entry-window rate % | Positive delta alerts | Zero-count transfer actions | Non-bridge zero assignments | Gates |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Stofnfiskur S-21 nov23 | `B884F78F-1E92-49C0-AE28-39DFC2E18C01` | 0 | 0 | 0 | 0.0 | 0 | 0 | 0 | FAIL |

## Aggregate Totals

- Total transitions: 0
- Bridge-aware transitions: 0
- Entry-window transitions: 0
- Positive transition alerts (without mixed-batch rows): 0
- Zero-count transfer actions: 0
- Non-bridge zero assignments: 0

## Entry-window Reason Breakdown

| Reason | Transition count |
| --- | ---: |

## FWSEA Endpoint Gate Results

| Batch | Component key | Candidate rows | Deterministic rows | Coverage % | Max targets/source | Gate | Report |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| Stofnfiskur S-21 nov23 | `B884F78F-1E92-49C0-AE28-39DFC2E18C01` | 12 | 11 | 91.7 | 1 | FAIL | `fwsea_endpoint_gate_Stofnfiskur_S_21_nov23_5_2023_2026-02-11.md` |

## Overall Result

- Regression check: FAIL (components with failures: Stofnfiskur S-21 nov23)