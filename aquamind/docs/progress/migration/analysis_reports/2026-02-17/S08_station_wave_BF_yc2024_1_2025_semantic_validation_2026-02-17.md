# Semantic Migration Validation Report

- Component key: `F16773A9-D3CA-4079-9B51-F36F610DFAE6`
- Batch: `BF yc2024` (id=542)
- Populations: 15
- Window: 2025-02-15 08:23:57 → 2025-07-21 18:31:04

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 173 | 173 | 0.00 |
| Feeding kg | 10244.49 | 10244.49 | 0.00 |
| Mortality events | 286 | 260 | 26.00 |
| Mortality count | 1101 | 1101 | 0.00 |
| Mortality biomass kg | 0.00 | 158.81 | -158.81 |
| Culling events | 2 | 2 | 0.00 |
| Culling count | 309 | 309 | 0.00 |
| Culling biomass kg | 22800.00 | 22800.00 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 2 | 2 | 0.00 |
| Growth samples | 5 | 5 | 0.00 |
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

- Mortality biomass note: FishTalk source biomass is zero/missing for this batch; AquaMind mortality biomass is derived from status/assignment context. This row is informational and is not a regression gate criterion.

## Lifecycle Stage Sanity

- Mixed-batch composition rows: 0
- Known removal count (mortality + culling + escapes + harvest): 1410
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 1/1 bridge-aware (100.0%), 0/1 entry-window (0.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 0
- Assignment zero-count rows (population_count <= 0): 5 total, 5 bridge-classified, 0 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 7.
- Fishgroup classification: 5 temporary bridge fishgroups, 5 real stage-entry fishgroups, 5 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Smolt | 20756 | 0 | 50380 | 77242 | 3.72 | 1.53 | 2025-02-15 | 2025-02-17 | 3 | 3 | 0 | 8 | 13 |
| Post-Smolt | 45232 | 0 | 45232 | 45232 | 1.0 | 1.0 | 2025-06-05 | 2025-06-07 | 2 | 2 | 0 | 2 | 2 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Smolt -> Post-Smolt | 26514 | 14236 | -12278 | 2 | 2 | yes | Bridge-aware (direct edge linkage; linked sources: 2) | WARN: stage drop exceeds total known removals by 10868 |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `251.0005`, `251.0007`, `251.0008`, `251.0010`, `ACA.0002`
- Real stage-entry fishgroup examples: `251.0002`, `251.0003`, `251.0006`, `ACA.0001`, `ACA.0004`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 15 | 15 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 1

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 0 | - | - |
| SourcePopBefore -> SourcePopAfter | 1 | Hatchery:1 | S08 Gjógv:1 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 1 | 0 | Hatchery:1 | S08 Gjógv:1 | Unknown:1 |
| Reachable outside descendants | 2 | 0 | Hatchery:2 | S08 Gjógv:2 | Unknown:2 |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)