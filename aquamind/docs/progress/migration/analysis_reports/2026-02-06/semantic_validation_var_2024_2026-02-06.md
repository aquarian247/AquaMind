# Semantic Migration Validation Report

- Component key: `251B661F-E0A6-4AD0-9B59-40A6CE1ADC86`
- Batch: `Vár 2024` (id=357)
- Populations: 109
- Window: 2024-03-10 14:46:12 → 2025-04-29 20:27:48

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 3937 | 3937 | 0.00 |
| Feeding kg | 8565997.86 | 8565997.86 | 0.00 |
| Mortality events | 7206 | 7131 | 75.00 |
| Mortality count | 112448 | 112448 | 0.00 |
| Mortality biomass kg | 0.00 | 283231.32 | -283231.32 |
| Culling events | 0 | 0 | 0.00 |
| Culling count | 0 | 0 | 0.00 |
| Culling biomass kg | 0.00 | 0.00 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 593 | 593 | 0.00 |
| Growth samples | 0 | 0 | 0.00 |
| Health journal entries | 0 | 0 | 0.00 |
| Lice samples | 376 | 372 | 4.00 |
| Lice data rows | 1406 | 1406 | 0.00 |
| Lice total count | 12776 | 12776 | 0.00 |
| Fish sampled (lice) | 7444 | 7381 | 63.00 |
| Environmental readings | n/a (sqlite) | 51855 | n/a |
| Harvest rows | 42 | 42 | 0.00 |
| Harvest events | n/a | 42 | n/a |
| Harvest count | 1253113 | 1253113 | 0.00 |
| Harvest live kg | 7718064700.00 | 7718064700.00 | 0.00 |
| Harvest gutted kg | 6328811200.00 | 6328811200.00 | 0.00 |

## Lifecycle Stage Sanity

- Mixed-batch composition rows: 0
- Known removal count (mortality + culling + escapes + harvest): 1365561
- Stage-entry window used for transition sanity: 2 day(s)
- Assignment zero-count rows (population_count <= 0): 67 total, 7 bridge-classified, 60 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 52.
- Fishgroup classification: 7 temporary bridge fishgroups, 1 real stage-entry fishgroups, 7 temporary bridge populations.

| Stage | Entry population | Full summed population | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Adult | 46298 | 1309647 | 2025-02-28 | 2025-03-02 | 1 | 1 | 0 | 42 | 109 |

- Transition deltas below use fishgroup bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `241.0009`, `241.0011`, `241.0013`, `241.0023`, `241.0025`, `241.0031`, `241.0051`
- Real stage-entry fishgroup examples: `241.0035`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 109 | 109 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | FAIL | Assignments with population_count <= 0 and not classified as temporary bridge: 60 (threshold: 2) |
- Overall gate result: FAIL (enforced)