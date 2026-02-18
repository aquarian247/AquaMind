# Semantic Migration Validation Report

- Component key: `1636C683-E8F2-476D-BC21-0170CA7DCEE8`
- Batch: `Benchmark Gen. Desembur 2024` (id=463)
- Populations: 221
- Window: 2024-12-18 08:52:25 → 2026-02-16 14:15:28.601393

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 2889 | 2889 | 0.00 |
| Feeding kg | 297524.43 | 297524.43 | 0.00 |
| Mortality events | 3832 | 3735 | 97.00 |
| Mortality count | 1246577 | 1246577 | 0.00 |
| Mortality biomass kg | 0.00 | 4996.48 | -4996.48 |
| Culling events | 16 | 16 | 0.00 |
| Culling count | 85367 | 85367 | 0.00 |
| Culling biomass kg | 4488182.00 | 4488182.00 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 22 | 22 | 0.00 |
| Growth samples | 301 | 301 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 1331944
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 3/4 bridge-aware (75.0%), 1/4 entry-window (25.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 3
- Assignment zero-count rows (population_count <= 0): 31 total, 31 bridge-classified, 0 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 47.
- Fishgroup classification: 88 temporary bridge fishgroups, 64 real stage-entry fishgroups, 88 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 3504525 | 0 | 3504525 | 3504525 | 1.0 | 1.0 | 2024-12-18 | 2024-12-20 | 39 | 39 | 0 | 39 | 39 |
| Fry | 3196671 | 0 | 3196671 | 3196671 | 1.0 | 1.0 | 2025-03-05 | 2025-03-07 | 12 | 12 | 0 | 12 | 12 |
| Parr | 1656072 | 0 | 3304902 | 8191741 | 4.95 | 2.48 | 2025-05-26 | 2025-05-28 | 7 | 7 | 10 | 51 | 80 |
| Smolt | 180955 | 0 | 2068367 | 6216105 | 34.35 | 3.01 | 2025-07-26 | 2025-07-28 | 3 | 3 | 3 | 50 | 51 |
| Post-Smolt | 411045 | 2191512 | 2384164 | 4054183 | 9.86 | 1.7 | 2025-10-23 | 2025-10-25 | 3 | 3 | 3 | 38 | 39 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1168167 | 89859 | -1078308 | 12 | 12 | yes | Bridge-aware (linked sources: 13); lineage graph fallback used | OK |
| Fry -> Parr | 66984 | 64241 | -2743 | 7 | 7 | yes | Bridge-aware (linked sources: 9); lineage graph fallback used | OK |
| Parr -> Smolt | 12011 | 6722 | -5289 | 3 | 3 | yes | Bridge-aware (linked sources: 2); lineage graph fallback used | OK |
| Smolt -> Post-Smolt | 180955 | 411045 | 230090 | 3 | 3 | yes | Entry window (incomplete linkage) | WARN: positive delta under incomplete linkage fallback |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `244.0046`, `244.0052`, `244.0053`, `244.0054`, `244.0055`, `244.0056`, `244.0057`, `244.0058`, `244.0059`, `244.0060`
- Real stage-entry fishgroup examples: `244.0002`, `244.0003`, `244.0004`, `244.0005`, `244.0006`, `244.0007`, `244.0008`, `244.0009`, `244.0010`, `244.0011`
- Bridge fishgroups excluded from stage-entry windows: `244.0065`, `244.0066`, `244.0083`, `244.0084`, `244.0085`, `244.0087`, `244.0089`, `244.0095`, `244.0096`, `244.0097`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 221 | 221 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 3504525 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 84

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 39 | Hatchery:39 | S24 Strond:39 |
| SourcePopBefore -> SourcePopAfter | 45 | Hatchery:45 | S24 Strond:45 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 84 | 0 | Hatchery:84 | S24 Strond:84 | Unknown:84 |
| Reachable outside descendants | 165 | 0 | Hatchery:165 | S24 Strond:165 | Unknown:165 |

### Active Container Latest Holder Evidence

- For each currently active migrated assignment container, this shows the latest non-zero status holder in source data.
- Containers checked: 15; latest holder in selected component: 15; latest holder outside selected component: 0; unknown latest holder: 0.

| Container | Source container id | Component population | Latest holder population | Latest holder in selected component | Latest count | Latest biomass kg | Latest status time | Site | Prod stage |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| G1 | 6073D1BB-0651-461C-AFF6-925927E49552 | `FAD92079-BBE3-4602-BB32-19D1517C4DE1` | `FAD92079-BBE3-4602-BB32-19D1517C4DE1` | yes | 150356 | 95025.9 | 2026-01-22 00:00:00 | S24 Strond | Hatchery |
| G2 | 657402E3-3500-466C-86D5-DC1C767A3A70 | `C1C11B30-3557-4AF7-929F-9D2855847947` | `C1C11B30-3557-4AF7-929F-9D2855847947` | yes | 148934 | 69635.2 | 2026-01-22 00:00:00 | S24 Strond | Hatchery |
| G3 | 01CB4CBE-E9C6-4200-8A5F-5F095B388D71 | `500AE2D4-01A9-4372-9F8F-76DC844A410E` | `500AE2D4-01A9-4372-9F8F-76DC844A410E` | yes | 155056 | 55213.9 | 2026-01-22 00:00:00 | S24 Strond | Hatchery |
| G4 | 59951ABF-8516-489D-8C11-6B5A8BABAE83 | `DD43441C-D0A0-4715-B48B-E93C7B09A706` | `DD43441C-D0A0-4715-B48B-E93C7B09A706` | yes | 160559 | 82005.1 | 2026-01-22 00:00:00 | S24 Strond | Hatchery |
| H1 | D306600C-5EE9-4FD5-A9CC-278C501212D0 | `336383E4-EF6E-4D6D-A7E6-E25A9B14FFF9` | `336383E4-EF6E-4D6D-A7E6-E25A9B14FFF9` | yes | 131498 | 60353.9 | 2026-01-22 00:00:00 | S24 Strond | Hatchery |
| H2 | 64D0225A-59C0-424E-96CC-8A2674E5D6E5 | `A8AF5595-F89E-4853-8356-6DFF8B3562E5` | `A8AF5595-F89E-4853-8356-6DFF8B3562E5` | yes | 146195 | 85743.4 | 2026-01-22 00:00:00 | S24 Strond | Hatchery |
| H3 | 5025C727-D163-497A-9C14-5BBFC6736B97 | `4B57C78A-2273-4168-9581-5A66EE2AE8EA` | `4B57C78A-2273-4168-9581-5A66EE2AE8EA` | yes | 157677 | 68968.2 | 2026-01-22 00:00:00 | S24 Strond | Hatchery |
| H4 | D581DCDB-5F4F-4423-A6D1-3E872E1E9C2E | `C55327FC-14CC-4F30-A286-959E5D29487E` | `C55327FC-14CC-4F30-A286-959E5D29487E` | yes | 151467 | 74858.4 | 2026-01-22 00:00:00 | S24 Strond | Hatchery |
| I1 | 6D5F9BAE-166A-4A37-B5FD-42565AFA9256 | `27143FD9-F838-4CA3-A9C9-174C5D7B8620` | `27143FD9-F838-4CA3-A9C9-174C5D7B8620` | yes | 123760 | 44082.2 | 2026-01-22 00:00:00 | S24 Strond | Hatchery |
| I2 | 59E1DAC8-9F21-4ADB-9161-DD5350184421 | `972321A9-8AC8-40EB-ADF6-2B28E4EE66C2` | `972321A9-8AC8-40EB-ADF6-2B28E4EE66C2` | yes | 122676 | 27089.6 | 2026-01-22 00:00:00 | S24 Strond | Hatchery |
| I3 | C637A5E2-53CA-4B79-96AC-36ED5380E328 | `25C70360-4D85-4C3C-AA7C-77F935A6366C` | `25C70360-4D85-4C3C-AA7C-77F935A6366C` | yes | 125823 | 18772.0 | 2026-01-22 00:00:00 | S24 Strond | Hatchery |
| J1 | C0D63A28-8E98-47CF-9271-CB58CBA7F240 | `74BD8BBB-D9E0-4383-BC3A-B2F58047735E` | `74BD8BBB-D9E0-4383-BC3A-B2F58047735E` | yes | 149794 | 69083.8 | 2026-01-22 00:00:00 | S24 Strond | Hatchery |
| J2 | 3BFCC01C-BCA1-4472-A53D-48CA4DDAFFF2 | `19A46CC3-7DC6-417D-B42E-9154D61A40FC` | `19A46CC3-7DC6-417D-B42E-9154D61A40FC` | yes | 153047 | 52168.7 | 2026-01-22 00:00:00 | S24 Strond | Hatchery |
| J3 | A3E66323-A9A1-4C9A-9A0D-3088BA90D8BE | `94AD1B24-52A1-464B-8A05-5A2D54998B86` | `94AD1B24-52A1-464B-8A05-5A2D54998B86` | yes | 158217 | 44687.3 | 2026-01-22 00:00:00 | S24 Strond | Hatchery |
| J4 | 5795805D-A47F-43FC-BC2F-3CD520C89062 | `1A406CCD-00B1-41D2-B558-05D6AC2A2B91` | `1A406CCD-00B1-41D2-B558-05D6AC2A2B91` | yes | 156453 | 62610.1 | 2026-01-22 00:00:00 | S24 Strond | Hatchery |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 1) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)