# Semantic Migration Validation Report

- Component key: `A538947B-1EDB-4165-AE2A-09B806B640F2`
- Batch: `Stofnfiskur Des 24` (id=534)
- Populations: 106
- Window: 2024-12-11 11:40:51 → 2026-01-22 23:59:59.999999 (uncapped end 2026-02-17 16:33:26.803356, cap 2026-01-22 23:59:59.999999)

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 2197 | 2197 | 0.00 |
| Feeding kg | 90126.31 | 90126.31 | -0.00 |
| Mortality events | 2236 | 2133 | 103.00 |
| Mortality count | 468516 | 468516 | 0.00 |
| Mortality biomass kg | 0.00 | 1837.63 | -1837.63 |
| Culling events | 29 | 29 | 0.00 |
| Culling count | 261901 | 261901 | 0.00 |
| Culling biomass kg | 10576350.70 | 10576350.70 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 27 | 27 | 0.00 |
| Growth samples | 12 | 12 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 730417
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 4/4 bridge-aware (100.0%), 0/4 entry-window (0.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 4
- Assignment zero-count rows (population_count <= 0): 12 total, 12 bridge-classified, 0 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 37.
- Fishgroup classification: 39 temporary bridge fishgroups, 33 real stage-entry fishgroups, 39 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 1761814 | 0 | 1761814 | 1761814 | 1.0 | 1.0 | 2024-12-11 | 2024-12-13 | 12 | 12 | 0 | 12 | 12 |
| Fry | 1721592 | 0 | 1721592 | 1721592 | 1.0 | 1.0 | 2025-03-05 | 2025-03-07 | 12 | 12 | 0 | 12 | 12 |
| Parr | 677338 | 0 | 1852208 | 5949024 | 8.78 | 3.21 | 2025-05-30 | 2025-06-01 | 4 | 4 | 4 | 39 | 51 |
| Smolt | 319415 | 0 | 1098566 | 1577182 | 4.94 | 1.44 | 2025-09-24 | 2025-09-26 | 3 | 3 | 4 | 19 | 19 |
| Post-Smolt | 189834 | 568699 | 769432 | 1183170 | 6.23 | 1.54 | 2025-12-23 | 2025-12-25 | 2 | 2 | 2 | 12 | 12 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1761814 | 293636 | -1468178 | 12 | 12 | yes | Bridge-aware (linked sources: 12); lineage graph fallback used | WARN: stage drop exceeds total known removals by 737761 |
| Fry -> Parr | 146817 | 146817 | 0 | 4 | 4 | yes | Bridge-aware (linked sources: 6); lineage graph fallback used | OK |
| Parr -> Smolt | 119291 | 89285 | -30006 | 3 | 3 | yes | Bridge-aware (linked sources: 3); lineage graph fallback used | OK |
| Smolt -> Post-Smolt | 57471 | 57471 | 0 | 2 | 2 | yes | Bridge-aware (linked sources: 2); lineage graph fallback used | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `244.0025`, `244.0026`, `244.0028`, `244.0029`, `244.0030`, `244.0031`, `244.0033`, `244.0034`, `244.0037`, `244.0038`
- Real stage-entry fishgroup examples: `244.0002`, `244.0003`, `244.0004`, `244.0005`, `244.0006`, `244.0007`, `244.0008`, `244.0009`, `244.0010`, `244.0011`
- Bridge fishgroups excluded from stage-entry windows: `244.0028`, `244.0029`, `244.0030`, `244.0031`, `244.0063`, `244.0064`, `244.0065`, `244.0067`, `244.0095`, `244.0096`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 106 | 106 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 1761814 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 48

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 12 | Hatchery:12 | S03 Norðtoftir:12 |
| SourcePopBefore -> SourcePopAfter | 36 | Hatchery:36 | S03 Norðtoftir:36 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 48 | 0 | Hatchery:48 | S03 Norðtoftir:48 | Unknown:48 |
| Reachable outside descendants | 64 | 0 | Hatchery:64 | S03 Norðtoftir:64 | Unknown:64 |

### Active Container Latest Holder Evidence

- For each currently active migrated assignment container, this shows the latest non-zero status holder in source data.
- Containers checked: 4; latest holder in selected component: 4; latest holder outside selected component: 0; unknown latest holder: 0.

| Container | Source container id | Component population | Latest holder population | Latest holder in selected component | Latest count | Latest biomass kg | Latest status time | Site | Prod stage |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| 1805 | B819646E-DB90-4496-B47D-43ABAB1CC08E | `902F2624-73F8-4548-B84F-4A3024C94F95` | `902F2624-73F8-4548-B84F-4A3024C94F95` | yes | 108246 | 34514.1 | 2026-01-22 00:00:00 | S03 Norðtoftir | Hatchery |
| 1806 | A1571731-C790-4D27-91C6-4C2F06D6498F | `D1F236C9-A353-4FA6-B378-4BA85F580786` | `D1F236C9-A353-4FA6-B378-4BA85F580786` | yes | 180374 | 45436.6 | 2026-01-22 00:00:00 | S03 Norðtoftir | Hatchery |
| 1807 | 04061AF2-5A2B-4370-AB19-E72F5F3AB289 | `12269189-DD54-4785-8DD8-A87EDE723B9E` | `12269189-DD54-4785-8DD8-A87EDE723B9E` | yes | 170371 | 34228.9 | 2026-01-22 00:00:00 | S03 Norðtoftir | Hatchery |
| 1808 | 641B7238-AC50-4FB8-8DE7-4381FF67FECD | `9105E976-547D-4D24-82AE-7806E9EC0840` | `9105E976-547D-4D24-82AE-7806E9EC0840` | yes | 109708 | 45931.5 | 2026-01-22 00:00:00 | S03 Norðtoftir | Hatchery |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)