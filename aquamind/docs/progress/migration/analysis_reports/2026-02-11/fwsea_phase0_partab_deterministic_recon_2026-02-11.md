# FWSEA Phase 0 + Part A/B Deterministic Recon (2026-02-11)

## Scope + guardrails followed
- Local FishTalk SQL Server instance only (`docker` container `sqlserver`), no remote/RDP.
- Read-only source DB investigation.
- AquaMind runtime kept FishTalk-agnostic (no runtime code/API/UI changes).
- Execution order respected:
  1. Phase 0 programmable-object recon
  2. Phase 0 decision gate
  3. Part A
  4. Part B
  5. No SQL tracing escalation in this pass

## Inputs used for deterministic IDs
- Component population IDs (`145`):
  - `/Users/aquarian247/Projects/AquaMind/scripts/migration/output/input_batch_migration/Stofnfiskur_Juni_24_2_2024/population_members.csv`
- Fry entry IDs (`12`):
  - `/tmp/stofn_juni24_m95_semantic_full.json`

## Exact execution commands
### Primary execution prefix (read-only user)
```bash
cat <SQL_FILE> | docker exec -i sqlserver /opt/mssql-tools18/bin/sqlcmd \
  -b -C -S localhost,1433 -U fishtalk_reader -P '<REDACTED>' -d FishTalk -W
```

### Phase 0 module-readability cross-check prefix (sa)
```bash
cat <SQL_FILE> | docker exec -i sqlserver /opt/mssql-tools18/bin/sqlcmd \
  -b -C -S localhost,1433 -U sa -P '<REDACTED>' -d FishTalk -W
```

### Query pack + raw output artifact root
- SQL files: `/tmp/fwsea_phase0_partab_2026-02-11/sql`
- Raw outputs: `/tmp/fwsea_phase0_partab_2026-02-11/out`
- Exact command manifest (replayable, password redacted): `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fwsea_phase0_partab_command_manifest_2026-02-11.sh`
- Output checksum manifest (`sha256`): `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fwsea_phase0_partab_output_manifest_sha256_2026-02-11.txt`

## Phase 0 results
### P0a inventory
Output:
- `VIEW=70`
- `SQL_TRIGGER=20`
- `SQL_STORED_PROCEDURE=6`
- `SQL_SCALAR_FUNCTION=1`

Source: `/tmp/fwsea_phase0_partab_2026-02-11/out/P0a_inventory_counts.txt`

### P0b/P0c/P0d/P0f with `fishtalk_reader`
- `sys.sql_modules.definition` unavailable for all inspected modules (appeared as `ENCRYPTED_OR_UNAVAILABLE` / `NO_DEFINITION_TEXT`).
- Keyword sweeps returned no hits.
- Dependency cross-check returned no rows.

Sources:
- `/tmp/fwsea_phase0_partab_2026-02-11/out/P0b_module_readability.txt`
- `/tmp/fwsea_phase0_partab_2026-02-11/out/P0c_keyword_*.txt`
- `/tmp/fwsea_phase0_partab_2026-02-11/out/P0d_view_readability.txt`
- `/tmp/fwsea_phase0_partab_2026-02-11/out/P0f_dependency_crosscheck.txt`

### P0 cross-check with `sa` (same local DB)
- View/module text is readable (not encrypted in database).
- Key deterministic dependencies found:
  - `Ext_Transfers_v2` depends on `PublicTransfers`
  - `Ext_Inputs_v2` depends on `ActionMetaData`
  - `Ext_FishSupplier_v2` depends on `ActionMetaData`
  - `Ext_HarvestResults_v2` depends on `ActionMetaData`
- `Ext_Transfers_v2` definition shows direct `PublicTransfers` + `PublicStatusValues` composition.
- `Ext_Inputs_v2` definition shows parameterized extraction from `ActionMetaData` (IDs: `10,11,88,96,99,100,107,108,110,115,118`).
- Revalidated with provided local `sa` credential on `2026-02-11` for `P0d_view_readability.sql` and `P0f_dependency_crosscheck.sql` (same deterministic outputs).

Sources:
- `/tmp/fwsea_phase0_partab_2026-02-11/out/P0b_module_readability_sa.txt`
- `/tmp/fwsea_phase0_partab_2026-02-11/out/P0d_view_readability_sa.txt`
- `/tmp/fwsea_phase0_partab_2026-02-11/out/P0f_dependency_crosscheck_sa.txt`
- `/tmp/fwsea_phase0_partab_2026-02-11/out/S13_key_view_definitions_full.txt`
- `/tmp/fwsea_phase0_partab_2026-02-11/out/S14_module_keyword_sweep_sa.txt`

## Phase 0 decision gate outcome
- **Gate outcome:** `partial/readable with elevated access`.
- Interpretation used for this pass:
  - Treat table/query evidence (Part A/B) as primary for linkage claims.
  - Use module-derived evidence (from `sa` cross-check) only as deterministic support for interpretation of `Ext_*` views.
- Confidence label at gate: **medium** (because `fishtalk_reader` cannot inspect module text directly).

## Part A (external mixing boundary) results
### A1a PopulationLink type inventory
- `LinkType=2 -> 16,712`
- `LinkType=1 -> 5,909`

Source: `/tmp/fwsea_phase0_partab_2026-02-11/out/A1a_populationlink_linktype_counts.txt`

### A1b Stofnfiskur Juni 24 component linkage
- Component population IDs coverage is complete in source tables:
  - `145/145` in `Populations`
  - `145/145` in `Ext_Populations_v2`
  - `145/145` in `FishGroupHistory`
- `PopulationLink` rows touching component: all are `component_to_outside` (no internal component-to-component rows):
  - `LinkType=1`: `15` rows across `15` operations
  - `LinkType=2`: `12` rows across `1` operation

Sources:
- `/tmp/fwsea_phase0_partab_2026-02-11/out/S1_component_id_coverage.txt`
- `/tmp/fwsea_phase0_partab_2026-02-11/out/S3_populationlink_component_summary.txt`
- `/tmp/fwsea_phase0_partab_2026-02-11/out/A1b_populationlink_component_links.txt`

### A1c Fry outside-pop identity
- For Fry-touched outside populations in this cohort path:
  - `outside_pop_count=35`
  - `35/35` exist in `Populations`
  - `0/35` in `Ext_Populations_v2`
  - `0/35` in `FishGroupHistory`
  - `0/35` in `PopulationLink`
- These rows are same-site (`S03 Norðtoftir`, `ProdStage=Hatchery`) and short-lived transfer nodes.

Sources:
- `/tmp/fwsea_phase0_partab_2026-02-11/out/S10_fry_outside_pop_coverage.txt`
- `/tmp/fwsea_phase0_partab_2026-02-11/out/A1c_subtransfers_fry_outside_identity.txt`

### A1d ActionMetaData on cross-boundary ops
- Cross-boundary SubTransfer operations for component: `48`
  - Operation type distribution: `1 -> 47`, `31 -> 1`
- Metadata on those operations is dominated by `ParameterID 1, 18, 119`.

Sources:
- `/tmp/fwsea_phase0_partab_2026-02-11/out/S4_cross_boundary_ops_summary.txt`
- `/tmp/fwsea_phase0_partab_2026-02-11/out/A1d_actionmetadata_paramid_summary.txt`
- `/tmp/fwsea_phase0_partab_2026-02-11/out/A1d_actionmetadata_cross_boundary_ops.txt`

### A1e OperationProductionStageChange overlap
- No rows for the targeted cross-boundary operation set.

Source: `/tmp/fwsea_phase0_partab_2026-02-11/out/A1e_op_stage_change_cross_boundary.txt`

## Part B (FW→Sea linkage) results
### B1a TransportCarrier GUID match test
- `ActionMetaData.ParameterGuid IN TransportCarrier.ID`: **no matches**.

Source: `/tmp/fwsea_phase0_partab_2026-02-11/out/B1a_actionmetadata_transportcarrier_matches.txt`

### B1b InternalDelivery + ActionMetaData
- Deterministic metadata exists on `InternalDelivery`-linked `SalesOperationID` actions:
  - frequent parameters include `184` (Transport XML) and `220` (GUID contact/site-like reference).
- Summary across full `InternalDelivery` set:
  - rows: `3155`
  - `ParameterID=184` rows: `3155`
  - `ParameterID=220` rows: `6229` (`119` distinct GUIDs)

Sources:
- `/tmp/fwsea_phase0_partab_2026-02-11/out/B1b_internaldelivery_actionmetadata_top100.txt`
- `/tmp/fwsea_phase0_partab_2026-02-11/out/S5_internaldelivery_paramid_summary.txt`

### B1b decode checks
- `ParameterID=220` GUIDs map to `Contact` names (site/area-like entities), **not** `TransportCarrier` and not `Ext_Transporters_v2`.
- `ParameterID=184` XML is parseable in `3155/3155` rows and contains `TripID` (`3155/3155`), but no `CompartmentID/CompartmentNr` and no `TransporterID/CarrierID` fields in parsed nodes.

Sources:
- `/tmp/fwsea_phase0_partab_2026-02-11/out/S6_internaldelivery_param220_guid_lookup.txt`
- `/tmp/fwsea_phase0_partab_2026-02-11/out/S15_internaldelivery_param220_contact_lookup.txt`
- `/tmp/fwsea_phase0_partab_2026-02-11/out/S16_internaldelivery_param184_xml_extract.txt`
- `/tmp/fwsea_phase0_partab_2026-02-11/out/S7_internaldelivery_param184_trip_extract.txt`

### B1c PopulationLink cross-stage check
- Original Ext-only join path under-covered because `PopulationLink` endpoints are only partially present in `Ext_Populations_v2`:
  - total `PopulationLink` rows: `22,621`
  - `FromPopulationID` in `Ext_Populations_v2`: `5,909`
  - `ToPopulationID` in `Ext_Populations_v2`: `16,712`
- Rebased check via `Populations -> ContainerID -> Ext_GroupedOrganisation_v2`:
  - marine-involved links: `4,326`

Sources:
- `/tmp/fwsea_phase0_partab_2026-02-11/out/B1c_populationlink_cross_prodstage.txt`
- `/tmp/fwsea_phase0_partab_2026-02-11/out/S8_populationlink_coverage_ext_vs_pop.txt`
- `/tmp/fwsea_phase0_partab_2026-02-11/out/S9_populationlink_cross_stage_via_populations.txt`

### B1d/B1f
- `ProductionStages` table present (13 rows).
- `OperationProductionStageChange` joined to `InternalDelivery.SalesOperationID`: no rows.
- Non-system DBs on instance: `FISHTALK` only.

Sources:
- `/tmp/fwsea_phase0_partab_2026-02-11/out/B1d_productionstages.txt`
- `/tmp/fwsea_phase0_partab_2026-02-11/out/B1d_stage_change_internaldelivery.txt`
- `/tmp/fwsea_phase0_partab_2026-02-11/out/B1f_non_system_databases.txt`

### InternalDelivery stage-class and overlap diagnostics
- `InternalDelivery` row distribution by sales/input stage class:
  - `sales=fw, input=marine -> 2,798`
  - `sales=fw, input=fw -> 160`
  - `sales=unknown, input=fw -> 112`
  - `sales=fw, input=unknown -> 47`
  - `sales=marine, input=marine -> 30`
  - `sales=unknown, input=marine -> 6`
  - `sales=unknown, input=unknown -> 2`
- `InputOperationID` coverage:
  - non-null: `3,114 / 3,155`
  - matching `Operations`: `3,114 / 3,114`
- Operation overlap:
  - `SalesOperationID` in `SubTransfers`: `1,429`
  - `InputOperationID` in `SubTransfers`: `1,147`
  - `SalesOperationID` in `PopulationLink`: `3,114`
  - `InputOperationID` in `PopulationLink`: `3,114`

Sources:
- `/tmp/fwsea_phase0_partab_2026-02-11/out/S18_internaldelivery_sales_vs_input_stage_class.txt`
- `/tmp/fwsea_phase0_partab_2026-02-11/out/S12_internaldelivery_inputoperation_coverage.txt`
- `/tmp/fwsea_phase0_partab_2026-02-11/out/S19_internaldelivery_subtransfer_overlap.txt`

## Compact findings table
| source | deterministic linkage found (Y/N) | coverage | confidence | recommended action |
| --- | --- | --- | --- | --- |
| `sys.sql_modules` + `Ext_*` view defs (sa cross-check) | Y | Key migration views (`Ext_Inputs_v2`, `Ext_Transfers_v2`) | High | Use module-derived interpretation in migration tooling docs; keep runtime untouched |
| `PopulationLink` for Stofnfiskur Juni 24 component | Y | `27` component-to-outside links | Medium | Treat as explicit outside-boundary evidence; do not auto-merge boundaries globally |
| Fry outside pops (`SubTransfers` path) | Y (outside-node signal), N (batch identity) | `35` outside pops, all missing in `Ext_Populations_v2`/`FishGroupHistory` | Medium | Classify as transfer-boundary/bridge-like evidence; keep uncertainty label for batch identity |
| Cross-boundary ops `ActionMetaData` (Stofnfiskur Juni 24) | Y | `48` ops, params `1/18/119` dominant | Medium | Integrate parameter profiling in tooling reports only |
| `InternalDelivery` + `ActionMetaData` (`184`, `220`) | Y (operation-level) | `3,155` sales ops; `2,798` fw->marine sales/input class | High | GO for tooling extraction/investigation integration (operation-level evidence) |
| `ActionMetaData.ParameterGuid -> TransportCarrier` | N | `0` matches | High | Keep “no direct carrier GUID mapping” assumption; do not hardcode carrier join |
| `PopulationLink` marine involvement (rebased via `Populations`) | Y | `4,326` marine-involved links | Medium | Add extraction + validation path for PopulationLink in migration tooling |

## FW20 behavior preservation
No migration policy/runtime code change was applied in this pass. Existing verified status remains preserved:
- FW20 remediation remains as documented in prior 2026-02-11 handoffs.
- External-mixing default remains `10.0` (no evidence in this pass warrants change).
- `transferred_count <= 0` policy unchanged (this pass did not replay transfers/actions).

## Go / No-Go decision (migration policy/tooling)
1. **GO (tooling integration, scoped):**
   - Integrate extraction/reporting support for:
     - `InternalDelivery` (`SalesOperationID`, `InputOperationID`, `InputSiteID`)
     - `ActionMetaData` parameters `184`, `220` for those operations
     - `Contact`/`ContactTypes` lookup for parameter-220 GUIDs
     - `PopulationLink` + `SubTransfers` overlap diagnostics
   - Scope is tooling validation/reporting only.

2. **NO-GO (policy/runtime changes):**
   - Do **not** auto-link FW and Sea in migration replay policy yet.
   - Do **not** alter external-mixing global default (`10.0` stays).
   - Do **not** introduce FishTalk-specific logic in runtime API/UI.

## Remaining uncertainty + deterministic next checks
- DB evidence now strongly suggests operation-level FW→Sea context in `InternalDelivery`, but population-level endpoint semantics for automatic linkage are not yet proven end-to-end.
- Deterministic next checks (tooling-only):
  1. Build a row-level candidate extractor: `InternalDelivery` row -> (`SalesOperationID` populations, `InputOperationID` populations, stage/site classes, trip_id from param `184`).
  2. Require strict acceptance gates before any auto-link policy:
     - unique/consistent population endpoint pairing,
     - no regression in semantic/counts gates,
     - no increase in incomplete-linkage transitions.
  3. If endpoint semantics remain ambiguous after extraction, escalate to local SQL tracing (Extended Events) targeting Activity Explorer delivery flows.
