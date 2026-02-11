# Semantic Migration Validation Report

- Component key: `B52612BD-F18B-48A4-BF21-12B5FC246803`
- Batch: `Bakkafrost S-21 jan 25` (id=392)
- Populations: 183
- Window: 2025-01-06 15:08:04 → 2026-02-10 22:52:18.989134

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 872 | 872 | 0.00 |
| Feeding kg | 26861.00 | 26861.00 | 0.00 |
| Mortality events | 1606 | 1459 | 147.00 |
| Mortality count | 451404 | 451404 | 0.00 |
| Mortality biomass kg | 0.00 | 477.91 | -477.91 |
| Culling events | 35 | 35 | 0.00 |
| Culling count | 196725 | 196725 | 0.00 |
| Culling biomass kg | 3805417.90 | 3805417.90 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 22 | 22 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 648129
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 3/3 bridge-aware (100.0%), 0/3 entry-window (0.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 1
- Assignment zero-count rows (population_count <= 0): 115 total, 41 bridge-classified, 1 same-stage superseded-zero, 43 short-lived orphan-zero, 17 no-count-evidence-zero, 13 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 51.
- Fishgroup classification: 53 temporary bridge fishgroups, 19 real stage-entry fishgroups, 53 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 1389877 | 0 | 1389877 | 1389877 | 1.0 | 1.0 | 2025-01-06 | 2025-01-08 | 7 | 7 | 0 | 7 | 7 |
| Fry | 994105 | 0 | 994105 | 994105 | 1.0 | 1.0 | 2025-04-02 | 2025-04-04 | 6 | 6 | 0 | 6 | 12 |
| Parr | 930010 | 1684033 | 1686072 | 4385675 | 4.72 | 2.6 | 2025-07-07 | 2025-07-09 | 5 | 5 | 0 | 51 | 147 |
| Smolt | 174799 | 0 | 424451 | 487573 | 2.79 | 1.15 | 2025-10-09 | 2025-10-11 | 1 | 1 | 1 | 4 | 17 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1501093 | 1501093 | 0 | 6 | 6 | yes | Bridge-aware (linked sources: 7) | OK |
| Fry -> Parr | 1501093 | 1501093 | 0 | 5 | 5 | yes | Bridge-aware (linked sources: 6); lineage graph fallback used | OK |
| Parr -> Smolt | 175165 | 175165 | 0 | 1 | 1 | yes | Bridge-aware (linked sources: 3) | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `251.0008`, `251.0009`, `251.0010`, `251.0011`, `251.0012`, `251.0013`, `251.0020`, `251.0021`, `251.0022`, `251.0026`
- Real stage-entry fishgroup examples: `251.0002`, `251.0003`, `251.0004`, `251.0005`, `251.0006`, `251.0007`, `251.0014`, `251.0015`, `251.0016`, `251.0017`
- Bridge fishgroups excluded from stage-entry windows: `251.0078`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 183 | 183 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 23

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 0 | - | - |
| SourcePopBefore -> SourcePopAfter | 23 | Hatchery:23 | S21 Viðareiði:23 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 23 | 0 | Hatchery:23 | S21 Viðareiði:23 | Unknown:23 |
| Reachable outside descendants | 50 | 0 | Hatchery:50 | S21 Viðareiði:50 | Unknown:50 |

### Active Container Latest Holder Evidence

- For each currently active migrated assignment container, this shows the latest non-zero status holder in source data.
- Containers checked: 17; latest holder in selected component: 11; latest holder outside selected component: 6; unknown latest holder: 0.

| Container | Source container id | Component population | Latest holder population | Latest holder in selected component | Latest count | Latest biomass kg | Latest status time | Site | Prod stage |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| A01 | 1C4BC069-2B03-4038-9775-1FB3D8C8F915 | `1DDE1B57-95AC-400D-9DA6-C1FBC6EB1787` | `C20D3FC2-A518-487B-B64D-DF20F230D374` | no | 135512 | 965.18 | 2025-10-31 00:00:00 | S21 Viðareiði | Hatchery |
| A03 | 130A5DC0-F1D1-45A3-894C-935BCD0F46DB | `C7685FCB-A56B-45B0-8B05-2F34F90EE295` | `C82C7850-FD6F-43BD-8148-94B4EE004C52` | no | 92869 | 1114.93 | 2025-10-31 00:00:00 | S21 Viðareiði | Hatchery |
| A05 | 4EDA3C9E-DD86-4EB0-88B7-FC496F829F2D | `059742E5-3E85-44BA-AD5D-F88997C7913A` | `36257392-264D-4F30-8CA3-B9145F2B9715` | no | 75273 | 1053.05 | 2025-10-31 00:00:00 | S21 Viðareiði | Hatchery |
| B01 | 217B28E1-4D81-4C69-8B28-8944129CC810 | `4195A5D0-BA0B-4762-83F3-61EC09C49A06` | `4195A5D0-BA0B-4762-83F3-61EC09C49A06` | yes | 46647 | 1416.0 | 2025-10-31 00:00:00 | S21 Viðareiði | Hatchery |
| B02 | 5A785B7F-620E-49CF-A9DC-E15FD1FA3483 | `04255994-08CF-41B6-A52E-1D8264A6C99A` | `04255994-08CF-41B6-A52E-1D8264A6C99A` | yes | 118581 | 3231.65 | 2025-10-31 00:00:00 | S21 Viðareiði | Hatchery |
| B03 | 07DDB999-DC07-4ED0-8C00-87915220B43F | `96A853EF-46C9-4A6C-9399-C1B3837F8167` | `96A853EF-46C9-4A6C-9399-C1B3837F8167` | yes | 76764 | 1115.62 | 2025-10-31 00:00:00 | S21 Viðareiði | Hatchery |
| B04 | FDB9058D-B242-45FA-A6F9-A2D61F11E5FA | `798B4C64-819D-4025-B0D7-261923137988` | `798B4C64-819D-4025-B0D7-261923137988` | yes | 24334 | 1012.68 | 2025-10-31 00:00:00 | S21 Viðareiði | Hatchery |
| B05 | BB003B3F-FB6B-4986-BEBC-0CCBA310C92A | `82675FCF-F154-4824-9FB4-70D8EA763127` | `57E13BAC-26E9-48E5-B8B9-5BDBD44E501A` | no | 69658 | 1199.1 | 2025-10-31 00:00:00 | S21 Viðareiði | Hatchery |
| B06 | 9D8C9346-6577-49B9-970B-DD965FBD6EB7 | `B957AFC0-3410-4BC5-9A44-6B8F6FE75B62` | `B957AFC0-3410-4BC5-9A44-6B8F6FE75B62` | yes | 106279 | 2416.72 | 2025-10-31 00:00:00 | S21 Viðareiði | Hatchery |
| B07 | 979D7540-BF0A-4F0A-A706-CE4D18A76C4E | `5DB57C16-DC16-4158-B7F6-F2E34AFF8B7E` | `5DB57C16-DC16-4158-B7F6-F2E34AFF8B7E` | yes | 66846 | 2558.23 | 2025-10-31 00:00:00 | S21 Viðareiði | Hatchery |
| B08 | 87D8F67D-D75C-422D-BF4D-DCEA87940B88 | `00B5F832-55F3-4854-87E3-D5424F041973` | `00B5F832-55F3-4854-87E3-D5424F041973` | yes | 49152 | 2611.98 | 2025-10-31 00:00:00 | S21 Viðareiði | Hatchery |
| B09 | 1F21A2B3-8C7A-45BD-8B02-9C6B2CF557CF | `86243D5E-8C35-480D-8351-595091216E56` | `6F99F95B-FE2A-4ACF-9B3C-8617757AE2D5` | no | 73162 | 1102.71 | 2025-10-31 00:00:00 | S21 Viðareiði | Hatchery |
| B10 | AA073C42-72C4-48E2-851E-F12650E119B5 | `DDD99A34-0B51-4D5D-A735-E04A9BB7EA3A` | `FEE7CFD1-E835-4E3F-94B2-0DE5F9226520` | no | 73366 | 1233.25 | 2025-10-31 00:00:00 | S21 Viðareiði | Hatchery |
| B11 | 8F8FE5FE-D339-47A0-AC53-D98171366809 | `46D8BC4F-02B5-4F8D-8EA9-ABD52A6850C1` | `46D8BC4F-02B5-4F8D-8EA9-ABD52A6850C1` | yes | 107569 | 3396.05 | 2025-10-31 00:00:00 | S21 Viðareiði | Hatchery |
| B12 | A0FCB3EA-A7F5-42FB-AFD3-1B3CB97B1551 | `2C890DB9-1938-43C4-9C44-F88D4201C881` | `2C890DB9-1938-43C4-9C44-F88D4201C881` | yes | 51406 | 2325.57 | 2025-10-31 00:00:00 | S21 Viðareiði | Hatchery |
| B14 | A1AA0F5D-895A-45FE-8D1B-E387FA596AF6 | `6E073D16-2792-4C7F-814D-2FCE83DBA6E4` | `6E073D16-2792-4C7F-814D-2FCE83DBA6E4` | yes | 28265 | 1552.28 | 2025-10-27 14:20:55 | S21 Viðareiði | Hatchery |
| B15 | A2E1382B-6D19-4B39-8E72-4314EC0519DD | `D59E5624-5D98-444D-9CC4-E530DDB7E8C4` | `D59E5624-5D98-444D-9CC4-E530DDB7E8C4` | yes | 24344 | 1013.09 | 2025-10-29 09:08:41 | S21 Viðareiði | Hatchery |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)