# Semantic Migration Validation Report

- Component key: `B12D319D-8F65-4C87-8818-05C5A388D41C`
- Batch: `Bakkafrost S-21 sep24` (id=469)
- Populations: 321
- Window: 2024-09-16 11:22:28 → 2026-02-16 15:17:31.023968

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 2258 | 2258 | 0.00 |
| Feeding kg | 106343.00 | 106343.00 | 0.00 |
| Mortality events | 2839 | 2365 | 474.00 |
| Mortality count | 201391 | 201391 | 0.00 |
| Mortality biomass kg | 0.00 | 1014.75 | -1014.75 |
| Culling events | 193 | 193 | 0.00 |
| Culling count | 325619 | 325619 | 0.00 |
| Culling biomass kg | 6248933.29 | 6248933.24 | 0.05 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 26 | 26 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 527010
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 4/4 bridge-aware (100.0%), 0/4 entry-window (0.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 2
- Assignment zero-count rows (population_count <= 0): 116 total, 115 bridge-classified, 1 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 157.
- Fishgroup classification: 191 temporary bridge fishgroups, 30 real stage-entry fishgroups, 191 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 1500408 | 0 | 1500408 | 1500408 | 1.0 | 1.0 | 2024-09-16 | 2024-09-18 | 7 | 7 | 0 | 7 | 7 |
| Fry | 1373867 | 0 | 1373867 | 1373867 | 1.0 | 1.0 | 2024-12-16 | 2024-12-18 | 6 | 6 | 0 | 6 | 12 |
| Parr | 1083809 | 0 | 1620065 | 8352539 | 7.71 | 5.16 | 2025-03-27 | 2025-03-29 | 6 | 6 | 1 | 139 | 230 |
| Smolt | 240830 | 0 | 1194868 | 2000552 | 8.31 | 1.67 | 2025-07-02 | 2025-07-04 | 3 | 3 | 1 | 26 | 33 |
| Post-Smolt | 477088 | 943174 | 1020343 | 1301863 | 2.73 | 1.28 | 2025-11-11 | 2025-11-13 | 8 | 8 | 4 | 27 | 39 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1500408 | 1500408 | 0 | 6 | 6 | yes | Bridge-aware (linked sources: 7) | OK |
| Fry -> Parr | 1500408 | 1500408 | 0 | 6 | 6 | yes | Bridge-aware (linked sources: 6); lineage graph fallback used | OK |
| Parr -> Smolt | 343092 | 343092 | 0 | 3 | 3 | yes | Bridge-aware (linked sources: 6) | OK |
| Smolt -> Post-Smolt | 726291 | 693789 | -32502 | 8 | 8 | yes | Bridge-aware (linked sources: 5); lineage graph fallback used | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `243.0008`, `243.0009`, `243.0010`, `243.0011`, `243.0012`, `243.0013`, `243.0020`, `243.0021`, `243.0022`, `243.0024`
- Real stage-entry fishgroup examples: `243.0002`, `243.0003`, `243.0004`, `243.0005`, `243.0006`, `243.0007`, `243.0014`, `243.0015`, `243.0016`, `243.0017`
- Bridge fishgroups excluded from stage-entry windows: `243.0030`, `243.0108`, `243.0283`, `243.0284`, `243.0285`, `243.0287`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 321 | 321 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 68

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 0 | - | - |
| SourcePopBefore -> SourcePopAfter | 68 | Hatchery:68 | S21 Viðareiði:68 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 68 | 0 | Hatchery:68 | S21 Viðareiði:68 | Unknown:68 |
| Reachable outside descendants | 143 | 0 | Hatchery:143 | S21 Viðareiði:143 | Unknown:143 |

### Active Container Latest Holder Evidence

- For each currently active migrated assignment container, this shows the latest non-zero status holder in source data.
- Containers checked: 16; latest holder in selected component: 16; latest holder outside selected component: 0; unknown latest holder: 0.

| Container | Source container id | Component population | Latest holder population | Latest holder in selected component | Latest count | Latest biomass kg | Latest status time | Site | Prod stage |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| E1 | 62EB4AB8-0AF7-4D9D-BDE4-F3A779254875 | `D0A9B4F2-AD33-43FD-8C16-DF90A9E09744` | `D0A9B4F2-AD33-43FD-8C16-DF90A9E09744` | yes | 68948 | 15359.9 | 2026-01-22 00:00:00 | S21 Viðareiði | Hatchery |
| E2 | DC6B8649-601F-47DC-93C8-C0E3032D1B82 | `C17C2300-0F82-4969-9C03-49A9BB9386F1` | `C17C2300-0F82-4969-9C03-49A9BB9386F1` | yes | 61260 | 13487.3 | 2026-01-22 00:00:00 | S21 Viðareiði | Hatchery |
| E3 | 836C6994-DBB0-40DD-9D42-F8084D11C44B | `5B3668D8-67B8-4B2C-B15B-510DE1A3D910` | `5B3668D8-67B8-4B2C-B15B-510DE1A3D910` | yes | 52443 | 9378.63 | 2026-01-22 00:00:00 | S21 Viðareiði | Hatchery |
| E4 | 53726CB3-72CE-46DE-9EE1-77B7A6245540 | `BD5711C6-199F-447D-A974-E6C3C363BD7E` | `BD5711C6-199F-447D-A974-E6C3C363BD7E` | yes | 83832 | 15522.2 | 2026-01-22 00:00:00 | S21 Viðareiði | Hatchery |
| E5 | 41376C8F-AA52-4CC6-B99C-0C079887AAE6 | `C3DD560C-0EFE-4071-82EB-BBFBA4FD3A02` | `C3DD560C-0EFE-4071-82EB-BBFBA4FD3A02` | yes | 39893 | 11293.8 | 2026-01-22 00:00:00 | S21 Viðareiði | Hatchery |
| E6 | 626ED567-D397-46DB-820F-E1E6A8980828 | `35F3D944-C765-4EE7-B400-349B7EF45BAF` | `35F3D944-C765-4EE7-B400-349B7EF45BAF` | yes | 58598 | 17318.3 | 2026-01-22 00:00:00 | S21 Viðareiði | Hatchery |
| E7 | 72B19598-8FEA-4CF6-9652-6A2A25DAB98B | `CFDE2967-32C2-440F-98BF-C489FEB9B38E` | `CFDE2967-32C2-440F-98BF-C489FEB9B38E` | yes | 62310 | 17765.8 | 2026-01-22 00:00:00 | S21 Viðareiði | Hatchery |
| E8 | 47732F90-3763-4C60-973E-5B39CD55EBB0 | `3F0DEB33-AC76-41FD-9937-AB99363942B8` | `3F0DEB33-AC76-41FD-9937-AB99363942B8` | yes | 49804 | 15069.9 | 2026-01-22 00:00:00 | S21 Viðareiði | Hatchery |
| F1 | EF8BEA56-E3E5-47D4-906A-1180212C868B | `78CC819F-E9BC-4B60-B93C-CD6239925F1A` | `78CC819F-E9BC-4B60-B93C-CD6239925F1A` | yes | 67051 | 13139.6 | 2026-01-22 00:00:00 | S21 Viðareiði | Hatchery |
| F2 | F9DA0C83-4A28-4CB2-8A83-681EF5390BEB | `FBC29FF6-5E63-458B-AA4D-397FB48854DE` | `FBC29FF6-5E63-458B-AA4D-397FB48854DE` | yes | 74480 | 15367.5 | 2026-01-22 00:00:00 | S21 Viðareiði | Hatchery |
| F3 | F8497058-9639-4748-8C08-E2E6B42A1A8D | `3B364CC2-8F63-4DE3-85DF-0CE1BD54C947` | `3B364CC2-8F63-4DE3-85DF-0CE1BD54C947` | yes | 46104 | 7225.13 | 2026-01-22 00:00:00 | S21 Viðareiði | Hatchery |
| F4 | AD8E20F2-F745-48B8-8A36-3DA26ADE4C1A | `B92A1E35-3795-46C7-98DE-823953C5435B` | `B92A1E35-3795-46C7-98DE-823953C5435B` | yes | 81615 | 12572.5 | 2026-01-22 00:00:00 | S21 Viðareiði | Hatchery |
| F5 | B05E90F9-F84F-46C3-81AD-DF9B2E640BC0 | `517B77E1-6C77-4609-987C-E7D40F8FBD22` | `517B77E1-6C77-4609-987C-E7D40F8FBD22` | yes | 33670 | 10893.7 | 2026-01-22 00:00:00 | S21 Viðareiði | Hatchery |
| F6 | 04C2D78F-305C-4EC0-BFD4-632DB3CF9091 | `747932E3-DF6A-400B-8472-015C2F055827` | `747932E3-DF6A-400B-8472-015C2F055827` | yes | 65734 | 22436.6 | 2026-01-22 00:00:00 | S21 Viðareiði | Hatchery |
| F7 | 0206A039-87F8-42D6-8CF0-DECDFB53C24D | `170DD652-8976-4008-A624-A22BCD228321` | `170DD652-8976-4008-A624-A22BCD228321` | yes | 50413 | 13538.2 | 2026-01-22 00:00:00 | S21 Viðareiði | Hatchery |
| F8 | DC3CF0C1-DCC6-438F-A712-D6658ECCCFB5 | `33912570-22EA-4ECB-BBC5-9CE0C412E8D0` | `33912570-22EA-4ECB-BBC5-9CE0C412E8D0` | yes | 47019 | 12678.2 | 2026-01-22 00:00:00 | S21 Viðareiði | Hatchery |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)