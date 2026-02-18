# Semantic Migration Validation Report

- Component key: `D8EEC9E7-59AA-41A8-9D26-0BD881B510FC`
- Batch: `AquaGen Mars 25` (id=529)
- Populations: 68
- Window: 2025-03-19 16:32:24 → 2026-01-22 23:59:59.999999 (uncapped end 2026-02-17 16:15:24.076753, cap 2026-01-22 23:59:59.999999)

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 1726 | 1726 | 0.00 |
| Feeding kg | 29697.49 | 29697.49 | 0.00 |
| Mortality events | 1794 | 1780 | 14.00 |
| Mortality count | 246502 | 246502 | 0.00 |
| Mortality biomass kg | 0.00 | 330.33 | -330.33 |
| Culling events | 21 | 21 | 0.00 |
| Culling count | 123250 | 123250 | 0.00 |
| Culling biomass kg | 997881.40 | 997881.40 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 0 | 0 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 369752
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 3/3 bridge-aware (100.0%), 0/3 entry-window (0.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 3
- Assignment zero-count rows (population_count <= 0): 16 total, 16 bridge-classified, 0 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 25.
- Fishgroup classification: 21 temporary bridge fishgroups, 25 real stage-entry fishgroups, 21 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 1751479 | 0 | 1751479 | 1751479 | 1.0 | 1.0 | 2025-03-19 | 2025-03-21 | 5 | 5 | 0 | 5 | 5 |
| Fry | 1707791 | 0 | 1707791 | 1707791 | 1.0 | 1.0 | 2025-06-06 | 2025-06-08 | 12 | 12 | 0 | 12 | 12 |
| Parr | 737402 | 0 | 1868627 | 4431128 | 6.01 | 2.37 | 2025-09-12 | 2025-09-14 | 4 | 4 | 2 | 27 | 43 |
| Smolt | 397923 | 570347 | 570347 | 585989 | 1.47 | 1.03 | 2026-01-13 | 2026-01-15 | 4 | 4 | 0 | 8 | 8 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1751479 | 1707791 | -43688 | 12 | 12 | yes | Bridge-aware (linked sources: 5); lineage graph fallback used | OK |
| Fry -> Parr | 853890 | 737402 | -116488 | 4 | 4 | yes | Bridge-aware (linked sources: 6); lineage graph fallback used | OK |
| Parr -> Smolt | 414808 | 397923 | -16885 | 4 | 4 | yes | Bridge-aware (linked sources: 3); lineage graph fallback used | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `251.0018`, `251.0019`, `251.0020`, `251.0021`, `251.0022`, `251.0023`, `251.0026`, `251.0027`, `251.0030`, `251.0031`
- Real stage-entry fishgroup examples: `251.0002`, `251.0003`, `251.0004`, `251.0005`, `251.0006`, `251.0007`, `251.0008`, `251.0009`, `251.0010`, `251.0011`
- Bridge fishgroups excluded from stage-entry windows: `251.0022`, `251.0023`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 68 | 68 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Count Provenance

- Populations where assignment count came from status snapshot fallback (conserved transfer count was zero):
| Stage | Population count from fallback |
| --- | ---: |
| Fry | 1707791 |
| Parr | 1122081 |
| Smolt | 570347 |

| PopulationID | Stage | Assignment count | Status snapshot count |
| --- | --- | ---: | ---: |
| `544859F6-88FD-40FF-BE5F-230A5801C198` | Parr | 217104 | 217104 |
| `895139D8-4754-4500-A543-9B56DD526B27` | Parr | 180899 | 180899 |
| `B105E4FA-ACC9-4BBE-96DA-441EE1FF9589` | Parr | 173418 | 173418 |
| `DE319497-2EB3-4EDA-AE30-6D4512F9429B` | Fry | 142326 | 142326 |
| `0853CA07-236E-48F7-A8B7-5C1428C3251A` | Fry | 142315 | 142315 |

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 1751479 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 30

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 5 | Hatchery:5 | S03 Norðtoftir:5 |
| SourcePopBefore -> SourcePopAfter | 25 | Hatchery:25 | S03 Norðtoftir:25 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 30 | 0 | Hatchery:30 | S03 Norðtoftir:30 | Unknown:30 |
| Reachable outside descendants | 41 | 0 | Hatchery:41 | S03 Norðtoftir:41 | Unknown:41 |

### Active Container Latest Holder Evidence

- For each currently active migrated assignment container, this shows the latest non-zero status holder in source data.
- Containers checked: 6; latest holder in selected component: 6; latest holder outside selected component: 0; unknown latest holder: 0.

| Container | Source container id | Component population | Latest holder population | Latest holder in selected component | Latest count | Latest biomass kg | Latest status time | Site | Prod stage |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| 1102 | BCCB7934-E4FC-4495-849D-CA7EE606F261 | `94AF5967-8202-4F1D-8643-E5671BE2886B` | `94AF5967-8202-4F1D-8643-E5671BE2886B` | yes | 85841 | 5734.71 | 2026-01-22 00:00:00 | S03 Norðtoftir | Hatchery |
| 1103 | 66837253-D591-4E80-BFAB-A3E9DB2B5298 | `55DA00FA-AAA4-48DE-9D61-D0C277574DCC` | `55DA00FA-AAA4-48DE-9D61-D0C277574DCC` | yes | 98544 | 8060.86 | 2026-01-22 00:00:00 | S03 Norðtoftir | Hatchery |
| 1106 | 42921283-E0D8-44B7-9680-530FB044B9CF | `1A8A8302-171B-4D6C-ABE0-957C5D03264C` | `1A8A8302-171B-4D6C-ABE0-957C5D03264C` | yes | 99821 | 6663.52 | 2026-01-22 00:00:00 | S03 Norðtoftir | Hatchery |
| 1107 | 3C05AA57-1A44-48DC-A76F-F55EE0446C57 | `9BD81637-C814-468E-A725-A60B75AF31B1` | `9BD81637-C814-468E-A725-A60B75AF31B1` | yes | 99917 | 8393.7 | 2026-01-22 00:00:00 | S03 Norðtoftir | Hatchery |
| 1109 | C38D44F2-9526-4C01-9D30-5FF623A9F111 | `54C5C09A-1139-41F2-B308-A9A07E9A404A` | `54C5C09A-1139-41F2-B308-A9A07E9A404A` | yes | 99641 | 9987.14 | 2026-01-22 00:00:00 | S03 Norðtoftir | Hatchery |
| 1110 | 4B9DE17D-2E55-45A0-B2E8-4C665BF03A1D | `AC83D5AD-3207-4B6E-A73C-774F73F00E4E` | `AC83D5AD-3207-4B6E-A73C-774F73F00E4E` | yes | 86583 | 7246.83 | 2026-01-22 00:00:00 | S03 Norðtoftir | Hatchery |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)