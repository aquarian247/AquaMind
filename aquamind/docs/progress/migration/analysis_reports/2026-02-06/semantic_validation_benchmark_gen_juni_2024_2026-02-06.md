# Semantic Migration Validation Report

- Component key: `5DC4DA59-A891-4BBB-BB2E-0CC95C633F20`
- Batch: `FT-5DC4DA59-A03` (id=1307)
- Populations: 359
- Window: 2024-06-13 07:33:41 → 2025-11-10 14:47:52

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 5212 | 0 | 5212.00 |
| Feeding kg | 1312139.56 | 0.00 | 1312139.56 |
| Mortality events | 6784 | 0 | 6784.00 |
| Mortality count | 535109 | 0 | 535109.00 |
| Mortality biomass kg | 0.00 | 0.00 | 0.00 |
| Culling events | 25 | 0 | 25.00 |
| Culling count | 137377 | 0 | 137377.00 |
| Culling biomass kg | 4242656.00 | 0.00 | 4242656.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 122 | 0 | 122.00 |
| Growth samples | 607 | 0 | 607.00 |
| Health journal entries | 0 | 0 | 0.00 |
| Lice samples | 0 | 0 | 0.00 |
| Lice data rows | 0 | 0 | 0.00 |
| Lice total count | 0 | 0 | 0.00 |
| Fish sampled (lice) | 0 | 0 | 0.00 |
| Environmental readings | n/a (sqlite) | 0 | n/a |
| Harvest rows | 0 | 0 | 0.00 |
| Harvest events | n/a | 0 | n/a |
| Harvest count | 0 | 0 | 0.00 |
| Harvest live kg | 0.00 | 0.00 | 0.00 |
| Harvest gutted kg | 0.00 | 0.00 | 0.00 |

## Lifecycle Stage Sanity

- Mixed-batch composition rows: 0
- Known removal count (mortality + culling + escapes + harvest): 672486
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 2/2 bridge-aware (100.0%), 0/2 entry-window (0.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 2
- Assignment zero-count rows (population_count <= 0): 48 total, 43 bridge-classified, 5 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 0.
- Fishgroup classification: 123 temporary bridge fishgroups, 53 real stage-entry fishgroups, 123 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 3500000 | 0 | 3500000 | 3500000 | 1.0 | 1.0 | 2024-06-13 | 2024-06-15 | 39 | 39 | 0 | 39 | 39 |
| Smolt | 3387493 | 0 | 5755622 | 34078287 | 10.06 | 5.92 | 2024-09-04 | 2024-09-06 | 12 | 12 | 0 | 268 | 316 |
| Post-Smolt | 169724 | 0 | 126916 | 239040 | 1.41 | 1.88 | 2025-11-08 | 2025-11-10 | 2 | 2 | 0 | 4 | 4 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Smolt | 1166664 | 89748 | -1076916 | 12 | 12 | yes | Bridge-aware (linked sources: 13); lineage graph fallback used | WARN: stage drop exceeds total known removals by 404430 |
| Smolt -> Post-Smolt | 8594 | 6113 | -2481 | 2 | 2 | yes | Bridge-aware (linked sources: 2); lineage graph fallback used | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `242.0052`, `242.0053`, `242.0054`, `242.0055`, `242.0056`, `242.0057`, `242.0058`, `242.0059`, `242.0060`, `242.0061`
- Real stage-entry fishgroup examples: `242.0002`, `242.0003`, `242.0004`, `242.0005`, `242.0006`, `242.0007`, `242.0008`, `242.0009`, `242.0010`, `242.0011`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 359 | 359 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 3500000 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 100

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 39 | Hatchery:39 | S24 Strond:39 |
| SourcePopBefore -> SourcePopAfter | 61 | Hatchery:61 | S24 Strond:61 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 100 | 0 | Hatchery:100 | S24 Strond:100 | Unknown:100 |
| Reachable outside descendants | 227 | 0 | Hatchery:227 | S24 Strond:227 | Unknown:227 |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)