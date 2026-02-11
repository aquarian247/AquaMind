# HANDOFF 2026-02-11 - FWSEA Phase 0 + Part A/B Execution (Local SQL, Tooling-Only)

## Scope completed
Executed the revised FWSEA investigation sequence on local FishTalk SQL Server only:
1. Phase 0 programmable-object recon (mandatory first)
2. Phase 0 decision gate
3. Part A external-mixing linkage investigation
4. Part B FW→Sea linkage investigation

No runtime API/UI code changes were made.

## Evidence report
Primary report:
- `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fwsea_phase0_partab_deterministic_recon_2026-02-11.md`
- Exact command manifest:
  - `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fwsea_phase0_partab_command_manifest_2026-02-11.sh`
- Output checksum manifest:
  - `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-11/fwsea_phase0_partab_output_manifest_sha256_2026-02-11.txt`

Raw SQL artifacts:
- SQL pack: `/tmp/fwsea_phase0_partab_2026-02-11/sql`
- Outputs: `/tmp/fwsea_phase0_partab_2026-02-11/out`

## Exact outcomes

### 1) Phase 0 outcome
- With `fishtalk_reader`, module definitions were unavailable; keyword/dependency scans returned no module text.
- Cross-check with local `sa` (still read-only query behavior) proved definitions are readable in this DB and yielded deterministic view semantics:
  - `Ext_Transfers_v2` derives from `PublicTransfers` + `PublicStatusValues`
  - `Ext_Inputs_v2` derives from `ActionMetaData` parameters (including transporter/input metadata)
- Revalidation with provided `sa` credential on `2026-02-11` reconfirmed `P0d` and `P0f` deterministic outputs.

Decision gate result:
- **Partial at readonly profile level, readable with elevated local profile**.
- Continued with Part A/B using table evidence as primary, module text as supporting interpretation.

### 2) Part A outcome (Stofnfiskur Juni 24)
- `PopulationLink` has explicit component-to-outside links for this cohort (`27` rows; no component-internal links).
- For Fry outside-touching populations, outside nodes exist in `Populations` but not in `Ext_Populations_v2` or `FishGroupHistory` in this path.
- Cross-boundary ops (`48`) are mostly transfer-like operation types (`1` and `31`), with ActionMetaData dominated by params `1/18/119`.
- No `OperationProductionStageChange` rows in the targeted cross-boundary subset.

Interpretation:
- Deterministic outside-boundary linkage exists, but outside-node batch identity coverage is incomplete in this backup path.

### 3) Part B outcome (FW→Sea)
- `ActionMetaData.ParameterGuid -> TransportCarrier.ID`: no deterministic match.
- `InternalDelivery` rows carry strong metadata signal:
  - Parameter `184`: parseable XML with trip IDs on all sampled/full rows.
  - Parameter `220`: GUIDs resolve to `Contact` entities (site/area-like), not transport carrier IDs.
- `InternalDelivery` endpoint coverage is strong:
  - `InputOperationID` non-null on `3114/3155`, all mapped to `Operations`.
  - Stage-class pairing across rows shows `sales=fw, input=marine` dominant (`2798` rows).
- `PopulationLink` has substantial marine-involved coverage when resolved through `Populations -> Container -> GroupedOrganisation` (`4326` rows).

Interpretation:
- Deterministic operation-level FW→Sea context exists in `InternalDelivery` + `ActionMetaData`, but automatic population-level linkage policy still requires stricter endpoint validation.

## Compact findings table
| source | deterministic linkage found (Y/N) | coverage | confidence | recommended action |
| --- | --- | --- | --- | --- |
| `sys.sql_modules` + key `Ext_*` views | Y | Core migration views decoded | High | Use module-derived interpretation in tooling docs/reports |
| `PopulationLink` (component scope) | Y | 27 component-to-outside links | Medium | Keep as explicit outside-boundary evidence in tooling |
| Fry outside-node identity path | N (for full batch identity) | 35 outside nodes without Ext/FGH identity | Medium | Keep uncertainty label; avoid hardcoded batch inference |
| Cross-boundary ops metadata (Part A) | Y | 48 ops; params `1/18/119` | Medium | Add profiling to tooling reports |
| `InternalDelivery` + `ActionMetaData` (`184`,`220`) | Y (operation-level) | 3155 rows, fw→marine pairing dominant | High | Integrate extraction/validation in tooling only |
| `ParameterGuid -> TransportCarrier` | N | 0 matches | High | Do not force carrier GUID join logic |
| `PopulationLink` marine involvement | Y | 4326 rows (rebased join path) | Medium | Add to deterministic linkage investigation tooling |

## Go / No-Go recommendation
1. **GO (tooling integration, scoped):**
   - Integrate `InternalDelivery` + `ActionMetaData(184,220)` + `Contact` + `PopulationLink/SubTransfers` diagnostics into migration tooling extraction/validation/reporting.
2. **NO-GO (policy/runtime changes):**
   - No automatic FW/Sea linking policy change yet.
   - Keep global external-mixing default at `10.0`.
   - Keep runtime FishTalk-agnostic.

## Unresolved risks
1. Population-level endpoint semantics for automatic FW→Sea linking are still not fully proven despite strong operation-level evidence.
2. Outside-node identity gaps (`Populations` present, `Ext_Populations_v2`/`FishGroupHistory` absent in relevant path) can still hide batch attribution.
3. Transport XML contains trip IDs but not directly parsed compartment/carrier IDs in this pass.

## Next deterministic steps
1. Build a tooling-only row-level linker candidate report:
   - `InternalDelivery` row -> sales-side populations, input-side populations, stage/site classes, trip_id.
2. Require strict acceptance gates before any auto-link policy promotion:
   - endpoint uniqueness/stability,
   - semantic/count regressions = none,
   - no increase in incomplete-linkage fallback.
3. If ambiguity remains, run local SQL tracing (Extended Events) on Activity Explorer delivery workflows.

## FW20 behavior preservation status
Preserved. No migration replay policy changes or runtime changes were applied in this pass.
