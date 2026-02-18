# Semantic Migration Validation Report

- Component key: `D6F4E237-C220-4DC8-9660-026D3871FFD6`
- Batch: `SF APR 25` (id=506)
- Populations: 78
- Window: 2025-04-30 14:01:38 → 2026-01-22 23:59:59.999999 (uncapped end 2026-02-17 13:47:18.230254, cap 2026-01-22 23:59:59.999999)

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 415 | 415 | 0.00 |
| Feeding kg | 5239.87 | 5239.87 | 0.00 |
| Mortality events | 876 | 871 | 5.00 |
| Mortality count | 22346 | 22346 | 0.00 |
| Mortality biomass kg | 0.00 | 5.46 | -5.46 |
| Culling events | 815 | 815 | 0.00 |
| Culling count | 100171 | 100171 | 0.00 |
| Culling biomass kg | 131719.04 | 131719.01 | 0.03 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 159 | 159 | 0.00 |
| Growth samples | 5 | 5 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 122517
- Stage-entry window used for transition sanity: 2 day(s)
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 0
- Assignment zero-count rows (population_count <= 0): 9 total, 9 bridge-classified, 0 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 21.
- Fishgroup classification: 10 temporary bridge fishgroups, 49 real stage-entry fishgroups, 10 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 1530757 | 2155569 | 3021920 | 4851815 | 3.17 | 1.61 | 2025-04-30 | 2025-05-02 | 49 | 49 | 0 | 69 | 78 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `251.0052`, `251.0053`, `251.0055`, `251.0056`, `251.0059`, `251.0061`, `251.0063`, `251.0066`, `251.0071`, `251.0078`
- Real stage-entry fishgroup examples: `251.0002`, `251.0003`, `251.0004`, `251.0005`, `251.0006`, `251.0007`, `251.0008`, `251.0009`, `251.0010`, `251.0011`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 78 | 78 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 1325606 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 47

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 43 | FreshWater:43 | FW24 KinlochMoidart:43 |
| SourcePopBefore -> SourcePopAfter | 4 | FreshWater:4 | FW24 KinlochMoidart:4 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 47 | 0 | FreshWater:47 | FW24 KinlochMoidart:47 | Unknown:47 |
| Reachable outside descendants | 47 | 0 | FreshWater:47 | FW24 KinlochMoidart:47 | Unknown:47 |

### Active Container Latest Holder Evidence

- For each currently active migrated assignment container, this shows the latest non-zero status holder in source data.
- Containers checked: 31; latest holder in selected component: 31; latest holder outside selected component: 0; unknown latest holder: 0.

| Container | Source container id | Component population | Latest holder population | Latest holder in selected component | Latest count | Latest biomass kg | Latest status time | Site | Prod stage |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| CH1.08 | E847ABB7-D14E-4F87-852A-EF906F2015C2 | `BAA5AB95-24F1-48BB-BC29-FA695AE06B73` | `BAA5AB95-24F1-48BB-BC29-FA695AE06B73` | yes | 30809 | 1.54 | 2025-07-31 12:02:51 | FW24 KinlochMoidart | FreshWater |
| CH2.08 | F3B53ECB-FD00-4593-9167-D6B8827AAFF8 | `DABBA46F-133E-44FC-98A5-8266783C462C` | `DABBA46F-133E-44FC-98A5-8266783C462C` | yes | 30741 | 1.54 | 2025-07-31 12:02:51 | FW24 KinlochMoidart | FreshWater |
| CH3.08 | DE96EC3C-ADB0-4D7E-924B-DB0F9A309093 | `456AFC04-56C3-4692-B3C6-53D6E0730328` | `456AFC04-56C3-4692-B3C6-53D6E0730328` | yes | 30774 | 1.54 | 2025-07-31 12:02:51 | FW24 KinlochMoidart | FreshWater |
| CH4.08 | EE558714-F1B7-4066-8A33-9B7E8B474B78 | `BB0D1A78-A77A-435D-B668-B30324C4253B` | `BB0D1A78-A77A-435D-B668-B30324C4253B` | yes | 30820 | 1.54 | 2025-07-31 12:02:51 | FW24 KinlochMoidart | FreshWater |
| CH5.08 | 3B4958CC-6CE2-44A3-ABA8-437592365BDD | `0A7EC9EB-4EF6-4BBF-90F4-4FE0D26E9AFE` | `0A7EC9EB-4EF6-4BBF-90F4-4FE0D26E9AFE` | yes | 30804 | 1.54 | 2025-07-31 12:02:51 | FW24 KinlochMoidart | FreshWater |
| CH6.02 | EA7DB48C-EA36-4F24-974C-2BDAE8E68D85 | `121EAED4-6E9A-40E0-B6D8-D1A6CD3669AF` | `121EAED4-6E9A-40E0-B6D8-D1A6CD3669AF` | yes | 30712 | 1.54 | 2025-07-31 12:02:51 | FW24 KinlochMoidart | FreshWater |
| CH6.03 | 9DF75700-883B-4381-9E84-E426EAC756D1 | `34C64A97-D478-464D-A712-1B35A175C788` | `34C64A97-D478-464D-A712-1B35A175C788` | yes | 30720 | 1.54 | 2025-07-31 12:02:51 | FW24 KinlochMoidart | FreshWater |
| CH6.04 | 01D0D7D2-1C3B-48A8-AF34-D8D0D1799419 | `946EBEC4-76A7-423D-9EF4-C4529C7AA9C8` | `946EBEC4-76A7-423D-9EF4-C4529C7AA9C8` | yes | 30785 | 1.54 | 2025-07-31 12:02:51 | FW24 KinlochMoidart | FreshWater |
| CH6.05 | 35013F65-92A6-4B32-BF41-93B0B4ADBD91 | `185CB38F-7856-46C5-B2FB-1F262A8F3175` | `185CB38F-7856-46C5-B2FB-1F262A8F3175` | yes | 30859 | 1.54 | 2025-07-31 12:02:51 | FW24 KinlochMoidart | FreshWater |
| CH6.06 | 5863EE5C-9D61-47EB-9C2C-5E02DE551F84 | `393C0DB8-60E5-4A56-980C-96547D5F83F2` | `393C0DB8-60E5-4A56-980C-96547D5F83F2` | yes | 30798 | 1.54 | 2025-07-31 12:02:51 | FW24 KinlochMoidart | FreshWater |
| CH6.07 | 307784D9-1D18-4D4B-952A-6290089854AB | `9F4F3A67-3328-46D5-B181-240CE8029BE6` | `9F4F3A67-3328-46D5-B181-240CE8029BE6` | yes | 30740 | 1.54 | 2025-07-31 12:02:51 | FW24 KinlochMoidart | FreshWater |
| CH6.08 | 30D9415B-F145-4481-97B9-B2A075D5D722 | `DC523F46-98A5-4C8C-949A-BB0DB98DF24F` | `DC523F46-98A5-4C8C-949A-BB0DB98DF24F` | yes | 30800 | 1.54 | 2025-07-31 12:02:51 | FW24 KinlochMoidart | FreshWater |
| CH7.02 | 9F973ABC-C10A-4E64-A4E8-61F4AFF06BF4 | `81AF26D8-3A5F-410E-BD3B-DCD2BAEB220E` | `81AF26D8-3A5F-410E-BD3B-DCD2BAEB220E` | yes | 30872 | 1.54 | 2025-07-31 12:02:51 | FW24 KinlochMoidart | FreshWater |
| CH7.03 | 54F06B86-D2BA-489B-9631-50DE5BC3617F | `048D548D-62DF-470C-BB83-DA09F7EC7A97` | `048D548D-62DF-470C-BB83-DA09F7EC7A97` | yes | 30854 | 1.54 | 2025-07-31 12:02:51 | FW24 KinlochMoidart | FreshWater |
| CH7.04 | 6E4557A2-B4AC-474C-8E5F-B92B552EC57F | `AAE4FBA0-A953-4540-BB44-487B0C22F4D2` | `AAE4FBA0-A953-4540-BB44-487B0C22F4D2` | yes | 30721 | 1.54 | 2025-07-31 12:02:51 | FW24 KinlochMoidart | FreshWater |
| CH7.05 | 7A2DC153-B2C6-4E88-B118-C49C510EBBF2 | `4EF02E97-C995-4466-978C-0B54666CB455` | `4EF02E97-C995-4466-978C-0B54666CB455` | yes | 30762 | 1.54 | 2025-07-31 12:02:51 | FW24 KinlochMoidart | FreshWater |
| CH7.06 | 26B5325A-5F40-4B98-A0B8-57D29CD86BA0 | `7B359C9B-3369-4B21-980E-7A8B80DCF4D9` | `7B359C9B-3369-4B21-980E-7A8B80DCF4D9` | yes | 30641 | 1.53 | 2025-07-31 12:02:51 | FW24 KinlochMoidart | FreshWater |
| CH7.07 | 6B1FB348-830F-404F-8AE9-D8ACCBC5C606 | `29641B36-A643-430A-82E9-DADF99829C2D` | `29641B36-A643-430A-82E9-DADF99829C2D` | yes | 30768 | 1.54 | 2025-07-31 12:02:51 | FW24 KinlochMoidart | FreshWater |
| CH7.08 | 0F48C515-2F8E-40C5-BBBF-8051F011CFFC | `32E1E5BC-5C0B-4453-A581-081EC78C60E4` | `32E1E5BC-5C0B-4453-A581-081EC78C60E4` | yes | 15116 | 0.76 | 2025-07-31 12:02:51 | FW24 KinlochMoidart | FreshWater |
| FT03 | BF3C4402-61F3-4D68-9D12-04329F799EC2 | `F87AD6BC-BCC9-441A-830A-723C8F2FF568` | `F87AD6BC-BCC9-441A-830A-723C8F2FF568` | yes | 156665 | 1611.45 | 2025-12-18 15:53:00 | FW24 KinlochMoidart | FreshWater |
| FT04 | 30334C89-B0CB-464E-AF53-14B4F967E455 | `8AA843B6-D7D7-44CC-8E3D-19BEE4C6300B` | `8AA843B6-D7D7-44CC-8E3D-19BEE4C6300B` | yes | 156191 | 2453.49 | 2026-01-20 12:45:24 | FW24 KinlochMoidart | FreshWater |
| FT05 | 7FA9633F-B966-4C54-A2E2-9D4CD9164FBB | `73790D39-6BB3-4209-8270-162CFB025069` | `73790D39-6BB3-4209-8270-162CFB025069` | yes | 156855 | 2536.71 | 2026-01-21 12:46:02 | FW24 KinlochMoidart | FreshWater |
| FT06 | 3AC5B51C-44BA-4FFE-AD97-F087D20A07DD | `5736863F-8F2E-49E0-8CB2-DAB2B29D3617` | `5736863F-8F2E-49E0-8CB2-DAB2B29D3617` | yes | 156827 | 2544.79 | 2026-01-22 00:00:00 | FW24 KinlochMoidart | FreshWater |
| FT08 | 0AAAB62E-F0DC-46D7-A64A-FEBB4E7284A1 | `87D9C185-B39D-46F9-83BF-0B9223213B02` | `87D9C185-B39D-46F9-83BF-0B9223213B02` | yes | 156755 | 1611.42 | 2025-12-18 15:53:00 | FW24 KinlochMoidart | FreshWater |
| FT09 | 5D71BA48-4F01-4FC2-8E6C-061C8968183D | `65E9A8A2-6564-4104-A7F3-3D724E629420` | `65E9A8A2-6564-4104-A7F3-3D724E629420` | yes | 156723 | 1667.01 | 2025-12-24 09:56:09 | FW24 KinlochMoidart | FreshWater |
| FT10 | 7E117397-621B-41D2-BFF3-131C576D4806 | `D06EF877-5D07-4747-9A1B-CE81F56C5CED` | `D06EF877-5D07-4747-9A1B-CE81F56C5CED` | yes | 155737 | 2348.77 | 2026-01-19 12:43:38 | FW24 KinlochMoidart | FreshWater |
| FT11 | 12652119-4BF0-4D95-93F0-E653459733EB | `89D8F183-3342-4183-A8B8-F523B173CC9C` | `89D8F183-3342-4183-A8B8-F523B173CC9C` | yes | 156361 | 2395.02 | 2026-01-22 00:00:00 | FW24 KinlochMoidart | FreshWater |
| FT12 | 283461F0-89AA-4DDE-A3D6-C5E5CF225A02 | `62E85D6D-F0FE-4A7D-9339-CD6925EF2EDA` | `62E85D6D-F0FE-4A7D-9339-CD6925EF2EDA` | yes | 156833 | 2438.9 | 2026-01-22 00:00:00 | FW24 KinlochMoidart | FreshWater |
| RC21 | FEAFF3ED-72CD-4EC0-AF99-FB775F667574 | `118162A0-591B-4AF2-8608-967D0FF45E59` | `118162A0-591B-4AF2-8608-967D0FF45E59` | yes | 310192 | 5014.99 | 2026-01-22 00:00:00 | FW24 KinlochMoidart | FreshWater |
| RC22 | 9D7744D8-D36E-46EF-BAD8-897D83B0EE51 | `851A1A11-DAE7-430D-BAC4-9164DC2792C2` | `851A1A11-DAE7-430D-BAC4-9164DC2792C2` | yes | 313046 | 4990.2 | 2026-01-22 00:00:00 | FW24 KinlochMoidart | FreshWater |
| RC24 | 3807B887-8267-4CF2-8121-89927B1D0221 | `F41A0558-CC4D-407A-B556-F0F17298CB95` | `F41A0558-CC4D-407A-B556-F0F17298CB95` | yes | 311559 | 4767.84 | 2026-01-22 00:00:00 | FW24 KinlochMoidart | FreshWater |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)