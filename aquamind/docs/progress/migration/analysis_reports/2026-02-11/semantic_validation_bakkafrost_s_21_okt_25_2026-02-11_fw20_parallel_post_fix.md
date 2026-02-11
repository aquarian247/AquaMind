# Semantic Migration Validation Report

- Component key: `829BEAC3-83F0-47F7-AFC3-140AE3A234ED`
- Batch: `Bakkafrost S-21 okt 25` (id=428)
- Populations: 13
- Window: 2025-10-28 13:17:54 → 2026-02-11 11:09:33.021699

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 0 | 0 | 0.00 |
| Feeding kg | 0.00 | 0.00 | 0.00 |
| Mortality events | 15 | 15 | 0.00 |
| Mortality count | 4068 | 4068 | 0.00 |
| Mortality biomass kg | 0.00 | 0.00 | 0.00 |
| Culling events | 0 | 0 | 0.00 |
| Culling count | 0 | 0 | 0.00 |
| Culling biomass kg | 0.00 | 0.00 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 0 | 0 | 0.00 |
| Growth samples | 0 | 0 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 4068
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 0/1 bridge-aware (0.0%), 1/1 entry-window (100.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 0
- Assignment zero-count rows (population_count <= 0): 8 total, 0 bridge-classified, 0 same-stage superseded-zero, 4 short-lived orphan-zero, 4 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 0.
- Fishgroup classification: 0 temporary bridge fishgroups, 5 real stage-entry fishgroups, 0 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 993681 | 0 | 993681 | 993681 | 1.0 | 1.0 | 2025-10-28 | 2025-10-30 | 5 | 5 | 0 | 5 | 5 |
| Fry | 0 | 0 | 0 | 0 | - | - | - | - | 0 | 0 | 0 | 0 | 8 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 993681 | 0 | -993681 | 0 | 0 | no | Entry window (no entry populations) | WARN: stage drop exceeds total known removals by 989613 |

### Fishgroup Classification Samples

- Real stage-entry fishgroup examples: `255.0002`, `255.0003`, `255.0004`, `255.0005`, `255.0006`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 13 | 13 | 100.0 | 0 | 0 | 0 |
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