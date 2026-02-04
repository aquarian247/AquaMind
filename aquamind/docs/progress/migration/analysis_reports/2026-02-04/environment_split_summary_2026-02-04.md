# Environment Split Summary (FW vs Sea)

Date: 2026-02-04
Source: live query against `Populations`, `FishGroupHistory`, `Ext_GroupedOrganisation_v2`
Classification uses `Ext_GroupedOrganisation_v2.ProdStage`:
- **Sea**: `MarineSite`
- **Freshwater**: `Hatchery`, `FreshWater`, `SmoltProduction`, `BroodStock`
- **Other**: NULL/Undefined

## Sea population coverage

- Sea populations (MarineSite): **24,291**
- Sea populations with InputProjectID: **23,816** (~**98.04%**)

This means sea cohorts can be grouped by `InputProjectID` similarly to FW.

## InputProject environment mix

Counts of `InputProjectID` by environment presence:

| Category | Count |
|---|---|
| Projects with both FW and Sea populations | 29 |
| Projects with only FW populations | 681 |
| Projects with only Sea populations | 1,346 |
| Projects with OTHER/unknown populations | 29 |

Notes
- Some `Site` labels beginning with `S` are actually `MarineSite` in `ProdStage`, so **site prefix alone is not sufficient** for classification.
- Environment splitting by `ProdStage` is the safest deterministic approach for a parallel replay strategy.

