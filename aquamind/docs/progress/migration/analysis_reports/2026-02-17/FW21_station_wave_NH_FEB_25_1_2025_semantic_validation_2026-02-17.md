# Semantic Migration Validation Report

- Component key: `EB666567-9CBA-45D7-9149-053827161D0C`
- Batch: `NH FEB 25` (id=500)
- Populations: 216
- Window: 2025-02-12 10:15:00 → 2026-01-22 23:59:59.999999 (uncapped end 2026-02-17 10:03:51.718083, cap 2026-01-22 23:59:59.999999)

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 2906 | 2906 | 0.00 |
| Feeding kg | 20303.03 | 20303.03 | -0.00 |
| Mortality events | 4153 | 3978 | 175.00 |
| Mortality count | 602944 | 602944 | 0.00 |
| Mortality biomass kg | 0.00 | 450.41 | -450.41 |
| Culling events | 25 | 25 | 0.00 |
| Culling count | 349253 | 349253 | 0.00 |
| Culling biomass kg | 2544330.00 | 2544330.00 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 1107 | 1107 | 0.00 |
| Growth samples | 204 | 204 | 0.00 |
| Health journal entries | 1 | 1 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 952197
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 1/1 bridge-aware (100.0%), 0/1 entry-window (0.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 0
- Assignment zero-count rows (population_count <= 0): 1 total, 0 bridge-classified, 1 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 70.
- Fishgroup classification: 72 temporary bridge fishgroups, 47 real stage-entry fishgroups, 72 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 1455805 | 0 | 2926467 | 4871250 | 3.35 | 1.66 | 2025-02-12 | 2025-02-14 | 46 | 46 | 0 | 92 | 93 |
| Fry | 274314 | 1001699 | 1753268 | 5828370 | 21.25 | 3.32 | 2025-04-29 | 2025-05-01 | 1 | 1 | 0 | 123 | 123 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 35530 | 35530 | 0 | 1 | 1 | yes | Bridge-aware (direct edge linkage; linked sources: 1) | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `251.0093`, `251.0098`, `251.0115`, `251.0116`, `251.0117`, `251.0118`, `251.0120`, `251.0121`, `251.0122`, `251.0123`
- Real stage-entry fishgroup examples: `251.0002`, `251.0003`, `251.0004`, `251.0005`, `251.0006`, `251.0007`, `251.0008`, `251.0009`, `251.0010`, `251.0011`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 216 | 216 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 1546295 |
| Fry | 6511 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 88

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 55 | Hatchery:55 | FW21 Couldoran:55 |
| SourcePopBefore -> SourcePopAfter | 33 | Hatchery:33 | FW21 Couldoran:33 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 88 | 0 | Hatchery:88 | FW21 Couldoran:88 | Unknown:88 |
| Reachable outside descendants | 116 | 0 | Hatchery:116 | FW21 Couldoran:116 | Unknown:116 |

### Active Container Latest Holder Evidence

- For each currently active migrated assignment container, this shows the latest non-zero status holder in source data.
- Containers checked: 32; latest holder in selected component: 32; latest holder outside selected component: 0; unknown latest holder: 0.

| Container | Source container id | Component population | Latest holder population | Latest holder in selected component | Latest count | Latest biomass kg | Latest status time | Site | Prod stage |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| CA01 | 5A27E660-95EF-45F0-B478-A50A4392734B | `8E70690E-F0CE-4839-B17D-BB1F44BFA0E1` | `8E70690E-F0CE-4839-B17D-BB1F44BFA0E1` | yes | 12017 | 196.34 | 2025-12-15 12:04:09 | FW21 Couldoran | Hatchery |
| CA02 | 324D66C8-C9DF-4CB4-A912-1368CB90BA0F | `D7754D35-0F5F-4F8D-B094-C7D64E975F47` | `D7754D35-0F5F-4F8D-B094-C7D64E975F47` | yes | 7699 | 160.35 | 2025-12-16 15:25:10 | FW21 Couldoran | Hatchery |
| CA03 | 11790AF5-DFBB-45EE-AB86-C45D5D7307B9 | `EB6BFA3F-7644-4BC7-965D-6A587734EC5D` | `EB6BFA3F-7644-4BC7-965D-6A587734EC5D` | yes | 24382 | 456.31 | 2025-12-17 11:04:07 | FW21 Couldoran | Hatchery |
| CA05 | C5C226D6-ECC0-489D-B2F3-4B15AB9D906D | `8FCCFA78-9EC5-4E0A-99BD-2C5B3E6F8CE7` | `8FCCFA78-9EC5-4E0A-99BD-2C5B3E6F8CE7` | yes | 24501 | 483.12 | 2025-12-18 17:14:45 | FW21 Couldoran | Hatchery |
| CB05 | E1FE2841-4CA2-4882-87EC-01EC1C11D89A | `EF94BBA6-091D-4BE1-A891-FD4FE2F12F93` | `EF94BBA6-091D-4BE1-A891-FD4FE2F12F93` | yes | 24847 | 727.47 | 2025-12-12 16:16:48 | FW21 Couldoran | Hatchery |
| CC01 | 9EF06CCA-4B1B-43AA-95A5-109CF000BA68 | `F4935ACB-D966-4749-8092-88D8F5B2B567` | `F4935ACB-D966-4749-8092-88D8F5B2B567` | yes | 68717 | 2838.58 | 2026-01-22 00:00:00 | FW21 Couldoran | Hatchery |
| CC02 | 4641162D-60D6-456A-9E7F-45666B478ED2 | `1FFF67B0-DA03-49A6-856A-6E6E2D093C24` | `1FFF67B0-DA03-49A6-856A-6E6E2D093C24` | yes | 69045 | 2629.9 | 2026-01-22 00:00:00 | FW21 Couldoran | Hatchery |
| CC03 | 2761421B-E1F8-43DA-B45F-ED925F7D3404 | `D5A1B060-F34A-48E9-94A7-9414391DEA0F` | `D5A1B060-F34A-48E9-94A7-9414391DEA0F` | yes | 67945 | 2535.74 | 2026-01-22 00:00:00 | FW21 Couldoran | Hatchery |
| CC04 | E62938AF-1925-4A97-8449-65B037C84C03 | `D1423419-A407-4819-B856-54F9F88970B0` | `D1423419-A407-4819-B856-54F9F88970B0` | yes | 59462 | 2387.13 | 2026-01-22 00:00:00 | FW21 Couldoran | Hatchery |
| CD01 | 7D5ADC8D-D8A6-4430-8471-16695B2E6B13 | `259645E4-5F47-4956-AB6D-111D24C2E14C` | `259645E4-5F47-4956-AB6D-111D24C2E14C` | yes | 43401 | 941.78 | 2025-12-10 12:28:53 | FW21 Couldoran | Hatchery |
| CD03 | DA89260D-BA76-40D6-AC20-73D4670E695D | `6454726B-D74B-444C-9233-33A7A81F56C4` | `6454726B-D74B-444C-9233-33A7A81F56C4` | yes | 21154 | 533.77 | 2025-12-10 14:48:20 | FW21 Couldoran | Hatchery |
| CD04 | 19A376D8-691D-483D-B65E-9720871B46D6 | `AE1175E2-A989-4F10-A303-01B4A9FC3E18` | `AE1175E2-A989-4F10-A303-01B4A9FC3E18` | yes | 31939 | 813.2 | 2025-12-10 11:05:18 | FW21 Couldoran | Hatchery |
| CD05 | 93081285-99C7-465B-8ADA-CF81C4BA2E6F | `DAFA43E4-9344-49B2-9820-E700122077C2` | `DAFA43E4-9344-49B2-9820-E700122077C2` | yes | 27064 | 676.61 | 2025-12-11 08:59:32 | FW21 Couldoran | Hatchery |
| CD06 | AC0D82FB-3354-4F43-BBF2-94584F4A94BD | `E894A338-CB89-4EFD-9B05-F447B438FE19` | `E894A338-CB89-4EFD-9B05-F447B438FE19` | yes | 29507 | 605.94 | 2025-12-10 09:45:25 | FW21 Couldoran | Hatchery |
| CD07 | 94AACCC0-7535-4B8D-B5DB-F71843C5E1B9 | `4CE2C94A-86D8-4FCB-B473-7A20F9352C50` | `4CE2C94A-86D8-4FCB-B473-7A20F9352C50` | yes | 33489 | 876.09 | 2025-12-09 09:29:37 | FW21 Couldoran | Hatchery |
| CD08 | 828945AB-A9B4-4241-B844-7EF3B0B90C82 | `737F425B-FED7-4931-9F03-BB48B7DBA53B` | `737F425B-FED7-4931-9F03-BB48B7DBA53B` | yes | 33489 | 876.09 | 2025-12-09 09:29:37 | FW21 Couldoran | Hatchery |
| CE03 | 6F063E87-F489-48EA-A95E-3836231608B8 | `E9BBF697-F81A-4BF9-B5CE-6946583C9F08` | `E9BBF697-F81A-4BF9-B5CE-6946583C9F08` | yes | 90000 | 741.86 | 2025-09-16 17:01:20 | FW21 Couldoran | Hatchery |
| CE07 | B5465D6F-ED28-43E2-BF61-D88F63608AC3 | `30A1F00C-0851-4DB2-8EDA-E35DA447E628` | `30A1F00C-0851-4DB2-8EDA-E35DA447E628` | yes | 25458 | 581.35 | 2025-12-11 11:41:11 | FW21 Couldoran | Hatchery |
| CE08 | EBB2D528-E5C5-4EC5-B210-39C144454421 | `3B3FB0C5-34B3-4C8F-8A11-1CDEE93F3567` | `3B3FB0C5-34B3-4C8F-8A11-1CDEE93F3567` | yes | 56587 | 717.19 | 2025-09-23 11:24:26 | FW21 Couldoran | Hatchery |
| CE09 | 88812444-EB65-4970-A714-20553D0CE8A2 | `A71B8639-661A-4F34-95F7-DD2C31207033` | `A71B8639-661A-4F34-95F7-DD2C31207033` | yes | 25735 | 756.8 | 2025-12-11 12:53:22 | FW21 Couldoran | Hatchery |
| CE10 | 2AEA7641-AAD0-4A2F-B2FB-D6504E8B3C33 | `CC42FFE1-D9DE-4251-8330-FEAAC222AD7A` | `CC42FFE1-D9DE-4251-8330-FEAAC222AD7A` | yes | 22835 | 694.67 | 2025-12-11 15:01:13 | FW21 Couldoran | Hatchery |
| CE11 | 2F2D8984-E8D4-428A-AA0B-D967C37DE9B8 | `D0EB2E18-E858-4694-8B5F-8F78E9605C6C` | `D0EB2E18-E858-4694-8B5F-8F78E9605C6C` | yes | 24223 | 629.29 | 2025-12-11 14:01:05 | FW21 Couldoran | Hatchery |
| CR01 | CCB09475-EF13-41DD-BA28-F1C952754B62 | `20B89574-56EB-4CA4-A757-00DA2E21F150` | `20B89574-56EB-4CA4-A757-00DA2E21F150` | yes | 96255 | 2368.98 | 2026-01-22 00:00:00 | FW21 Couldoran | Hatchery |
| CR02 | 37380E55-06B8-4E50-BBCB-B0C6C1A449FB | `337A69E1-6194-4C74-A5D7-3B5564C89C56` | `337A69E1-6194-4C74-A5D7-3B5564C89C56` | yes | 47295 | 1891.8 | 2026-01-15 17:20:21 | FW21 Couldoran | Hatchery |
| CR03 | 8F942DF8-FE5C-4395-9F87-FEA044135ADC | `061D2B7E-EC1D-43DD-A299-648CAB3AAB21` | `061D2B7E-EC1D-43DD-A299-648CAB3AAB21` | yes | 12549 | 447.06 | 2026-01-14 17:19:19 | FW21 Couldoran | Hatchery |
| CR04 | 1B94D87A-F852-4C16-AFF1-4444B65A69C0 | `17240E25-DF39-4745-8BC6-5F4136920B9D` | `17240E25-DF39-4745-8BC6-5F4136920B9D` | yes | 135757 | 2836.15 | 2026-01-22 00:00:00 | FW21 Couldoran | Hatchery |
| CR05 | 0AFC1E8D-C310-4A6D-B4C2-E131B9E831F2 | `239AB8C9-04B8-482E-93CA-AEA4DBB62788` | `239AB8C9-04B8-482E-93CA-AEA4DBB62788` | yes | 39395 | 1356.25 | 2026-01-22 12:46:55 | FW21 Couldoran | Hatchery |
| CR06 | A9FF6558-CF6E-4376-8A16-ADA457BD4E49 | `1F8F88CE-EA11-48A4-B8AD-4F5B30BF13F5` | `54EB4030-B52B-446D-9FC7-0F5245C04D2E` | yes | 39396 | 1356.28 | 2026-01-22 12:46:55 | FW21 Couldoran | Hatchery |
| CR07 | DA2EF724-84A3-4A1F-B195-AC20D9244331 | `AA218394-804D-46F1-8E4F-E6732EC76387` | `AA218394-804D-46F1-8E4F-E6732EC76387` | yes | 56473 | 1374.53 | 2026-01-22 00:00:00 | FW21 Couldoran | Hatchery |
| CR08 | CF9D26E0-44D7-429D-863A-EE62D806E106 | `CE549AF6-C673-4191-880E-8D9EB18816D5` | `CE549AF6-C673-4191-880E-8D9EB18816D5` | yes | 56588 | 1377.33 | 2026-01-22 00:00:00 | FW21 Couldoran | Hatchery |
| CR09 | 20D6D4D9-A75B-471C-9A8C-6B7FBD91D443 | `13C357C2-5BB3-4355-8ADA-7CB4506F9987` | `13C357C2-5BB3-4355-8ADA-7CB4506F9987` | yes | 38663 | 1297.97 | 2026-01-22 00:00:00 | FW21 Couldoran | Hatchery |
| CR10 | 1D56587F-D695-43F4-9CBF-EF225C9DE282 | `EB5D2D3C-5B8C-4B83-8430-6C6992CB0387` | `EB5D2D3C-5B8C-4B83-8430-6C6992CB0387` | yes | 38774 | 1329.15 | 2026-01-22 00:00:00 | FW21 Couldoran | Hatchery |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)