# Semantic Migration Validation Report

- Component key: `81AC7D6F-3C81-4F36-9875-881C828F62E3`
- Batch: `Summar 2024` (id=356)
- Populations: 106
- Window: 2024-08-06 16:31:08 → 2025-10-15 00:42:20

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 5273 | 5273 | 0.00 |
| Feeding kg | 8772000.00 | 8772000.00 | 0.00 |
| Mortality events | 11320 | 11199 | 121.00 |
| Mortality count | 99828 | 99828 | 0.00 |
| Mortality biomass kg | 0.00 | 279861.47 | -279861.47 |
| Culling events | 0 | 0 | 0.00 |
| Culling count | 0 | 0 | 0.00 |
| Culling biomass kg | 0.00 | 0.00 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 676 | 676 | 0.00 |
| Growth samples | 0 | 0 | 0.00 |
| Health journal entries | 0 | 0 | 0.00 |
| Lice samples | 443 | 427 | 16.00 |
| Lice data rows | 1472 | 1472 | 0.00 |
| Lice total count | 8036 | 8036 | 0.00 |
| Fish sampled (lice) | 8893 | 8573 | 320.00 |
| Environmental readings | n/a (sqlite) | 36204 | n/a |
| Harvest rows | 32 | 32 | 0.00 |
| Harvest events | n/a | 32 | n/a |
| Harvest count | 1151086 | 1151086 | 0.00 |
| Harvest live kg | 8272780700.00 | 8272780700.00 | 0.00 |
| Harvest gutted kg | 6783680700.00 | 6783680700.00 | 0.00 |

## Lifecycle Stage Sanity

- Mixed-batch composition rows: 0
- Known removal count (mortality + culling + escapes + harvest): 1250914
- Stage-entry window used for transition sanity: 2 day(s)
- Assignment zero-count rows (population_count <= 0): 74 total, 13 bridge-classified, 61 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 46.
- Fishgroup classification: 13 temporary bridge fishgroups, 1 real stage-entry fishgroups, 13 temporary bridge populations.

| Stage | Entry population | Full summed population | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Adult | 55406 | 1260001 | 2025-08-08 | 2025-08-10 | 1 | 1 | 0 | 32 | 106 |

- Transition deltas below use fishgroup bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `241.0003`, `241.0008`, `241.0011`, `241.0015`, `241.0027`, `241.0036`, `241.0040`, `241.0042`, `241.0046`, `241.0049`
- Real stage-entry fishgroup examples: `241.0005`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 106 | 106 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | FAIL | Assignments with population_count <= 0 and not classified as temporary bridge: 61 (threshold: 2) |
- Overall gate result: FAIL (enforced)