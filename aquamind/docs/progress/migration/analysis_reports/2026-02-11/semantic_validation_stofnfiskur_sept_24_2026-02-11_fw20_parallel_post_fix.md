# Semantic Migration Validation Report

- Component key: `E9F7C414-399C-4F17-879F-087899496683`
- Batch: `Stofnfiskur sept 24` (id=427)
- Populations: 118
- Window: 2024-09-04 14:54:18 → 2026-02-11 11:07:43.024374

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 2902 | 2902 | 0.00 |
| Feeding kg | 240377.57 | 240377.57 | -0.00 |
| Mortality events | 3162 | 2986 | 176.00 |
| Mortality count | 296398 | 296398 | 0.00 |
| Mortality biomass kg | 0.00 | 1557.85 | -1557.85 |
| Culling events | 31 | 31 | 0.00 |
| Culling count | 117546 | 117546 | 0.00 |
| Culling biomass kg | 1479407.64 | 1479407.64 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 36 | 36 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 413944
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 4/4 bridge-aware (100.0%), 0/4 entry-window (0.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 4
- Assignment zero-count rows (population_count <= 0): 25 total, 17 bridge-classified, 0 same-stage superseded-zero, 5 short-lived orphan-zero, 3 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 42.
- Fishgroup classification: 39 temporary bridge fishgroups, 35 real stage-entry fishgroups, 39 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 1733842 | 0 | 1733842 | 1733842 | 1.0 | 1.0 | 2024-09-04 | 2024-09-06 | 12 | 12 | 0 | 12 | 12 |
| Fry | 1446319 | 0 | 1446319 | 1446319 | 1.0 | 1.0 | 2024-12-03 | 2024-12-05 | 12 | 12 | 0 | 12 | 12 |
| Parr | 1305548 | 0 | 1535148 | 3167146 | 2.43 | 2.06 | 2025-02-25 | 2025-02-27 | 6 | 6 | 1 | 27 | 44 |
| Smolt | 31597 | 0 | 242398 | 595151 | 18.84 | 2.46 | 2025-07-22 | 2025-07-24 | 3 | 3 | 2 | 20 | 20 |
| Post-Smolt | 281779 | 133762 | 685950 | 1692607 | 6.01 | 2.47 | 2025-09-09 | 2025-09-11 | 2 | 2 | 4 | 22 | 30 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1760000 | 146674 | -1613326 | 12 | 12 | yes | Bridge-aware (linked sources: 12); lineage graph fallback used | WARN: stage drop exceeds total known removals by 1199382 |
| Fry -> Parr | 146674 | 146674 | 0 | 6 | 6 | yes | Bridge-aware (linked sources: 12); lineage graph fallback used | OK |
| Parr -> Smolt | 37037 | 32133 | -4904 | 3 | 3 | yes | Bridge-aware (linked sources: 2); lineage graph fallback used | OK |
| Smolt -> Post-Smolt | 32133 | 32133 | 0 | 2 | 2 | yes | Bridge-aware (linked sources: 3); lineage graph fallback used | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `243.0026`, `243.0027`, `243.0028`, `243.0029`, `243.0030`, `243.0031`, `243.0033`, `243.0034`, `243.0035`, `243.0036`
- Real stage-entry fishgroup examples: `243.0002`, `243.0003`, `243.0004`, `243.0005`, `243.0006`, `243.0007`, `243.0008`, `243.0009`, `243.0010`, `243.0011`
- Bridge fishgroups excluded from stage-entry windows: `243.0033`, `243.0062`, `243.0064`, `243.0084`, `243.0085`, `243.0086`, `243.0087`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 118 | 118 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 1760000 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 53

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 12 | Hatchery:12 | S03 Norðtoftir:12 |
| SourcePopBefore -> SourcePopAfter | 41 | Hatchery:41 | S03 Norðtoftir:41 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 53 | 0 | Hatchery:53 | S03 Norðtoftir:53 | Unknown:53 |
| Reachable outside descendants | 66 | 0 | Hatchery:66 | S03 Norðtoftir:66 | Unknown:66 |

### Active Container Latest Holder Evidence

- For each currently active migrated assignment container, this shows the latest non-zero status holder in source data.
- Containers checked: 6; latest holder in selected component: 6; latest holder outside selected component: 0; unknown latest holder: 0.

| Container | Source container id | Component population | Latest holder population | Latest holder in selected component | Latest count | Latest biomass kg | Latest status time | Site | Prod stage |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| 1801 | 1FA0F0B4-625A-42AA-B8CC-17FF3EA3A8A2 | `FB0543E1-7C5E-404C-926B-C0D02C508D50` | `FB0543E1-7C5E-404C-926B-C0D02C508D50` | yes | 173781 | 28788.5 | 2025-10-31 00:00:00 | S03 Norðtoftir | Hatchery |
| 1802 | 8197B471-F78A-47B5-A21E-BFE8050DE65E | `3D809DA5-A0E1-4288-B4D1-FF452F65BBE0` | `3D809DA5-A0E1-4288-B4D1-FF452F65BBE0` | yes | 129743 | 32316.7 | 2025-10-31 00:00:00 | S03 Norðtoftir | Hatchery |
| 1803 | 1D403F77-D5CE-4B95-A74F-761E26288A30 | `B8A5C85A-FFA4-4A44-9091-948C858D43E5` | `B8A5C85A-FFA4-4A44-9091-948C858D43E5` | yes | 186960 | 24019.3 | 2025-10-31 00:00:00 | S03 Norðtoftir | Hatchery |
| 1804 | E444A0AE-CCBE-4693-97D2-6EA8FD98D096 | `052082DE-BC21-4AD3-99DB-39D1E37BD48C` | `052082DE-BC21-4AD3-99DB-39D1E37BD48C` | yes | 140709 | 27670.7 | 2025-10-31 00:00:00 | S03 Norðtoftir | Hatchery |
| 1806 | A1571731-C790-4D27-91C6-4C2F06D6498F | `BBB76C09-F23A-42E0-AFD6-1C47219235AF` | `BBB76C09-F23A-42E0-AFD6-1C47219235AF` | yes | 308680 | 79087.0 | 2025-10-31 00:00:00 | S03 Norðtoftir | Hatchery |
| 1807 | 04061AF2-5A2B-4370-AB19-E72F5F3AB289 | `D54D471D-5F79-483D-9115-992578DFC13C` | `D54D471D-5F79-483D-9115-992578DFC13C` | yes | 203852 | 77002.9 | 2025-10-31 00:00:00 | S03 Norðtoftir | Hatchery |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)