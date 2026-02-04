# FW->Sea (MarineSite) transfer scan - Ext_Transfers_v2

Date: 2026-01-30

## Scope
- Source: `scripts/migration/data/extract/ext_transfers.csv` with joins to `populations.csv`, `grouped_organisation.csv`, `fish_group_history.csv`, `input_projects.csv`, `org_units.csv`.
- Filter: `SourcePop` in FW stages (FreshWater/SmoltProduction/Hatchery/BroodStock) -> `DestPop` in `MarineSite`.

## Summary
- FW->MarineSite edges found: **283**
- Unique FW cohorts (InputProjects): **15**
- FW SourcePop rows with `Ext_Inputs_v2` match: **0** (all FW->Marine edges require `FishGroupHistory -> InputProjects` for identity)

## Cohort list (grouped by InputProject)
| ProjectName | YearClass | ProjectNumber | FW Site | InputProjectID | Edge count | Dest sites (unique) |
|---|---:|---:|---|---|---:|---|
| Salmobreed/Bolaks | 2011 | 0 | FW12 Amhuinnsuidhe | 1AA9D619-0E59-427F-BD95-1916E50A22F8 | 36 | N112 Taranaish, N122 VuiaMor |
| Salmobreed/Bolaks | 2011 | 1 | FW12 Amhuinnsuidhe | CC3982E7-2753-4A51-A8C9-DE371E496E3A | 34 | N332 PetersportNorth, N612 Kenmore, N613 Aird |
| SalmoBreed/Bolaks | 2011 | 0 | FW13 Geocrab | 14C535C4-0E23-4CCC-BBD6-596BC64ED506 | 30 | GravirInner, N112 Taranaish, N221 TrilleachanMor, S341 GobaBharra, VuiaBeag |
| SalmoBreed/Bolaks | 2010 | 2 | FW11 Barvas | B685C0CF-FCA5-4BAD-9AF2-B0715B9D2971 | 28 | GravirInner, VuiaBeag |
| Salmobreed/Bolaks | 2011 | 1 | FW22 Russel Burn | CF627E64-E1C3-4D65-AF87-D373064B4639 | 26 | Gousam, GravirInner, N111 Eughlam, N122 VuiaMor, S412 Strone, S421 Lamlash, Strome |
| Salmobreed/Bolaks | 2010 | 0 | FW22 Russel Burn | 1A8AFC1D-A46B-4A02-B81E-6570959F1F28 | 25 | Gousam, S222 DruimyeonBay, Strome |
| 11S0SB | 2011 | 2 | FW22 Russel Burn | F01454DE-A328-48B6-A938-C9BF61020735 | 21 | S321 Ardgaddan, S322 StrondoirBay, S331 GlenanBay, S343 TarbertSouth |
| 12S1SB | 2012 | 2 | Tullich | 18F19976-545F-4596-A4B9-FEF8565B20E8 | 19 | N621 Portree, S321 Ardgaddan, S331 GlenanBay |
| salmoBreed/Bolaks | 2011 | 1 | FW11 Barvas | B29FE1BD-F6F6-45B0-A298-1ABBD7513B71 | 18 | S342 MeallMhor |
| SalmoBreed/Bolaks | 2011 | 0 | FW11 Barvas | 28176346-2B49-4EB6-AF0A-81A0F3F61ABA | 14 | N112 Taranaish, VuiaBeag |
| SalmoBreed/Bolaks | 2011 | 1 | FW13 Geocrab | 62B0D40A-4258-421F-A6C2-F9295A9E2F7F | 12 | N222 Plocrapol, N613 Aird, N621 Portree |
| 11S0SB PD | 2011 | 3 | FW22 Russel Burn | D6A90190-401E-47CF-A68B-B6316806BA83 | 10 | S321 Ardgaddan, S322 StrondoirBay, S343 TarbertSouth |
| SalmoBreed/Bolaks | 2011 | 2 | FW11 Barvas | 06EF92C5-02BD-496B-AA76-BDF140800167 | 7 | N323 Uiskevagh |
| Landcatch | 2011 | 0 | FW22 Russel Burn | 01E16F72-A919-41A6-8F83-4792D8446D38 | 2 | S412 Strone |
| Trout | 2014 | 0 | Loch Geirean | D37F664B-5F7F-4EF6-A092-4723C608A51B | 1 | N321 Grimsay |

## Sample edges (one per cohort)
- **Salmobreed/Bolaks** (YearClass 2011, ProjectNumber 0, FW site FW12 Amhuinnsuidhe, InputProjectID 1AA9D619-0E59-427F-BD95-1916E50A22F8)
  - SourcePop `3DCB1B1C-3C98-4B4E-92FC-0130B6BF71E3` (FW12 Amhuinnsuidhe, Hatchery) -> DestPop `65892314-C1CE-4E2A-BD8D-F8529AD04615` (N122 VuiaMor, MarineSite); Count 18872, BiomassKg 1344.44
- **Salmobreed/Bolaks** (YearClass 2011, ProjectNumber 1, FW site FW12 Amhuinnsuidhe, InputProjectID CC3982E7-2753-4A51-A8C9-DE371E496E3A)
  - SourcePop `987E7621-F508-47CF-A238-12B1B0BBCA77` (FW12 Amhuinnsuidhe, Hatchery) -> DestPop `4BC0077D-76F9-4659-B418-AB428D3EE6DA` (N332 PetersportNorth, MarineSite); Count 9305, BiomassKg 812.028
- **SalmoBreed/Bolaks** (YearClass 2011, ProjectNumber 0, FW site FW13 Geocrab, InputProjectID 14C535C4-0E23-4CCC-BBD6-596BC64ED506)
  - SourcePop `32D3A5FC-5337-436D-BE2F-459FEF6B0346` (FW13 Geocrab, Hatchery) -> DestPop `5D9A129E-9B01-485C-A00C-8483549CC3C0` (VuiaBeag, MarineSite); Count 56200, BiomassKg 6279.68
- **SalmoBreed/Bolaks** (YearClass 2010, ProjectNumber 2, FW site FW11 Barvas, InputProjectID B685C0CF-FCA5-4BAD-9AF2-B0715B9D2971)
  - SourcePop `3D3F6E8A-8A57-4F5D-90D2-04021E9A6084` (FW11 Barvas, Hatchery) -> DestPop `E5DFCD0F-DE34-4413-AD2F-B3158C5062F4` (GravirInner, MarineSite); Count 12323, BiomassKg 847.893
- **Salmobreed/Bolaks** (YearClass 2011, ProjectNumber 1, FW site FW22 Russel Burn, InputProjectID CF627E64-E1C3-4D65-AF87-D373064B4639)
  - SourcePop `EA1CC93B-9A23-4CD7-A72F-0ADAA8ADF6AF` (FW22 Russel Burn, Hatchery) -> DestPop `F52CE676-7DF7-43E0-BE87-54A7212DCD97` (Strome, MarineSite); Count 83148, BiomassKg 5479.45
- **Salmobreed/Bolaks** (YearClass 2010, ProjectNumber 0, FW site FW22 Russel Burn, InputProjectID 1A8AFC1D-A46B-4A02-B81E-6570959F1F28)
  - SourcePop `77B63840-FD7D-439D-B840-0B2448839720` (FW22 Russel Burn, Hatchery) -> DestPop `E56D204B-637D-4F4B-979A-07E65C62EF31` (S222 DruimyeonBay, MarineSite); Count 60199, BiomassKg 3912.94
- **11S0SB** (YearClass 2011, ProjectNumber 2, FW site FW22 Russel Burn, InputProjectID F01454DE-A328-48B6-A938-C9BF61020735)
  - SourcePop `9215F4B6-6CF6-4A1B-852B-11044DCEC421` (FW22 Russel Burn, Hatchery) -> DestPop `6656B49F-4304-4565-B6DD-4F78C4F337AA` (S321 Ardgaddan, MarineSite); Count 78200, BiomassKg 5936.51
- **12S1SB** (YearClass 2012, ProjectNumber 2, FW site Tullich, InputProjectID 18F19976-545F-4596-A4B9-FEF8565B20E8)
  - SourcePop `FAC441A1-FA2F-4AB6-A5C2-15C161546631` (FW22 Russel Burn, Hatchery) -> DestPop `22B8FB1C-175C-4036-8B7F-4F73065F01AA` (S321 Ardgaddan, MarineSite); Count 26234, BiomassKg 1701.68
- **salmoBreed/Bolaks** (YearClass 2011, ProjectNumber 1, FW site FW11 Barvas, InputProjectID B29FE1BD-F6F6-45B0-A298-1ABBD7513B71)
  - SourcePop `7E3D7D8A-3974-4485-84ED-198D447CA860` (FW11 Barvas, Hatchery) -> DestPop `4D45BF1D-9852-47AB-853C-4844300EF8C3` (S342 MeallMhor, MarineSite); Count 17125, BiomassKg 1153.14
- **SalmoBreed/Bolaks** (YearClass 2011, ProjectNumber 0, FW site FW11 Barvas, InputProjectID 28176346-2B49-4EB6-AF0A-81A0F3F61ABA)
  - SourcePop `8084AA83-122F-44AB-9A3E-0FE99FB08A05` (FW11 Barvas, Hatchery) -> DestPop `A15DFDA9-53DE-4052-AA06-BD00A389887E` (VuiaBeag, MarineSite); Count 3343, BiomassKg 241.365
- **SalmoBreed/Bolaks** (YearClass 2011, ProjectNumber 1, FW site FW13 Geocrab, InputProjectID 62B0D40A-4258-421F-A6C2-F9295A9E2F7F)
  - SourcePop `FE1BA35C-1388-4B70-B701-03194EA2875C` (FW13 Geocrab, Hatchery) -> DestPop `7EB1C310-EF67-4B05-8B8D-D82226B2AC75` (N222 Plocrapol, MarineSite); Count 59352, BiomassKg 5288.31
- **11S0SB PD** (YearClass 2011, ProjectNumber 3, FW site FW22 Russel Burn, InputProjectID D6A90190-401E-47CF-A68B-B6316806BA83)
  - SourcePop `CD778D1A-E460-4F30-A89F-46C932C100CC` (FW22 Russel Burn, Hatchery) -> DestPop `88AABD39-854D-4F08-B02B-EE823DED0A3A` (S322 StrondoirBay, MarineSite); Count 54945, BiomassKg 3956.04
- **SalmoBreed/Bolaks** (YearClass 2011, ProjectNumber 2, FW site FW11 Barvas, InputProjectID 06EF92C5-02BD-496B-AA76-BDF140800167)
  - SourcePop `24647C50-EA83-4A4A-B886-0A3AEF7EA53F` (FW14 Harris Lochs, SmoltProduction) -> DestPop `CA716C0E-C3BF-4978-9E9A-B0D3809CE5D4` (N323 Uiskevagh, MarineSite); Count 9322, BiomassKg 1118.64
- **Landcatch** (YearClass 2011, ProjectNumber 0, FW site FW22 Russel Burn, InputProjectID 01E16F72-A919-41A6-8F83-4792D8446D38)
  - SourcePop `840FBC96-1637-4C2E-A3C2-3C2C4EB2B7AD` (FW22 Russel Burn, Hatchery) -> DestPop `42AE4C5D-A366-4A08-A166-717C75240250` (S412 Strone, MarineSite); Count 56167, BiomassKg 5403.27
- **Trout** (YearClass 2014, ProjectNumber 0, FW site Loch Geirean, InputProjectID D37F664B-5F7F-4EF6-A092-4723C608A51B)
  - SourcePop `85115316-B0D7-4AAA-A03E-0C99D99D2014` (Loch Geirean, SmoltProduction) -> DestPop `CF02FA7D-1471-4C1D-9C08-244FC9CCE832` (N321 Grimsay, MarineSite); Count 5910, BiomassKg 653.055

## Canonical example (for mapping doc)
- InputProject: `Salmobreed/Bolaks` YearClass 2010, ProjectNumber 0, InputProjectID 1A8AFC1D-A46B-4A02-B81E-6570959F1F28
- Transfer: SourcePop `EA1CC93B-9A23-4CD7-A72F-0ADAA8ADF6AF` (FW22 Russel Burn, Hatchery) -> DestPop `F52CE676-7DF7-43E0-BE87-54A7212DCD97` (Strome, MarineSite)
- `Ext_Transfers_v2`: TransferredCount 83148, TransferredBiomassKg 5479.45
