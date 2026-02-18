# Semantic Migration Validation Report

- Component key: `DCF897C6-A2A3-4914-89E9-D43C8389D887`
- Batch: `BF oktober 2025` (id=541)
- Populations: 17
- Window: 2025-10-09 10:14:20 → 2026-01-22 23:59:59.999999 (uncapped end 2026-02-18 08:45:44.052163, cap 2026-01-22 23:59:59.999999)

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 0 | 0 | 0.00 |
| Feeding kg | 0.00 | 0.00 | 0.00 |
| Mortality events | 21 | 18 | 3.00 |
| Mortality count | 17866 | 17866 | 0.00 |
| Mortality biomass kg | 0.00 | 0.00 | 0.00 |
| Culling events | 0 | 0 | 0.00 |
| Culling count | 0 | 0 | 0.00 |
| Culling biomass kg | 0.00 | 0.00 | 0.00 |
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

## Lifecycle Stage Sanity

- Mixed-batch composition rows: 0
- Known removal count (mortality + culling + escapes + harvest): 17866
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 0/1 bridge-aware (0.0%), 1/1 entry-window (100.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 0
- Assignment zero-count rows (population_count <= 0): 0 total, 0 bridge-classified, 0 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 1.
- Fishgroup classification: 0 temporary bridge fishgroups, 17 real stage-entry fishgroups, 0 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 279990 | 0 | 279990 | 279990 | 1.0 | 1.0 | 2025-10-09 | 2025-10-11 | 1 | 1 | 0 | 1 | 1 |
| Fry | 256637 | 256637 | 256637 | 256637 | 1.0 | 1.0 | 2025-12-30 | 2026-01-01 | 16 | 16 | 0 | 16 | 16 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 279990 | 256637 | -23353 | 16 | 14 | no | Entry window (incomplete linkage) | WARN: stage drop exceeds total known removals by 5487 |

### Fishgroup Classification Samples

- Real stage-entry fishgroup examples: `253.0001`, `253.0002`, `253.0003`, `253.0004`, `253.0005`, `253.0006`, `253.0007`, `253.0008`, `253.0009`, `253.0010`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 17 | 17 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 1

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 0 | - | - |
| SourcePopBefore -> SourcePopAfter | 1 | Hatchery:1 | S08 Gjógv:1 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 1 | 0 | Hatchery:1 | S08 Gjógv:1 | Unknown:1 |
| Reachable outside descendants | 15 | 0 | Hatchery:15 | S08 Gjógv:15 | Unknown:15 |

### Active Container Latest Holder Evidence

- For each currently active migrated assignment container, this shows the latest non-zero status holder in source data.
- Containers checked: 16; latest holder in selected component: 16; latest holder outside selected component: 0; unknown latest holder: 0.

| Container | Source container id | Component population | Latest holder population | Latest holder in selected component | Latest count | Latest biomass kg | Latest status time | Site | Prod stage |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| a1 | C913B1AD-D9F9-44A1-8F7E-1D6C16AE1CD1 | `60BC7A61-673A-4369-9BD5-42038BF69F62` | `60BC7A61-673A-4369-9BD5-42038BF69F62` | yes | 16039 | 6.44 | 2026-01-22 00:00:00 | S08 Gjógv | Hatchery |
| a2 | BF715284-B17C-4C2D-9534-2017913D80EE | `4EE3DE2D-F6FD-468D-A258-BBD26CEA019B` | `4EE3DE2D-F6FD-468D-A258-BBD26CEA019B` | yes | 16039 | 6.44 | 2026-01-22 00:00:00 | S08 Gjógv | Hatchery |
| a3 | 27A91814-881B-4D35-A70C-B351FE60E5D7 | `C5F9C51F-6E0F-4885-8D27-9AACEF01F611` | `C5F9C51F-6E0F-4885-8D27-9AACEF01F611` | yes | 16039 | 6.44 | 2026-01-22 00:00:00 | S08 Gjógv | Hatchery |
| a4 | D2C52EA0-BD1A-4379-AEDE-3CB7A26411D3 | `524C7205-3CBA-4825-8E35-AB088C488C39` | `524C7205-3CBA-4825-8E35-AB088C488C39` | yes | 16040 | 6.44 | 2026-01-22 00:00:00 | S08 Gjógv | Hatchery |
| a5 | 233391AA-1F5C-433C-B01F-EA4A10CE5139 | `60FE0E42-2E5B-4D34-BE3B-C1B74E5F1DBC` | `60FE0E42-2E5B-4D34-BE3B-C1B74E5F1DBC` | yes | 16040 | 6.44 | 2026-01-22 00:00:00 | S08 Gjógv | Hatchery |
| b1 | E012C9EA-5F08-454A-A8B0-85957D141C5B | `B105B675-F6A1-4DB4-8588-AFC5BB49669D` | `B105B675-F6A1-4DB4-8588-AFC5BB49669D` | yes | 16040 | 6.44 | 2026-01-22 00:00:00 | S08 Gjógv | Hatchery |
| b2 | 70972704-174F-4BFA-BD93-05C39EF5C3E5 | `10CDAD50-BBD7-4329-A876-34712B6F71EF` | `10CDAD50-BBD7-4329-A876-34712B6F71EF` | yes | 16040 | 6.44 | 2026-01-22 00:00:00 | S08 Gjógv | Hatchery |
| b3 | 7783A9D1-510C-4051-B404-F950A80D6B3B | `6F49006D-3445-4C6A-ABD9-DD1CD6678061` | `6F49006D-3445-4C6A-ABD9-DD1CD6678061` | yes | 16040 | 6.44 | 2026-01-22 00:00:00 | S08 Gjógv | Hatchery |
| b4 | 42927AC9-C8B1-4D5C-98D6-095C0EA580CA | `FA3EDD24-C37E-420E-9F33-52D7D59DE347` | `FA3EDD24-C37E-420E-9F33-52D7D59DE347` | yes | 16040 | 6.44 | 2026-01-22 00:00:00 | S08 Gjógv | Hatchery |
| b5 | 25998D3D-FEAF-4488-9163-1B4EC1D4C6BF | `57984C4C-4677-4CEF-A0C2-506D944D04AE` | `57984C4C-4677-4CEF-A0C2-506D944D04AE` | yes | 16040 | 6.44 | 2026-01-22 00:00:00 | S08 Gjógv | Hatchery |
| c1 | 5395F882-C6D8-4A28-B5E3-FF5C31AA40BF | `BC80A810-0564-4BC7-82E4-314C0F457E47` | `BC80A810-0564-4BC7-82E4-314C0F457E47` | yes | 16040 | 6.44 | 2026-01-22 00:00:00 | S08 Gjógv | Hatchery |
| c2 | 06402C02-00B2-422F-8512-B02D04EE596C | `7923F3C1-D8A0-458E-B52B-D1D1CEEDC41A` | `7923F3C1-D8A0-458E-B52B-D1D1CEEDC41A` | yes | 16040 | 6.44 | 2026-01-22 00:00:00 | S08 Gjógv | Hatchery |
| c3 | 58F9331C-BB73-4699-BFC6-722F25B09A83 | `BDB6D37B-F007-45E2-90CB-40BC00038C24` | `BDB6D37B-F007-45E2-90CB-40BC00038C24` | yes | 16040 | 6.44 | 2026-01-22 00:00:00 | S08 Gjógv | Hatchery |
| d1 | ACE1F71C-7F4F-4349-8D8A-2CFE91C4466E | `328687EF-C2A7-49EB-9CBB-1E652CAFC84C` | `328687EF-C2A7-49EB-9CBB-1E652CAFC84C` | yes | 16040 | 6.44 | 2026-01-22 00:00:00 | S08 Gjógv | Hatchery |
| d2 | 53450007-96E4-4550-9E0E-83783F95B693 | `758E669D-5B38-4540-A2BE-716E6B6DCBF8` | `758E669D-5B38-4540-A2BE-716E6B6DCBF8` | yes | 16040 | 6.44 | 2026-01-22 00:00:00 | S08 Gjógv | Hatchery |
| d3 | D63B1842-8D10-43BA-A828-A3EEF4204078 | `05B1A94D-9755-4679-AA26-C830B46FFAE6` | `05B1A94D-9755-4679-AA26-C830B46FFAE6` | yes | 16040 | 6.44 | 2026-01-22 00:00:00 | S08 Gjógv | Hatchery |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)