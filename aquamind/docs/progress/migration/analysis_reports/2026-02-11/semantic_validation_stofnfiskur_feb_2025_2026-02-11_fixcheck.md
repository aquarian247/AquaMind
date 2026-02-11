# Semantic Migration Validation Report

- Component key: `06A54D02-57F9-47DF-948D-07067891C007`
- Batch: `Stofnfiskur feb 2025` (id=419)
- Populations: 122
- Window: 2025-02-19 09:54:51 → 2026-02-11 02:32:06.218002

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 542 | 542 | 0.00 |
| Feeding kg | 14793.12 | 14793.12 | -0.00 |
| Mortality events | 1920 | 1596 | 324.00 |
| Mortality count | 825424 | 825424 | 0.00 |
| Mortality biomass kg | 0.00 | 1816.56 | -1816.56 |
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
- Assignment zero-count rows (population_count <= 0): 64 total, 14 bridge-classified, 0 same-stage superseded-zero, 25 short-lived orphan-zero, 25 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 28.
- Fishgroup classification: 33 temporary bridge fishgroups, 19 real stage-entry fishgroups, 33 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 1470032 | 0 | 1470032 | 1470032 | 1.0 | 1.0 | 2025-02-19 | 2025-02-21 | 5 | 5 | 0 | 5 | 5 |
| Fry | 774019 | 0 | 774019 | 774019 | 1.0 | 1.0 | 2025-05-12 | 2025-05-14 | 7 | 7 | 0 | 7 | 7 |
| Parr | 927460 | 1305836 | 1466639 | 4489155 | 4.84 | 3.06 | 2025-08-05 | 2025-08-07 | 7 | 7 | 0 | 46 | 95 |
| Smolt | 0 | 0 | 0 | 0 | - | - | - | - | 0 | 0 | 0 | 0 | 15 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1470032 | 774019 | -696013 | 7 | 5 | no | Entry window (incomplete linkage) | OK |
| Fry -> Parr | 1042177 | 1038807 | -3370 | 7 | 7 | yes | Bridge-aware (direct edge linkage; linked sources: 7) | OK |
| Parr -> Smolt | 927460 | 0 | -927460 | 0 | 0 | no | Entry window (no entry populations) | WARN: stage drop exceeds total known removals by 35222 |

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
| Fry | 268655 |

| PopulationID | Stage | Assignment count | Status snapshot count |
| --- | --- | ---: | ---: |
| `B88CFA95-E634-489C-A1F8-40B474E1BAE4` | Fry | 135515 | 219095 |
| `E3C06D0A-481A-49C9-A3E8-D8DCD11B3A0B` | Fry | 133140 | 219095 |

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 195203 |
| Parr | 25194 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 24

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 3 | Hatchery:3 | S16 Glyvradalur:3 |
| SourcePopBefore -> SourcePopAfter | 21 | Hatchery:21 | S16 Glyvradalur:21 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 24 | 0 | Hatchery:24 | S16 Glyvradalur:24 | Unknown:24 |
| Reachable outside descendants | 40 | 0 | Hatchery:40 | S16 Glyvradalur:40 | Unknown:40 |

### Active Container Latest Holder Evidence

- For each currently active migrated assignment container, this shows the latest non-zero status holder in source data.
- Containers checked: 15; latest holder in selected component: 7; latest holder outside selected component: 8; unknown latest holder: 0.

| Container | Source container id | Component population | Latest holder population | Latest holder in selected component | Latest count | Latest biomass kg | Latest status time | Site | Prod stage |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| C. 18 | 4083C085-62D9-407C-979D-5B3DD849C9FD | `2D08C974-E685-4BFA-9827-8FE3BA54820B` | `2D08C974-E685-4BFA-9827-8FE3BA54820B` | yes | 141315 | 2424.83 | 2025-10-31 00:00:00 | S16 Glyvradalur | Hatchery |
| C.17 | 275243E0-C6F5-46F8-B7C2-B9B43B44176A | `B0E96970-3DCE-4AA4-B215-B94513511F54` | `B0E96970-3DCE-4AA4-B215-B94513511F54` | yes | 188162 | 1314.46 | 2025-10-31 00:00:00 | S16 Glyvradalur | Hatchery |
| C02 | 8DD2197A-16CD-4483-B715-074EC9FAF8EC | `D3CDA579-A457-426B-99E9-4D01C7BE59C8` | `D3CDA579-A457-426B-99E9-4D01C7BE59C8` | yes | 152607 | 3717.24 | 2025-10-31 00:00:00 | S16 Glyvradalur | Hatchery |
| C03 | 7ADA5D59-255D-42AE-89CA-060DAA29EB5C | `84F99F7A-382F-4DDB-BB94-B5B70D07A0F1` | `84F99F7A-382F-4DDB-BB94-B5B70D07A0F1` | yes | 145143 | 3661.98 | 2025-10-31 00:00:00 | S16 Glyvradalur | Hatchery |
| C04 | 67E5E170-462D-400C-BCCF-438698B93A59 | `90D0B333-A5E2-4281-A992-D01745407B88` | `90D0B333-A5E2-4281-A992-D01745407B88` | yes | 77368 | 2320.03 | 2025-10-31 00:00:00 | S16 Glyvradalur | Hatchery |
| C05 | E4405E3D-0E5D-4F35-9979-2827D70CEFE7 | `36411FD6-9306-44B0-9654-8B5A96843A77` | `068AEFB1-1E83-4869-A24E-5FC68E7CB9C4` | no | 150666 | 406.8 | 2025-10-31 00:00:00 | S16 Glyvradalur | Hatchery |
| C06 | B38CBCB9-F003-4D69-9071-0EB4DEAB9B62 | `40EA07EE-2367-4722-81B3-C73BCF1C29E4` | `7C8D579D-860D-4702-97BC-E78ACEB6129D` | no | 147029 | 367.57 | 2025-10-31 14:58:32 | S16 Glyvradalur | Hatchery |
| C07 | 76144452-16D0-4C89-8A8A-C30F5D288A74 | `9733CC3F-76D8-4EEB-9ECC-8CE79EED9917` | `9F82871A-3F6E-4D91-9494-06D2778F0E76` | no | 146614 | 385.24 | 2025-10-31 14:58:32 | S16 Glyvradalur | Hatchery |
| C08 | 8EE49EF8-0516-4A59-AD51-A47053455E5F | `B625C8F5-6EE2-4E5A-865B-9C68EF94DC17` | `A884F674-2903-41C1-9F56-30A7685D0DDE` | no | 133137 | 332.84 | 2025-10-31 00:00:00 | S16 Glyvradalur | Hatchery |
| C09 | BE7EC9E2-D7C7-4FFC-9C5B-3DBE70FD5305 | `C1B6AA3C-7A67-42A7-8FFF-186A32ED8FD9` | `C1B6AA3C-7A67-42A7-8FFF-186A32ED8FD9` | yes | 140373 | 4537.26 | 2025-10-31 00:00:00 | S16 Glyvradalur | Hatchery |
| C10 | 7F8C66B6-18E6-433D-8F13-A6BD3EC7EF45 | `2F012BF8-4038-44CF-A709-CBC1529A1DD9` | `2F012BF8-4038-44CF-A709-CBC1529A1DD9` | yes | 54695 | 1391.47 | 2025-10-31 00:00:00 | S16 Glyvradalur | Hatchery |
| C13 | 5F6D489B-5AF2-4589-8664-374DB83CE810 | `F14FB0CE-8CDC-487A-9810-ED478586E1A7` | `33072C98-484D-4E34-93FE-2ADF95F9209A` | no | 149325 | 397.54 | 2025-10-31 00:00:00 | S16 Glyvradalur | Hatchery |
| C14 | 09B3DC8E-6969-4617-93D3-0C0ACAB1D296 | `5E4C441A-B86C-41C3-A841-8073B26C2F5A` | `81E7EA8A-63AE-414B-AC39-5CDACA16D504` | no | 148773 | 401.69 | 2025-10-31 00:00:00 | S16 Glyvradalur | Hatchery |
| C15 | C28A6753-2AB9-44BF-A87C-4C789A0C05CF | `7A1DA57B-532D-4098-AD54-A213A32E54DA` | `A03CC00A-E089-496F-B775-A60112558D93` | no | 174304 | 470.62 | 2025-10-31 00:00:00 | S16 Glyvradalur | Hatchery |
| C16 | FD79CDDF-25EE-4755-B91B-90245F506E24 | `9BF450C0-AC8D-4CB1-9CC7-E6EA8BF5FBB1` | `171D34EF-FD02-47F8-9B7A-18E0B0654F32` | no | 183442 | 495.29 | 2025-10-31 00:00:00 | S16 Glyvradalur | Hatchery |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)