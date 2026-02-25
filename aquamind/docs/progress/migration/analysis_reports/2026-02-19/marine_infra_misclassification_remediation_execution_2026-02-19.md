# Marine Infrastructure Misclassification Remediation (Execution Ledger)

Date: 2026-02-19  
Environment: migration-safe DB (`configure_migration_environment` + migration DB guard)

## Scope

Correct infrastructure drift where marine/grouped hierarchy rows were materialized as freshwater stations/halls, and normalize hall labels that leaked tray/rack suffixes from FishTalk identifiers.

## Execution Summary

1. **Initial dry-run plan** (`remediate_misclassified_infrastructure.py`)
   - Hall->Area candidate moves: `2670`
   - Candidate freshwater stations affected: `86`
   - GUID-like station names in candidate set: `2`
2. **Marine misclassification apply**
   - `containers_moved_to_area`: `2670`
   - `areas_created`: `78`
   - `halls_deleted_empty`: `104`
   - `stations_deleted_empty`: `86`
3. **Station geography correction apply** (unanimous evidence only)
   - `stations_geography_reassigned`: `15` (Faroe -> Scotland)
4. **Hall normalization apply** (semicolon suffix collapse)
   - `hall_collapse_containers_rehomed`: `939`
   - `hall_targets_created`: `19`
   - `hall_collapse_sources_deleted`: `855`
5. **Orphan semicolon-hall sweep**
   - Empty semicolon halls deleted: `843`

## Validation Snapshot (Post-remediation)

- Faroe freshwater stations total: `12`
- Faroe `S*` stations: `7`
  - `S03 Norðtoftir`, `S04 Húsar`, `S08 Gjógv`, `S10 Svínoy`, `S16 Glyvradalur`, `S21 Viðareiði`, `S24 Strond`
- Faroe `A*` stations: `0`
- GUID-like freshwater stations in Faroe: `0`
- `A03 Svínáir` as station: `false`
- `A03 Svínáir` as area (Faroe): `true`
- Halls with semicolon suffixes remaining: `0`
- Containers still attached to semicolon halls: `0`

## S16-specific Check (Rack/Tray Flattening)

- Station `S16 Glyvradalur` hall count after normalization: `11`
- Includes canonical hall `A Høll` and no `A Høll;NNNNN` tray-suffixed hall artifacts.
- FishTalk `Skáp`/tray depth is preserved as source metadata, not as additional station/hall hierarchy.

## Residual Domain Decisions (Not Auto-applied)

- Remaining non-`S*` Faroe stations: `H01 Svínoy`, `H125 Glyvrar`, `L01 Við Áir`, `L02 Skopun`, `Temp`.
- These are no longer marine misclassifications, but may require business-level classification policy:
  - whether `L*`/`H*` should remain in station inventory or be typed differently,
  - how to treat unresolved placeholder `Temp` (no grouped-organisation row, no assignments).

