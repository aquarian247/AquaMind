# Semantic Migration Validation Report

- Component key: `251B661F-E0A6-4AD0-9B59-40A6CE1ADC86`
- Batch: `FT-251B661F-05` (id=1309)
- Populations: 109
- Window: 2024-03-10 14:46:12 → 2025-04-29 20:27:48

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 3937 | 0 | 3937.00 |
| Feeding kg | 8565997.86 | 0.00 | 8565997.86 |
| Mortality events | 7206 | 0 | 7206.00 |
| Mortality count | 112448 | 0 | 112448.00 |
| Mortality biomass kg | 0.00 | 0.00 | 0.00 |
| Culling events | 0 | 0 | 0.00 |
| Culling count | 0 | 0 | 0.00 |
| Culling biomass kg | 0.00 | 0.00 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 593 | 0 | 593.00 |
| Growth samples | 0 | 0 | 0.00 |
| Health journal entries | 0 | 0 | 0.00 |
| Lice samples | 376 | 0 | 376.00 |
| Lice data rows | 1406 | 0 | 1406.00 |
| Lice total count | 12776 | 0 | 12776.00 |
| Fish sampled (lice) | 7444 | 0 | 7444.00 |
| Environmental readings | n/a (sqlite) | 0 | n/a |
| Harvest rows | 42 | 0 | 42.00 |
| Harvest events | n/a | 0 | n/a |
| Harvest count | 1253113 | 0 | 1253113.00 |
| Harvest live kg | 7718064700.00 | 0.00 | 7718064700.00 |
| Harvest gutted kg | 6328811200.00 | 0.00 | 6328811200.00 |

## Lifecycle Stage Sanity

- Mixed-batch composition rows: 0
- Known removal count (mortality + culling + escapes + harvest): 1365561
- Stage-entry window used for transition sanity: 2 day(s)
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 0
- Assignment zero-count rows (population_count <= 0): 21 total, 5 bridge-classified, 16 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 0.
- Fishgroup classification: 7 temporary bridge fishgroups, 1 real stage-entry fishgroups, 7 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Adult | 100622 | 0 | 1715223 | 5909860 | 58.73 | 3.45 | 2024-03-10 | 2024-03-12 | 1 | 1 | 0 | 88 | 109 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `241.0009`, `241.0011`, `241.0013`, `241.0023`, `241.0025`, `241.0031`, `241.0051`
- Real stage-entry fishgroup examples: `241.0001`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 109 | 109 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: YES
- Direct external destination populations (any role): 5

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 0 | - | - |
| SourcePopBefore -> SourcePopAfter | 5 | MarineSite:5 | A04 Lambavík:5 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 5 | 5 | MarineSite:5 | A04 Lambavík:5 | North:5 |
| Reachable outside descendants | 5 | 5 | MarineSite:5 | A04 Lambavík:5 | North:5 |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)