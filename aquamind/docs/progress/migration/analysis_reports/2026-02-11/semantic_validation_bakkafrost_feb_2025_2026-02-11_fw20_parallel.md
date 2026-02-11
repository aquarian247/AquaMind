# Semantic Migration Validation Report

- Component key: `4A1E4829-7D62-4CBA-A8CF-274E1F611B6D`
- Batch: `Bakkafrost feb 2025` (id=406)
- Populations: 72
- Window: 2025-02-25 15:42:13 → 2026-02-11 01:47:03.001889

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 137 | 137 | 0.00 |
| Feeding kg | 4133.75 | 4133.75 | -0.00 |
| Mortality events | 563 | 509 | 54.00 |
| Mortality count | 340424 | 340424 | 0.00 |
| Mortality biomass kg | 0.00 | 890.07 | -890.07 |
| Culling events | 1 | 1 | 0.00 |
| Culling count | 66814 | 66814 | 0.00 |
| Culling biomass kg | 668140.00 | 668140.00 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 9 | 9 | 0.00 |
| Growth samples | 3 | 3 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 407238
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 1/3 bridge-aware (33.3%), 2/3 entry-window (66.7%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 1
- Assignment zero-count rows (population_count <= 0): 55 total, 10 bridge-classified, 0 same-stage superseded-zero, 23 short-lived orphan-zero, 22 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 9.
- Fishgroup classification: 12 temporary bridge fishgroups, 5 real stage-entry fishgroups, 12 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 280972 | 0 | 280972 | 280972 | 1.0 | 1.0 | 2025-02-25 | 2025-02-27 | 1 | 1 | 0 | 1 | 1 |
| Fry | 264223 | 0 | 264223 | 264223 | 1.0 | 1.0 | 2025-05-12 | 2025-05-14 | 2 | 2 | 0 | 2 | 2 |
| Parr | 248437 | 855388 | 855388 | 1057388 | 4.26 | 1.24 | 2025-08-06 | 2025-08-08 | 2 | 2 | 0 | 14 | 55 |
| Smolt | 0 | 0 | 0 | 0 | - | - | - | - | 0 | 0 | 0 | 0 | 14 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 299995 | 299995 | 0 | 2 | 2 | yes | Bridge-aware (linked sources: 1); lineage graph fallback used | OK |
| Fry -> Parr | 264223 | 248437 | -15786 | 2 | 2 | yes | Entry window (no bridge path) | OK |
| Parr -> Smolt | 248437 | 0 | -248437 | 0 | 0 | no | Entry window (no entry populations) | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `252.0005`, `252.0006`, `25A.0003`, `25A.0006`, `25A.0007`, `25A.0009`, `25A.0010`, `25A.0011`, `25A.0015`, `25A.0017`
- Real stage-entry fishgroup examples: `252.0002`, `252.0003`, `252.0004`, `25A.0002`, `25A.0004`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 72 | 72 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 7

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 0 | - | - |
| SourcePopBefore -> SourcePopAfter | 7 | Hatchery:7 | S16 Glyvradalur:7 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 7 | 0 | Hatchery:7 | S16 Glyvradalur:7 | Unknown:7 |
| Reachable outside descendants | 13 | 0 | Hatchery:13 | S16 Glyvradalur:13 | Unknown:13 |

### Active Container Latest Holder Evidence

- For each currently active migrated assignment container, this shows the latest non-zero status holder in source data.
- Containers checked: 11; latest holder in selected component: 5; latest holder outside selected component: 6; unknown latest holder: 0.

| Container | Source container id | Component population | Latest holder population | Latest holder in selected component | Latest count | Latest biomass kg | Latest status time | Site | Prod stage |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| C. 18 | 4083C085-62D9-407C-979D-5B3DD849C9FD | `2D08C974-E685-4BFA-9827-8FE3BA54820B` | `2D08C974-E685-4BFA-9827-8FE3BA54820B` | yes | 141315 | 2424.83 | 2025-10-31 00:00:00 | S16 Glyvradalur | Hatchery |
| C.17 | 275243E0-C6F5-46F8-B7C2-B9B43B44176A | `B0E96970-3DCE-4AA4-B215-B94513511F54` | `B0E96970-3DCE-4AA4-B215-B94513511F54` | yes | 188162 | 1314.46 | 2025-10-31 00:00:00 | S16 Glyvradalur | Hatchery |
| C03 | 7ADA5D59-255D-42AE-89CA-060DAA29EB5C | `84F99F7A-382F-4DDB-BB94-B5B70D07A0F1` | `84F99F7A-382F-4DDB-BB94-B5B70D07A0F1` | yes | 145143 | 3661.98 | 2025-10-31 00:00:00 | S16 Glyvradalur | Hatchery |
| C04 | 67E5E170-462D-400C-BCCF-438698B93A59 | `90D0B333-A5E2-4281-A992-D01745407B88` | `90D0B333-A5E2-4281-A992-D01745407B88` | yes | 77368 | 2320.03 | 2025-10-31 00:00:00 | S16 Glyvradalur | Hatchery |
| C05 | E4405E3D-0E5D-4F35-9979-2827D70CEFE7 | `36411FD6-9306-44B0-9654-8B5A96843A77` | `068AEFB1-1E83-4869-A24E-5FC68E7CB9C4` | no | 150666 | 406.8 | 2025-10-31 00:00:00 | S16 Glyvradalur | Hatchery |
| C06 | B38CBCB9-F003-4D69-9071-0EB4DEAB9B62 | `0FEC1A4D-E46D-40F0-8C0D-8090A77DBB51` | `7C8D579D-860D-4702-97BC-E78ACEB6129D` | no | 147029 | 367.57 | 2025-10-31 14:58:32 | S16 Glyvradalur | Hatchery |
| C07 | 76144452-16D0-4C89-8A8A-C30F5D288A74 | `B2B56602-764C-45AD-AA59-E878E98C058E` | `9F82871A-3F6E-4D91-9494-06D2778F0E76` | no | 146614 | 385.24 | 2025-10-31 14:58:32 | S16 Glyvradalur | Hatchery |
| C08 | 8EE49EF8-0516-4A59-AD51-A47053455E5F | `B625C8F5-6EE2-4E5A-865B-9C68EF94DC17` | `A884F674-2903-41C1-9F56-30A7685D0DDE` | no | 133137 | 332.84 | 2025-10-31 00:00:00 | S16 Glyvradalur | Hatchery |
| C10 | 7F8C66B6-18E6-433D-8F13-A6BD3EC7EF45 | `2F012BF8-4038-44CF-A709-CBC1529A1DD9` | `2F012BF8-4038-44CF-A709-CBC1529A1DD9` | yes | 54695 | 1391.47 | 2025-10-31 00:00:00 | S16 Glyvradalur | Hatchery |
| C13 | 5F6D489B-5AF2-4589-8664-374DB83CE810 | `F14FB0CE-8CDC-487A-9810-ED478586E1A7` | `33072C98-484D-4E34-93FE-2ADF95F9209A` | no | 149325 | 397.54 | 2025-10-31 00:00:00 | S16 Glyvradalur | Hatchery |
| C15 | C28A6753-2AB9-44BF-A87C-4C789A0C05CF | `7A1DA57B-532D-4098-AD54-A213A32E54DA` | `A03CC00A-E089-496F-B775-A60112558D93` | no | 174304 | 470.62 | 2025-10-31 00:00:00 | S16 Glyvradalur | Hatchery |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)