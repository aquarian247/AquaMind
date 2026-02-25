# Handoff: Infra Classification + Hall Flattening Remediation

Date: 2026-02-19  
Status: Applied on migration-safe DB, code guards added for future reruns

## Why this handoff exists

User-reported infra integrity issue:
- Faroe freshwater station inventory included marine `A*` rows and GUID-like station names.
- S16-style nested FishTalk hierarchy (`Hall -> Skáp -> Tray`) appeared to leak into AquaMind hall structure.

## What was changed

### Code guards (future migrations)

- `scripts/migration/tools/pilot_migrate_component.py`
  - strengthened site-code + prod-stage bucket inference (`A*`/`N*`/`S###` sea guards),
  - removed implicit freshwater fallback for unresolved rows,
  - station identity now scoped by `(name, geography)` to prevent cross-geography collisions,
  - station type inference helper added (`L*`/`BRS*` -> broodstock),
  - geography fallback includes site-code heuristic.

- `scripts/migration/loaders/infrastructure.py`
  - aligned geography and bucket inference with site-code heuristics,
  - removed hall-label freshwater fallback for unresolved environment bucket,
  - station lookup now uses `(name, geography)`,
  - station type inference helper added.

- `scripts/migration/tools/pilot_migrate_infrastructure.py`
  - station lookup keyed by `(name, geography)`,
  - site-code bucket inference helper added,
  - `hall_label_from_official` now strips tray/rack suffix after `;` (prevents hall explosion).

- `scripts/migration/tools/remediate_misclassified_infrastructure.py` (new)
  - migrates marine containers from hall/station context to area context,
  - reassigns station geography only on unanimous source evidence,
  - normalizes semicolon-suffixed halls to canonical hall names and cleans orphan hall rows,
  - emits report artifacts (md/json).

### Documentation update

- `aquamind/docs/progress/migration/DATA_MAPPING_DOCUMENT.md`
  - chapter 2 now explicitly documents:
    - site-code fallback geography rules,
    - no persistent `AreaGroup` hierarchy in AquaMind,
    - `Hall -> Skáp -> Tray` flattening to `Hall -> Container`,
    - no implicit hall-label freshwater fallback.

## Execution artifacts

- Consolidated ledger:
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-19/marine_infra_misclassification_remediation_execution_2026-02-19.md`
- Tool output snapshot (latest run state):
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-19/marine_infra_station_area_remediation_2026-02-19.md`
  - `aquamind/docs/progress/migration/analysis_reports/2026-02-19/marine_infra_station_area_remediation_2026-02-19.json`

## Post-remediation state (migration-safe DB)

- `A*` Faroe stations: `0`
- GUID-like Faroe stations: `0`
- `A03 Svínáir` exists as `Area`, not `FreshwaterStation`
- Semicolon hall artifacts: `0`
- S16 hall structure reduced to canonical hall names (no `A Høll;NNNNN` rows)
- Faroe `S*` stations present: `7` (`S03`, `S04`, `S08`, `S10`, `S16`, `S21`, `S24`)

## Residual decision needed

Remaining non-`S*` Faroe stations (`H01`, `H125`, `L01`, `L02`, `Temp`) are no longer marine misclassifications.  
Need domain decision whether to:
1) keep as valid non-`S*` land/broodstock entities, or  
2) reclassify/exclude from station inventory policy.

