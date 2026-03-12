# Semantic Migration Validation Report

- Component key: `BC782146-C921-4AD1-8021-0E1ED2228D7C`
- Batch: `Stofnfiskur S-21 feb24 - Vár 2024` (id=1348)
- Populations: 382
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
| Environmental readings | n/a (sqlite) | 111801 | n/a |
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
- Transition basis usage: 4/5 bridge-aware (80.0%), 1/5 entry-window (20.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 0
- Assignment zero-count rows (population_count <= 0): 185 total, 59 bridge-classified, 116 same-stage superseded-zero, 0 short-lived orphan-zero, 10 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 236.
- Fishgroup classification: 104 temporary bridge fishgroups, 26 real stage-entry fishgroups, 104 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 1501655 | 0 | 1501655 | 1501655 | 1.0 | 1.0 | 2024-02-21 | 2024-02-23 | 7 | 7 | 0 | 7 | 11 |
| Fry | 1479522 | 0 | 1558870 | 1856572 | 1.25 | 1.19 | 2024-05-23 | 2024-05-25 | 6 | 6 | 0 | 10 | 23 |
| Parr | 252997 | 0 | 1185836 | 5897871 | 23.31 | 4.97 | 2024-08-23 | 2024-08-25 | 3 | 3 | 0 | 112 | 215 |
| Smolt | 170884 | 0 | 819838 | 1689053 | 9.88 | 2.06 | 2024-11-18 | 2024-11-20 | 2 | 2 | 1 | 21 | 74 |
| Post-Smolt | 341385 | 0 | 836642 | 1627652 | 4.77 | 1.95 | 2025-04-01 | 2025-04-03 | 8 | 8 | 6 | 47 | 59 |
| Adult | 39991 | 0 | 39991 | 39991 | 1.0 | 1.0 | 2024-05-23 | 2024-05-25 | 1 | 0 | 0 | 1 | 1 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1501655 | 1322607 | -179048 | 6 | 6 | yes | Bridge-aware (linked sources: 11) | OK |
| Fry -> Parr | 641604 | 239797 | -401807 | 3 | 3 | yes | Bridge-aware (linked sources: 6) | OK |
| Parr -> Smolt | 123611 | 78134 | -45477 | 2 | 2 | yes | Bridge-aware (linked sources: 3) | OK |
| Smolt -> Post-Smolt | 268998 | 236582 | -32416 | 8 | 8 | yes | Bridge-aware (linked sources: 17) | OK |
| Post-Smolt -> Adult | 341385 | 39991 | -301394 | 1 | 0 | no | Entry window (incomplete linkage) | OK |

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

### Count Provenance

- Populations where assignment count came from status snapshot fallback (conserved transfer count was zero):
| Stage | Population count from fallback |
| --- | ---: |
| Parr | 474976 |
| Post-Smolt | 370732 |

| PopulationID | Stage | Assignment count | Status snapshot count |
| --- | --- | ---: | ---: |
| `90FF4962-780A-4100-BED4-03CD8C9FA990` | Parr | 75470 | 75470 |
| `44910E23-01D9-4BE8-9CAE-8EF36054D9F5` | Parr | 67097 | 67097 |
| `B695A9DD-6A38-4404-94B7-4792015A2974` | Post-Smolt | 58662 | 58662 |
| `F475EF9E-AB5F-45E3-8891-3C4A7C52E7D2` | Post-Smolt | 56267 | 56267 |
| `E2A72FCD-5BC9-41E7-837B-4D6D0993B0CA` | Parr | 55040 | 55040 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 0

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 0 | - | - |
| SourcePopBefore -> SourcePopAfter | 0 | - | - |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 0 | 0 | - | - | - |
| Reachable outside descendants | 0 | 0 | - | - | - |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (advisory)