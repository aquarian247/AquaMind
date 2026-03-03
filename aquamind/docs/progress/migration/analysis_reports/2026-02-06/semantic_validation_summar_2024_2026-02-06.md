# Semantic Migration Validation Report

- Component key: `81AC7D6F-3C81-4F36-9875-881C828F62E3`
- Batch: `FT-81AC7D6F-13` (id=1308)
- Populations: 106
- Window: 2024-08-06 16:31:08 → 2025-10-15 00:42:20

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 5273 | 0 | 5273.00 |
| Feeding kg | 8772000.00 | 0.00 | 8772000.00 |
| Mortality events | 11320 | 0 | 11320.00 |
| Mortality count | 99828 | 0 | 99828.00 |
| Mortality biomass kg | 0.00 | 0.00 | 0.00 |
| Culling events | 0 | 0 | 0.00 |
| Culling count | 0 | 0 | 0.00 |
| Culling biomass kg | 0.00 | 0.00 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 676 | 0 | 676.00 |
| Growth samples | 0 | 0 | 0.00 |
| Health journal entries | 0 | 0 | 0.00 |
| Lice samples | 443 | 0 | 443.00 |
| Lice data rows | 1472 | 0 | 1472.00 |
| Lice total count | 8036 | 0 | 8036.00 |
| Fish sampled (lice) | 8893 | 0 | 8893.00 |
| Environmental readings | n/a (sqlite) | 0 | n/a |
| Harvest rows | 32 | 0 | 32.00 |
| Harvest events | n/a | 0 | n/a |
| Harvest count | 1151086 | 0 | 1151086.00 |
| Harvest live kg | 8272780700.00 | 0.00 | 8272780700.00 |
| Harvest gutted kg | 6783680700.00 | 0.00 | 6783680700.00 |

## Lifecycle Stage Sanity

- Mixed-batch composition rows: 0
- Known removal count (mortality + culling + escapes + harvest): 1250914
- Stage-entry window used for transition sanity: 2 day(s)
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 0
- Assignment zero-count rows (population_count <= 0): 49 total, 12 bridge-classified, 37 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 0.
- Fishgroup classification: 13 temporary bridge fishgroups, 4 real stage-entry fishgroups, 13 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Adult | 354287 | 0 | 1435846 | 3049991 | 8.61 | 2.12 | 2024-08-06 | 2024-08-08 | 4 | 4 | 0 | 57 | 106 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `241.0003`, `241.0008`, `241.0011`, `241.0015`, `241.0027`, `241.0036`, `241.0040`, `241.0042`, `241.0046`, `241.0049`
- Real stage-entry fishgroup examples: `241.0005`, `241.0010`, `241.0017`, `241.0018`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 106 | 106 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 0

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 0 | - | - |
| SourcePopBefore -> SourcePopAfter | 0 | - | - |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 0 | 0 | - | - | - |
| Reachable outside descendants | 0 | 0 | - | - | - |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)