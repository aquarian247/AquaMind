# Semantic Migration Validation Report

- Component key: `0CB99E1D-8E9F-4CE0-A323-27608DA573D7`
- Batch: `Bakkafrost mai 24` (id=378)
- Populations: 164
- Window: 2024-05-10 08:33:22 → 2025-09-29 07:20:22

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 1521 | 1521 | 0.00 |
| Feeding kg | 465946.68 | 465946.68 | 0.00 |
| Mortality events | 2889 | 2619 | 270.00 |
| Mortality count | 223016 | 223016 | 0.00 |
| Mortality biomass kg | 0.00 | 6574.89 | -6574.89 |
| Culling events | 5 | 5 | 0.00 |
| Culling count | 76087 | 76087 | 0.00 |
| Culling biomass kg | 3436839.00 | 3436839.00 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 44 | 44 | 0.00 |
| Growth samples | 9 | 9 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 299103
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 1/4 bridge-aware (25.0%), 3/4 entry-window (75.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 1
- Assignment zero-count rows (population_count <= 0): 46 total, 43 bridge-classified, 3 same-stage superseded-zero, 0 short-lived orphan-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 63.
- Fishgroup classification: 77 temporary bridge fishgroups, 14 real stage-entry fishgroups, 77 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 295949 | 0 | 295949 | 295949 | 1.0 | 1.0 | 2024-05-10 | 2024-05-12 | 1 | 1 | 0 | 1 | 1 |
| Fry | 496615 | 0 | 496615 | 496615 | 1.0 | 1.0 | 2024-07-27 | 2024-07-29 | 3 | 3 | 0 | 3 | 3 |
| Parr | 834208 | 0 | 2016822 | 8783617 | 10.53 | 4.36 | 2024-10-31 | 2024-11-02 | 7 | 7 | 0 | 84 | 125 |
| Smolt | 304010 | 0 | 1324016 | 2635349 | 8.67 | 1.99 | 2025-03-12 | 2025-03-14 | 1 | 1 | 2 | 14 | 19 |
| Post-Smolt | 168769 | 453576 | 584082 | 663646 | 3.93 | 1.14 | 2025-06-06 | 2025-06-08 | 2 | 2 | 2 | 16 | 16 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 295949 | 496615 | 200666 | 3 | 1 | no | Entry window (incomplete linkage) | WARN: positive delta under incomplete linkage fallback |
| Fry -> Parr | 496615 | 834208 | 337593 | 7 | 7 | yes | Entry window (incomplete linkage) | WARN: positive delta under incomplete linkage fallback |
| Parr -> Smolt | 834208 | 304010 | -530198 | 1 | 1 | yes | Entry window (incomplete linkage) | WARN: stage drop exceeds total known removals by 231095 |
| Smolt -> Post-Smolt | 46186 | 45376 | -810 | 2 | 2 | yes | Bridge-aware (linked sources: 1); lineage graph fallback used | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `24A.0003`, `24A.0004`, `24A.0005`, `24A.0006`, `24A.0009`, `24A.0013`, `24A.0029`, `24A.0030`, `24A.0031`, `24A.0033`
- Real stage-entry fishgroup examples: `242.0002`, `242.0003`, `242.0004`, `242.0005`, `24A.0002`, `24A.0010`, `24A.0011`, `24A.0014`, `24A.0016`, `24A.0019`
- Bridge fishgroups excluded from stage-entry windows: `24A.0086`, `24A.0088`, `24A.0143`, `24A.0144`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 164 | 164 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Count Provenance

- Populations where assignment count came from status snapshot fallback (conserved transfer count was zero):
| Stage | Population count from fallback |
| --- | ---: |
| Fry | 319865 |

| PopulationID | Stage | Assignment count | Status snapshot count |
| --- | --- | ---: | ---: |
| `8E425921-6107-4C1D-9013-BD52D6CD57AA` | Fry | 162867 | 220173 |
| `8F665BEF-9BF0-43D6-8ABE-4DE7F5150705` | Fry | 156998 | 220173 |

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Parr | 119 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 43

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 3 | Hatchery:3 | S16 Glyvradalur:3 |
| SourcePopBefore -> SourcePopAfter | 39 | Hatchery:39 | S16 Glyvradalur:39 |
| DestPopBefore -> DestPopAfter | 1 | Hatchery:1 | S16 Glyvradalur:1 |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 43 | 0 | Hatchery:43 | S16 Glyvradalur:43 | Unknown:43 |
| Reachable outside descendants | 72 | 0 | Hatchery:72 | S16 Glyvradalur:72 | Unknown:72 |

### Active Container Latest Holder Evidence

- For each currently active migrated assignment container, this shows the latest non-zero status holder in source data.
- Containers checked: 4; latest holder in selected component: 0; latest holder outside selected component: 4; unknown latest holder: 0.

| Container | Source container id | Component population | Latest holder population | Latest holder in selected component | Latest count | Latest biomass kg | Latest status time | Site | Prod stage |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| E01 | A8588434-EC8A-48D5-A7BB-9CB1AE614928 | `D889F616-6B3D-4EE6-AAF2-14CD51B506D6` | `D9A84BC2-5497-44DB-AB26-F318E801C026` | no | 143164 | 51676.8 | 2025-10-31 00:00:00 | S16 Glyvradalur | Hatchery |
| E02 | FC172B8F-B999-468E-A079-A0E9380D1E13 | `8394CB4B-A952-431F-8E8F-02500B38D5E0` | `527E2031-CD42-4E0B-B989-44B4AC8EDD64` | no | 138351 | 58835.1 | 2025-10-31 00:00:00 | S16 Glyvradalur | Hatchery |
| E04 | 3783BBEC-FBF4-4894-9C26-18D02559FB87 | `56CC74D5-ED65-46FF-B31A-DA9782D3F32A` | `9BEB44BF-67B9-4900-B751-FF9733644E83` | no | 139265 | 55349.0 | 2025-10-31 00:00:00 | S16 Glyvradalur | Hatchery |
| E07 | B64B9CB2-A0E0-442C-9A51-E943A338F71E | `75208CC2-BE47-4131-9295-119F421295B1` | `E7E143C7-80BE-45F5-A05E-25214C8544AA` | no | 143120 | 32106.9 | 2025-10-31 00:00:00 | S16 Glyvradalur | Hatchery |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 2) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, and short-lived orphan-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)