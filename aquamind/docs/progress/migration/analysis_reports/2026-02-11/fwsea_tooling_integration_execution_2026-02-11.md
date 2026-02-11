# FWSEA Tooling Integration Execution (2026-02-11)

## Scope
Implemented the recommended **tooling-only** FWSEA integration path with no runtime or migration-policy changes:

1. Extended extract tooling for deterministic FWSEA evidence inputs.
2. Added a deterministic FWSEA linkage report tool.
3. Executed local extract + report generation on the FishTalk local SQL instance.

## Code changes
- `/Users/aquarian247/Projects/AquaMind/scripts/migration/tools/bulk_extract_fishtalk.py`
  - Added table: `internal_delivery_action_metadata` (scoped to InternalDelivery operations; params `184`/`220`).
  - Added table: `contacts`.
  - Added table: `contact_types`.
  - Added XML-derived columns for param `184` rows: `XmlParseable`, `TripID`, `CompartmentID`, `CompartmentNr`, `TransporterID`, `CarrierID`.
  - Added `SET QUOTED_IDENTIFIER ON;` to support XML methods.
- `/Users/aquarian247/Projects/AquaMind/scripts/migration/tools/fwsea_deterministic_linkage_report.py`
  - New active tooling report script.
  - Inputs: InternalDelivery, ActionMetaData (184/220), Contact/ContactTypes, PopulationLink, SubTransfers, population/grouped-organisation context.
  - Outputs: markdown + optional JSON deterministic evidence summary.
  - Supports optional component scoping via `population_members.csv`.
- `/Users/aquarian247/Projects/AquaMind/scripts/migration/tools/README.md`
  - Added the new report tool to active tools list.

## Exact commands run

### 1) Verify tooling registration + script health
```bash
cd /Users/aquarian247/Projects/AquaMind
python -m py_compile scripts/migration/tools/fwsea_deterministic_linkage_report.py scripts/migration/tools/bulk_extract_fishtalk.py
python scripts/migration/tools/bulk_extract_fishtalk.py --list-tables | rg -n "internal_delivery_action_metadata|contacts|contact_types" -n -S
python scripts/migration/tools/fwsea_deterministic_linkage_report.py --help
```

### 2) Extract newly integrated FWSEA evidence tables
```bash
cd /Users/aquarian247/Projects/AquaMind
python scripts/migration/tools/bulk_extract_fishtalk.py \
  --tables internal_delivery_action_metadata,contacts,contact_types \
  --output scripts/migration/data/extract/
```

Observed output summary:
- `internal_delivery_action_metadata`: `13,718` rows
- `contacts`: `857` rows
- `contact_types`: `1,323` rows

### 3) Generate deterministic FWSEA tooling report (component-scoped example)
```bash
cd /Users/aquarian247/Projects/AquaMind
python scripts/migration/tools/fwsea_deterministic_linkage_report.py \
  --csv-dir scripts/migration/data/extract \
  --report-dir scripts/migration/output/input_batch_migration/Stofnfiskur_Juni_24_2_2024 \
  --output aquamind/docs/progress/migration/analysis_reports/2026-02-11/fwsea_tooling_deterministic_linkage_report_stofnfiskur_juni24_2026-02-11.md \
  --summary-json aquamind/docs/progress/migration/analysis_reports/2026-02-11/fwsea_tooling_deterministic_linkage_report_stofnfiskur_juni24_2026-02-11.summary.json
```

Generated artifacts:
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fwsea_tooling_deterministic_linkage_report_stofnfiskur_juni24_2026-02-11.md`
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fwsea_tooling_deterministic_linkage_report_stofnfiskur_juni24_2026-02-11.summary.json`

## Key resulting metrics (from summary JSON)
- InternalDelivery rows: `3155`
- InputOperationID coverage: `3114/3114` matched in operations extract
- Stage pair distribution (rows):
  - `sales=fw, input=marine`: `2704`
  - `sales=fw, input=fw`: `160`
  - `sales=unknown, input=fw`: `112`
  - `sales=unknown, input=marine`: `100`
- Parameter `184`:
  - rows: `7489`
  - parseable XML rows: `7489`
  - trip_id rows: `7489`
  - compartment/carrier fields: `0/0`
- Parameter `220`:
  - rows: `6229`
  - distinct GUIDs: `119`
  - GUID->Contact matches: `119`
  - GUID->TransportCarrier matches: `0`
  - GUID->Ext_Transporters matches: `0`
- InternalDelivery op overlap:
  - Sales op in SubTransfers: `1390`
  - Input op in SubTransfers: `1113`
  - Sales op in PopulationLink: `3037`
  - Input op in PopulationLink: `3037`

## Compact findings table
| source | deterministic linkage found (Y/N) | coverage | confidence | recommended action |
| --- | --- | --- | --- | --- |
| `internal_delivery_action_metadata` (params 184/220) | Y | 13,718 rows | High | Keep this extract table in standard tooling bundle |
| `contacts` + `contact_types` lookup on param 220 GUIDs | Y | 119/119 GUIDs resolved to Contact IDs | High | Use Contact resolution in tooling diagnostics; avoid carrier hardcoding |
| Param 184 XML parsed fields (`TripID`) | Y | 7,489/7,489 parseable + trip id present | High | Keep parsed XML fields in extraction for deterministic reporting |
| InternalDelivery vs PopulationLink/SubTransfers overlap | Y | 3,037/1,390+ operation overlaps | Medium | Retain as operation-level linkage diagnostics only |

## FW20 + policy/runtime status
- FW20 behavior preserved.
- No runtime FishTalk coupling added.
- No migration-policy changes introduced.
- External-mixing default remains `10.0`.

## Go / No-Go (post-integration)
1. **GO**: keep and use this tooling integration path for deterministic evidence collection.
2. **NO-GO**: still no automatic FW/Sea policy linkage promotion without additional endpoint-level acceptance gates.
