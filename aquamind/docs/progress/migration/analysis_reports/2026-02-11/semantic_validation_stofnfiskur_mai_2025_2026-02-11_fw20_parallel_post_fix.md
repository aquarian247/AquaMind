# Semantic Migration Validation Report

- Component key: `B2490BF6-4503-4651-8E62-06D043A1FD2A`
- Batch: `Stofnfiskur mai 2025` (id=429)
- Populations: 53
- Window: 2025-05-28 13:07:15 → 2026-02-11 11:11:33.279031

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 336 | 336 | 0.00 |
| Feeding kg | 2324.96 | 2324.96 | -0.00 |
| Mortality events | 1208 | 1041 | 167.00 |
| Mortality count | 567486 | 567486 | 0.00 |
| Mortality biomass kg | 0.00 | 180.32 | -180.32 |
| Culling events | 2 | 2 | 0.00 |
| Culling count | 354 | 354 | 0.00 |
| Culling biomass kg | 1583.97 | 1583.97 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 567840
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 2/2 bridge-aware (100.0%), 0/2 entry-window (0.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 1
- Assignment zero-count rows (population_count <= 0): 31 total, 3 bridge-classified, 0 same-stage superseded-zero, 6 short-lived orphan-zero, 22 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 13.
- Fishgroup classification: 4 temporary bridge fishgroups, 21 real stage-entry fishgroups, 4 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 1707344 | 0 | 1707344 | 1707344 | 1.0 | 1.0 | 2025-05-28 | 2025-05-30 | 5 | 5 | 0 | 5 | 5 |
| Fry | 1281733 | 0 | 1407673 | 1407673 | 1.1 | 1.0 | 2025-08-16 | 2025-08-18 | 8 | 8 | 1 | 9 | 12 |
| Parr | 1800422 | 1800422 | 1800422 | 1800422 | 1.0 | 1.0 | 2025-10-29 | 2025-10-31 | 8 | 8 | 0 | 8 | 36 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1800776 | 1800776 | 0 | 8 | 8 | yes | Bridge-aware (linked sources: 5); lineage graph fallback used | OK |
| Fry -> Parr | 1800776 | 1800776 | 0 | 8 | 8 | yes | Bridge-aware (direct edge linkage; linked sources: 8) | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `253.0006`, `253.0009`, `253.0012`, `253.0014`
- Real stage-entry fishgroup examples: `253.0002`, `253.0003`, `253.0004`, `253.0005`, `253.0007`, `253.0008`, `253.0010`, `253.0011`, `253.0013`, `253.0015`
- Bridge fishgroups excluded from stage-entry windows: `253.0006`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 53 | 53 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 5

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 0 | - | - |
| SourcePopBefore -> SourcePopAfter | 5 | Hatchery:5 | S16 Glyvradalur:5 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 5 | 0 | Hatchery:5 | S16 Glyvradalur:5 | Unknown:5 |
| Reachable outside descendants | 7 | 0 | Hatchery:7 | S16 Glyvradalur:7 | Unknown:7 |

### Active Container Latest Holder Evidence

- For each currently active migrated assignment container, this shows the latest non-zero status holder in source data.
- Containers checked: 8; latest holder in selected component: 8; latest holder outside selected component: 0; unknown latest holder: 0.

| Container | Source container id | Component population | Latest holder population | Latest holder in selected component | Latest count | Latest biomass kg | Latest status time | Site | Prod stage |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| C05 | E4405E3D-0E5D-4F35-9979-2827D70CEFE7 | `068AEFB1-1E83-4869-A24E-5FC68E7CB9C4` | `068AEFB1-1E83-4869-A24E-5FC68E7CB9C4` | yes | 150666 | 406.8 | 2025-10-31 00:00:00 | S16 Glyvradalur | Hatchery |
| C06 | B38CBCB9-F003-4D69-9071-0EB4DEAB9B62 | `7C8D579D-860D-4702-97BC-E78ACEB6129D` | `7C8D579D-860D-4702-97BC-E78ACEB6129D` | yes | 147029 | 367.57 | 2025-10-31 14:58:32 | S16 Glyvradalur | Hatchery |
| C07 | 76144452-16D0-4C89-8A8A-C30F5D288A74 | `9F82871A-3F6E-4D91-9494-06D2778F0E76` | `9F82871A-3F6E-4D91-9494-06D2778F0E76` | yes | 146614 | 385.24 | 2025-10-31 14:58:32 | S16 Glyvradalur | Hatchery |
| C08 | 8EE49EF8-0516-4A59-AD51-A47053455E5F | `A884F674-2903-41C1-9F56-30A7685D0DDE` | `A884F674-2903-41C1-9F56-30A7685D0DDE` | yes | 133137 | 332.84 | 2025-10-31 00:00:00 | S16 Glyvradalur | Hatchery |
| C13 | 5F6D489B-5AF2-4589-8664-374DB83CE810 | `33072C98-484D-4E34-93FE-2ADF95F9209A` | `33072C98-484D-4E34-93FE-2ADF95F9209A` | yes | 149325 | 397.54 | 2025-10-31 00:00:00 | S16 Glyvradalur | Hatchery |
| C14 | 09B3DC8E-6969-4617-93D3-0C0ACAB1D296 | `81E7EA8A-63AE-414B-AC39-5CDACA16D504` | `81E7EA8A-63AE-414B-AC39-5CDACA16D504` | yes | 148773 | 401.69 | 2025-10-31 00:00:00 | S16 Glyvradalur | Hatchery |
| C15 | C28A6753-2AB9-44BF-A87C-4C789A0C05CF | `A03CC00A-E089-496F-B775-A60112558D93` | `A03CC00A-E089-496F-B775-A60112558D93` | yes | 174304 | 470.62 | 2025-10-31 00:00:00 | S16 Glyvradalur | Hatchery |
| C16 | FD79CDDF-25EE-4755-B91B-90245F506E24 | `171D34EF-FD02-47F8-9B7A-18E0B0654F32` | `171D34EF-FD02-47F8-9B7A-18E0B0654F32` | yes | 183442 | 495.29 | 2025-10-31 00:00:00 | S16 Glyvradalur | Hatchery |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)