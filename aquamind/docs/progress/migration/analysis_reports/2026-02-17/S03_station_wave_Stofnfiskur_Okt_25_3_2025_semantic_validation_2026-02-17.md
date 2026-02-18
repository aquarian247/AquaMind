# Semantic Migration Validation Report

- Component key: `61D42D9D-D222-4B66-8860-1140C25D440E`
- Batch: `Stofnfiskur Okt 25` (id=537)
- Populations: 21
- Window: 2025-10-01 09:35:19 → 2026-01-22 23:59:59.999999 (uncapped end 2026-02-18 08:24:28.816154, cap 2026-01-22 23:59:59.999999)

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 0 | 0 | 0.00 |
| Feeding kg | 0.00 | 0.00 | 0.00 |
| Mortality events | 73 | 63 | 10.00 |
| Mortality count | 12244 | 12244 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 12244
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 1/1 bridge-aware (100.0%), 0/1 entry-window (0.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 1
- Assignment zero-count rows (population_count <= 0): 0 total, 0 bridge-classified, 0 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 0.
- Fishgroup classification: 0 temporary bridge fishgroups, 21 real stage-entry fishgroups, 0 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 1761002 | 0 | 1761002 | 1761002 | 1.0 | 1.0 | 2025-10-01 | 2025-10-03 | 9 | 9 | 0 | 9 | 9 |
| Fry | 1633987 | 1633987 | 1633987 | 1633987 | 1.0 | 1.0 | 2025-12-30 | 2026-01-01 | 12 | 12 | 0 | 12 | 12 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1761002 | 1633987 | -127015 | 12 | 12 | yes | Bridge-aware (linked sources: 9); lineage graph fallback used | WARN: stage drop exceeds total known removals by 114771 |

### Fishgroup Classification Samples

- Real stage-entry fishgroup examples: `253.0001`, `253.0002`, `253.0003`, `253.0004`, `253.0005`, `253.0006`, `253.0007`, `253.0008`, `253.0009`, `253.0010`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 21 | 21 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Count Provenance

- Populations where assignment count came from status snapshot fallback (conserved transfer count was zero):
| Stage | Population count from fallback |
| --- | ---: |
| Fry | 1633987 |

| PopulationID | Stage | Assignment count | Status snapshot count |
| --- | --- | ---: | ---: |
| `1B9565CA-160F-4969-8DEF-231E3F3D0581` | Fry | 137848 | 137848 |
| `2FC38B20-3943-47A5-8F16-46B82B2A9FFE` | Fry | 137680 | 137680 |
| `02098006-3B3A-4E39-A743-A83BE0C732C7` | Fry | 137500 | 137500 |
| `861C13A7-B74A-41BD-BE9B-45C174032A5E` | Fry | 137276 | 137276 |
| `58AE3996-BE40-4164-9A12-74573DC53BC5` | Fry | 137001 | 137001 |

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 1761002 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 9

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 9 | Hatchery:9 | S03 Norðtoftir:9 |
| SourcePopBefore -> SourcePopAfter | 0 | - | - |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 9 | 0 | Hatchery:9 | S03 Norðtoftir:9 | Unknown:9 |
| Reachable outside descendants | 20 | 0 | Hatchery:20 | S03 Norðtoftir:20 | Unknown:20 |

### Active Container Latest Holder Evidence

- For each currently active migrated assignment container, this shows the latest non-zero status holder in source data.
- Containers checked: 12; latest holder in selected component: 12; latest holder outside selected component: 0; unknown latest holder: 0.

| Container | Source container id | Component population | Latest holder population | Latest holder in selected component | Latest count | Latest biomass kg | Latest status time | Site | Prod stage |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| 501 | 02FD376A-9614-414A-B8AF-0B47CDE96345 | `6B1B9491-E8C8-4676-8AB3-DBC00306404F` | `6B1B9491-E8C8-4676-8AB3-DBC00306404F` | yes | 136658 | 39.21 | 2026-01-22 00:00:00 | S03 Norðtoftir | Hatchery |
| 502 | 7F5F6AD6-9D4A-4B3B-8F5B-B95F894C2282 | `02098006-3B3A-4E39-A743-A83BE0C732C7` | `02098006-3B3A-4E39-A743-A83BE0C732C7` | yes | 137500 | 39.33 | 2026-01-22 00:00:00 | S03 Norðtoftir | Hatchery |
| 503 | A5E6D3A5-AF84-4A4D-8E0D-9D2F427FF0DB | `58AE3996-BE40-4164-9A12-74573DC53BC5` | `58AE3996-BE40-4164-9A12-74573DC53BC5` | yes | 137001 | 39.17 | 2026-01-22 00:00:00 | S03 Norðtoftir | Hatchery |
| 504 | E803E7AB-5777-45DE-A875-3DC6450D23AC | `861C13A7-B74A-41BD-BE9B-45C174032A5E` | `861C13A7-B74A-41BD-BE9B-45C174032A5E` | yes | 137276 | 38.88 | 2026-01-22 00:00:00 | S03 Norðtoftir | Hatchery |
| 505 | 58607BE3-14D7-496A-80E6-DE726EBF254E | `1B9565CA-160F-4969-8DEF-231E3F3D0581` | `1B9565CA-160F-4969-8DEF-231E3F3D0581` | yes | 137848 | 39.3 | 2026-01-22 00:00:00 | S03 Norðtoftir | Hatchery |
| 506 | 29AEA2C0-441C-4E8A-949D-6BA2F50A97D8 | `2FC38B20-3943-47A5-8F16-46B82B2A9FFE` | `2FC38B20-3943-47A5-8F16-46B82B2A9FFE` | yes | 137680 | 39.41 | 2026-01-22 00:00:00 | S03 Norðtoftir | Hatchery |
| 507 | 6CC396D7-B12D-47A8-A4C2-829149C5A815 | `B1D6AFE2-1502-40B6-829B-A6417DBC97BD` | `B1D6AFE2-1502-40B6-829B-A6417DBC97BD` | yes | 136196 | 39.37 | 2026-01-22 00:00:00 | S03 Norðtoftir | Hatchery |
| 508 | BAB36CFE-1ACA-4C47-9144-C33F72BA1B31 | `BADB46E5-A5EB-44AB-8281-75AE4B70AD91` | `BADB46E5-A5EB-44AB-8281-75AE4B70AD91` | yes | 135952 | 39.16 | 2026-01-22 00:00:00 | S03 Norðtoftir | Hatchery |
| 509 | 077BD6CC-5251-4329-B37A-916384A62F98 | `BE27A979-984A-4A1E-9DCF-66E5C29F0AEF` | `BE27A979-984A-4A1E-9DCF-66E5C29F0AEF` | yes | 134096 | 38.72 | 2026-01-22 00:00:00 | S03 Norðtoftir | Hatchery |
| 510 | 6353FDE9-3294-4407-BD8D-5DA1CF6CAD8D | `2C7CBDBC-969F-4FE7-B798-C66A7F315D86` | `2C7CBDBC-969F-4FE7-B798-C66A7F315D86` | yes | 133174 | 38.88 | 2026-01-22 00:00:00 | S03 Norðtoftir | Hatchery |
| 511 | BBB15FC4-92EE-4152-93C3-DF0D2D80D974 | `A9097CF5-3FA2-436B-802E-A344F4B49B0D` | `A9097CF5-3FA2-436B-802E-A344F4B49B0D` | yes | 135730 | 39.04 | 2026-01-22 00:00:00 | S03 Norðtoftir | Hatchery |
| 512 | 0D01E87E-3806-48C5-9A17-22452C5D46FA | `419C46BB-2D32-488B-A049-64A9E277E29C` | `419C46BB-2D32-488B-A049-64A9E277E29C` | yes | 134876 | 36.78 | 2026-01-22 00:00:00 | S03 Norðtoftir | Hatchery |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)