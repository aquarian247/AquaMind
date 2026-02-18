# Semantic Migration Validation Report

- Component key: `EAC1F40B-4594-43FF-984C-E7E6FAC5CCFC`
- Batch: `AquaGen juni 25` (id=530)
- Populations: 41
- Window: 2025-06-18 16:26:10 → 2026-01-22 23:59:59.999999 (uncapped end 2026-02-17 16:18:04.555176, cap 2026-01-22 23:59:59.999999)

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 504 | 504 | 0.00 |
| Feeding kg | 1016.91 | 1016.91 | 0.00 |
| Mortality events | 655 | 653 | 2.00 |
| Mortality count | 160838 | 160838 | 0.00 |
| Mortality biomass kg | 0.00 | 35.74 | -35.74 |
| Culling events | 12 | 12 | 0.00 |
| Culling count | 19707 | 19707 | 0.00 |
| Culling biomass kg | 40620.60 | 40620.60 | 0.00 |
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

- Mortality biomass note: FishTalk source biomass is zero/missing for this batch; AquaMind mortality biomass is derived from status/assignment context. This row is informational and is not a regression gate criterion.

## Lifecycle Stage Sanity

- Mixed-batch composition rows: 0
- Known removal count (mortality + culling + escapes + harvest): 180545
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 2/2 bridge-aware (100.0%), 0/2 entry-window (0.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 2
- Assignment zero-count rows (population_count <= 0): 16 total, 16 bridge-classified, 0 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 12.
- Fishgroup classification: 18 temporary bridge fishgroups, 17 real stage-entry fishgroups, 18 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 383587 | 0 | 1774435 | 1774435 | 4.63 | 1.0 | 2025-06-18 | 2025-06-20 | 1 | 1 | 0 | 5 | 5 |
| Fry | 1695421 | 0 | 1695421 | 1695421 | 1.0 | 1.0 | 2025-09-19 | 2025-09-21 | 12 | 12 | 0 | 12 | 12 |
| Parr | 1011185 | 1514674 | 1514674 | 1782921 | 1.76 | 1.18 | 2025-12-10 | 2025-12-12 | 4 | 4 | 2 | 8 | 24 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1774435 | 489274 | -1285161 | 12 | 12 | yes | Bridge-aware (linked sources: 5); lineage graph fallback used | WARN: stage drop exceeds total known removals by 1104616 |
| Fry -> Parr | 324888 | 324888 | 0 | 4 | 4 | yes | Bridge-aware (linked sources: 8); lineage graph fallback used | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `252.0018`, `252.0019`, `252.0021`, `252.0022`, `252.0023`, `252.0024`, `252.0026`, `252.0027`, `252.0028`, `252.0029`
- Real stage-entry fishgroup examples: `252.0001`, `252.0006`, `252.0007`, `252.0008`, `252.0009`, `252.0010`, `252.0011`, `252.0012`, `252.0013`, `252.0014`
- Bridge fishgroups excluded from stage-entry windows: `252.0028`, `252.0029`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 41 | 41 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 1774435 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 17

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 5 | Hatchery:5 | S03 Norðtoftir:5 |
| SourcePopBefore -> SourcePopAfter | 12 | Hatchery:12 | S03 Norðtoftir:12 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 17 | 0 | Hatchery:17 | S03 Norðtoftir:17 | Unknown:17 |
| Reachable outside descendants | 28 | 0 | Hatchery:28 | S03 Norðtoftir:28 | Unknown:28 |

### Active Container Latest Holder Evidence

- For each currently active migrated assignment container, this shows the latest non-zero status holder in source data.
- Containers checked: 6; latest holder in selected component: 6; latest holder outside selected component: 0; unknown latest holder: 0.

| Container | Source container id | Component population | Latest holder population | Latest holder in selected component | Latest count | Latest biomass kg | Latest status time | Site | Prod stage |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| 801 | C0F3B240-CC70-4476-893A-D411FB51E61C | `4A56B456-7354-4BD8-BFE3-8F13F8EA954D` | `4A56B456-7354-4BD8-BFE3-8F13F8EA954D` | yes | 288673 | 4275.7 | 2026-01-22 00:00:00 | S03 Norðtoftir | Hatchery |
| 802 | 6CC24621-030E-4352-98EC-B59A9945B35B | `22E5C517-03F9-4E50-B363-D434BD6AAD88` | `22E5C517-03F9-4E50-B363-D434BD6AAD88` | yes | 199266 | 3617.05 | 2026-01-22 00:00:00 | S03 Norðtoftir | Hatchery |
| 803 | 35F54316-EB0D-43C9-A6C1-D805018AD9D4 | `8DB9AD13-4D03-4908-BD00-99F4B1BD49A9` | `8DB9AD13-4D03-4908-BD00-99F4B1BD49A9` | yes | 325468 | 4755.56 | 2026-01-22 00:00:00 | S03 Norðtoftir | Hatchery |
| 804 | 684837F1-02C2-4759-9EFA-E25E996CE25A | `488C714A-770B-4564-B591-5D5344419D26` | `488C714A-770B-4564-B591-5D5344419D26` | yes | 197778 | 3845.49 | 2026-01-22 00:00:00 | S03 Norðtoftir | Hatchery |
| 805 | 968B5094-265D-4ECB-ACDE-CD72467CB995 | `E02514D3-FAC8-49A5-9BA4-EDF2017637CA` | `E02514D3-FAC8-49A5-9BA4-EDF2017637CA` | yes | 300665 | 4724.48 | 2026-01-22 00:00:00 | S03 Norðtoftir | Hatchery |
| 806 | BA09C565-3DF5-4CB9-A55C-BD7FD1D26378 | `7CF2ADAB-BFC7-45F6-BD27-5E4CC342E097` | `7CF2ADAB-BFC7-45F6-BD27-5E4CC342E097` | yes | 202824 | 4006.73 | 2026-01-22 00:00:00 | S03 Norðtoftir | Hatchery |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)