# Semantic Migration Validation Report

- Component key: `BC782146-C921-4AD1-8021-0E1ED2228D7C`
- Batch: `Stofnfiskur S-21 feb24` (id=390)
- Populations: 253
- Window: 2024-02-21 10:00:35 → 2025-08-13 17:38:09

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 3418 | 3418 | 0.00 |
| Feeding kg | 288478.52 | 288478.52 | 0.00 |
| Mortality events | 3890 | 3159 | 731.00 |
| Mortality count | 314374 | 314374 | 0.00 |
| Mortality biomass kg | 0.00 | 2454.91 | -2454.91 |
| Culling events | 99 | 99 | 0.00 |
| Culling count | 161574 | 161574 | 0.00 |
| Culling biomass kg | 2162567.31 | 2162567.32 | -0.01 |
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
- Known removal count (mortality + culling + escapes + harvest): 475948
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 4/4 bridge-aware (100.0%), 0/4 entry-window (0.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 2
- Assignment zero-count rows (population_count <= 0): 67 total, 66 bridge-classified, 1 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 107.
- Fishgroup classification: 104 temporary bridge fishgroups, 26 real stage-entry fishgroups, 104 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 1472522 | 0 | 1472522 | 1472522 | 1.0 | 1.0 | 2024-02-21 | 2024-02-23 | 7 | 7 | 0 | 7 | 7 |
| Fry | 1123604 | 0 | 1123604 | 1123604 | 1.0 | 1.0 | 2024-05-23 | 2024-05-25 | 6 | 6 | 0 | 6 | 11 |
| Parr | 252547 | 0 | 1170420 | 6333876 | 25.08 | 5.41 | 2024-08-23 | 2024-08-25 | 3 | 3 | 0 | 105 | 151 |
| Smolt | 271393 | 0 | 1323859 | 2638556 | 9.72 | 1.99 | 2024-11-18 | 2024-11-20 | 2 | 2 | 1 | 21 | 25 |
| Post-Smolt | 340509 | 431133 | 1444196 | 2316009 | 6.8 | 1.6 | 2025-04-01 | 2025-04-03 | 8 | 8 | 6 | 47 | 59 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1501655 | 1501655 | 0 | 6 | 6 | yes | Bridge-aware (linked sources: 7) | OK |
| Fry -> Parr | 494253 | 494253 | 0 | 3 | 3 | yes | Bridge-aware (linked sources: 2); lineage graph fallback used | OK |
| Parr -> Smolt | 345470 | 345470 | 0 | 2 | 2 | yes | Bridge-aware (linked sources: 3) | OK |
| Smolt -> Post-Smolt | 688523 | 655819 | -32704 | 8 | 8 | yes | Bridge-aware (linked sources: 4); lineage graph fallback used | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `241.0008`, `241.0009`, `241.0010`, `241.0011`, `241.0012`, `241.0019`, `241.0020`, `241.0021`, `241.0025`, `241.0026`
- Real stage-entry fishgroup examples: `241.0002`, `241.0003`, `241.0004`, `241.0005`, `241.0006`, `241.0007`, `241.0013`, `241.0014`, `241.0015`, `241.0016`
- Bridge fishgroups excluded from stage-entry windows: `241.0097`, `241.0183`, `241.0184`, `241.0185`, `241.0194`, `241.0196`, `241.0198`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 253 | 253 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Parr | 8532 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 49

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 2 | Hatchery:2 | S21 Viðareiði:2 |
| SourcePopBefore -> SourcePopAfter | 47 | Hatchery:47 | S21 Viðareiði:47 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 49 | 0 | Hatchery:49 | S21 Viðareiði:49 | Unknown:49 |
| Reachable outside descendants | 129 | 0 | Hatchery:129 | S21 Viðareiði:129 | Unknown:129 |

### Active Container Latest Holder Evidence

- For each currently active migrated assignment container, this shows the latest non-zero status holder in source data.
- Containers checked: 11; latest holder in selected component: 0; latest holder outside selected component: 11; unknown latest holder: 0.

| Container | Source container id | Component population | Latest holder population | Latest holder in selected component | Latest count | Latest biomass kg | Latest status time | Site | Prod stage |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| E1 | 62EB4AB8-0AF7-4D9D-BDE4-F3A779254875 | `E1B9CAC7-6E71-48CC-AB82-4ADF92CC4C55` | `C8C2020A-C197-47C8-8126-3BC8BAD99856` | no | 56455 | 23617.9 | 2025-10-31 00:00:00 | S21 Viðareiði | Hatchery |
| E2 | DC6B8649-601F-47DC-93C8-C0E3032D1B82 | `FA0AEE34-4040-4797-941A-74F1402D6D5A` | `FA899C07-A0BA-4BA3-B4BB-DC6738BDD3BD` | no | 47132 | 20806.6 | 2025-10-31 00:00:00 | S21 Viðareiði | Hatchery |
| E4 | 53726CB3-72CE-46DE-9EE1-77B7A6245540 | `3F91C84E-28FD-4BF4-8C6C-DDA97C63CF1B` | `2607539D-D374-4A86-B240-CA8ABF828465` | no | 66938 | 22966.2 | 2025-10-31 00:00:00 | S21 Viðareiði | Hatchery |
| E5 | 41376C8F-AA52-4CC6-B99C-0C079887AAE6 | `409246EC-CEDD-47D0-844D-C47DC536BC6D` | `0193ED50-A517-4771-A265-0074E033C46A` | no | 51450 | 26432.7 | 2025-10-31 00:00:00 | S21 Viðareiði | Hatchery |
| E7 | 72B19598-8FEA-4CF6-9652-6A2A25DAB98B | `5F06BACC-40ED-4163-97D8-6B639143D7B6` | `1E4B5A0B-9A98-472C-80BB-8D3EA8EB440F` | no | 47039 | 23815.2 | 2025-10-31 00:00:00 | S21 Viðareiði | Hatchery |
| E8 | 47732F90-3763-4C60-973E-5B39CD55EBB0 | `295BDE9A-7F6C-46B0-B638-65AE9BAD5A0C` | `E2641E47-CF36-40BE-8DF1-9E42D786909F` | no | 53416 | 27465.0 | 2025-10-31 00:00:00 | S21 Viðareiði | Hatchery |
| F1 | EF8BEA56-E3E5-47D4-906A-1180212C868B | `2799F914-B427-4F7C-93CE-EB22FF696123` | `FF9BA8FD-E854-4976-B8EA-4ACA2F73E5B6` | no | 76752 | 24358.8 | 2025-10-31 00:00:00 | S21 Viðareiði | Hatchery |
| F2 | F9DA0C83-4A28-4CB2-8A83-681EF5390BEB | `4C063F0C-CD7F-4567-ADBB-7174C1C9E805` | `DD94FFF1-E907-429E-B9C1-CAFC5C3108B5` | no | 62942 | 24405.6 | 2025-10-31 00:00:00 | S21 Viðareiði | Hatchery |
| F4 | AD8E20F2-F745-48B8-8A36-3DA26ADE4C1A | `E1C5F953-33F5-4BD9-8586-3F699E64D983` | `C0B69E56-25F8-4E4F-B9DE-19071DBB14EB` | no | 87244 | 22581.0 | 2025-10-31 00:00:00 | S21 Viðareiði | Hatchery |
| F5 | B05E90F9-F84F-46C3-81AD-DF9B2E640BC0 | `145F1A1A-777E-42E5-AEB0-378A8FF38C48` | `82EDF0AC-8EEB-406C-9721-4828A73F72DB` | no | 48320 | 30811.6 | 2025-10-31 00:00:00 | S21 Viðareiði | Hatchery |
| F7 | 0206A039-87F8-42D6-8CF0-DECDFB53C24D | `6487CAA4-60A6-429A-9BC9-C73F95F6F556` | `902658F9-FCC6-4C3F-9D3E-1522199733F1` | no | 46339 | 27091.8 | 2025-10-31 00:00:00 | S21 Viðareiði | Hatchery |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)