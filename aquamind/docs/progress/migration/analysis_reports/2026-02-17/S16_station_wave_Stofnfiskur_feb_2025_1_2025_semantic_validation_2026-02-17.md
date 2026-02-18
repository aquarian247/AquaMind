# Semantic Migration Validation Report

- Component key: `06A54D02-57F9-47DF-948D-07067891C007`
- Batch: `Stofnfiskur feb 2025` (id=526)
- Populations: 122
- Window: 2025-02-19 09:54:51 → 2026-01-22 23:59:59.999999 (uncapped end 2026-02-17 16:00:20.527421, cap 2026-01-22 23:59:59.999999)

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 542 | 542 | 0.00 |
| Feeding kg | 14793.12 | 14793.12 | -0.00 |
| Mortality events | 1920 | 1596 | 324.00 |
| Mortality count | 825424 | 825424 | 0.00 |
| Mortality biomass kg | 0.00 | 1822.94 | -1822.94 |
| Culling events | 1 | 1 | 0.00 |
| Culling count | 66814 | 66814 | 0.00 |
| Culling biomass kg | 668140.00 | 668140.00 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 9 | 9 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 892238
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 1/3 bridge-aware (33.3%), 2/3 entry-window (66.7%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 0
- Assignment zero-count rows (population_count <= 0): 33 total, 32 bridge-classified, 1 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 22.
- Fishgroup classification: 54 temporary bridge fishgroups, 20 real stage-entry fishgroups, 54 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 1500410 | 0 | 1500410 | 1500410 | 1.0 | 1.0 | 2025-02-19 | 2025-02-21 | 5 | 5 | 0 | 5 | 5 |
| Fry | 1243002 | 0 | 1243002 | 1243002 | 1.0 | 1.0 | 2025-05-12 | 2025-05-14 | 7 | 7 | 0 | 7 | 7 |
| Parr | 941158 | 0 | 1358896 | 6812454 | 7.24 | 5.01 | 2025-08-05 | 2025-08-07 | 7 | 7 | 0 | 71 | 95 |
| Smolt | 123990 | 622197 | 622197 | 954964 | 7.7 | 1.53 | 2025-12-10 | 2025-12-12 | 1 | 1 | 0 | 6 | 15 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1500410 | 1243002 | -257408 | 7 | 5 | no | Entry window (incomplete linkage) | OK |
| Fry -> Parr | 1211712 | 1043588 | -168124 | 7 | 7 | yes | Bridge-aware (direct edge linkage; linked sources: 7) | OK |
| Parr -> Smolt | 941158 | 123990 | -817168 | 1 | 1 | yes | Entry window (incomplete linkage) | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `251.0018`, `251.0019`, `251.0020`, `251.0022`, `251.0023`, `251.0024`, `251.0026`, `251.0027`, `251.0028`, `251.0029`
- Real stage-entry fishgroup examples: `251.0002`, `251.0003`, `251.0004`, `251.0005`, `251.0006`, `251.0007`, `251.0008`, `251.0009`, `251.0010`, `251.0011`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 122 | 122 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Count Provenance

- Populations where assignment count came from status snapshot fallback (conserved transfer count was zero):
| Stage | Population count from fallback |
| --- | ---: |
| Fry | 438190 |

| PopulationID | Stage | Assignment count | Status snapshot count |
| --- | --- | ---: | ---: |
| `B88CFA95-E634-489C-A1F8-40B474E1BAE4` | Fry | 219095 | 219095 |
| `E3C06D0A-481A-49C9-A3E8-D8DCD11B3A0B` | Fry | 219095 | 219095 |

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 195203 |
| Parr | 25194 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 45

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 3 | Hatchery:3 | S16 Glyvradalur:3 |
| SourcePopBefore -> SourcePopAfter | 42 | Hatchery:42 | S16 Glyvradalur:42 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 45 | 0 | Hatchery:45 | S16 Glyvradalur:45 | Unknown:45 |
| Reachable outside descendants | 61 | 0 | Hatchery:61 | S16 Glyvradalur:61 | Unknown:61 |

### Active Container Latest Holder Evidence

- For each currently active migrated assignment container, this shows the latest non-zero status holder in source data.
- Containers checked: 3; latest holder in selected component: 3; latest holder outside selected component: 0; unknown latest holder: 0.

| Container | Source container id | Component population | Latest holder population | Latest holder in selected component | Latest count | Latest biomass kg | Latest status time | Site | Prod stage |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| D01 | A149E1A7-5A9B-4993-88B0-CEAD2E7C9A28 | `6D17832F-1167-452B-A4AD-7E6260201F48` | `6D17832F-1167-452B-A4AD-7E6260201F48` | yes | 220170 | 17238.3 | 2026-01-22 00:00:00 | S16 Glyvradalur | Hatchery |
| D02 | B35798D6-0CEC-4877-AE42-22701F31DEF4 | `3034F5EE-40D0-4DBF-95EB-2E804066C510` | `3034F5EE-40D0-4DBF-95EB-2E804066C510` | yes | 210440 | 26704.8 | 2026-01-22 00:00:00 | S16 Glyvradalur | Hatchery |
| D03 | 1C86F107-5D9C-405A-BEFE-8357A3C01352 | `61E5C6F5-EA1F-421F-8E36-574BD719F986` | `61E5C6F5-EA1F-421F-8E36-574BD719F986` | yes | 191587 | 15555.3 | 2026-01-22 00:00:00 | S16 Glyvradalur | Hatchery |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)