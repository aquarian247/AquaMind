# HANDOFF 2026-02-24: FWSEA deterministic sales-link scoring module + B-class FT notes

## Session objective
Deliver a deterministic extraction module for FW->Sea linkage scoring that emits customer + ring + trip + status sales count in one output, and preserve user-supplied FishTalk B-class observations for the next agent session.

## Outcome status
- New deterministic FWSEA scoring tool implemented and executed successfully.
- Tool emits one row per sales action with:
  - customer (`ParameterID=220 -> Contact.Name`)
  - ring text (`ParameterID=96`)
  - trip id (`ParameterID=184` TransportXML)
  - exact-time status sales count/biomass (`PublicStatusValues`)
  - deterministic evidence score + band.
- Missing user-referenced B-class location (`A37` at 2023-09-08) resolved with source evidence.
- User-provided B-class FT observations recorded below for the next policy wave.

## Code changes in this session
- Added:
  - `scripts/migration/tools/fwsea_sales_linkage_scoring_extract.py`
- Updated:
  - `scripts/migration/tools/README.md` (new active tool entry)

## Primary artifacts (new)
- FWSEA scoring run:
  - `scripts/migration/output/fwsea_sales_linkage_scoring_20260224.csv`
  - `scripts/migration/output/fwsea_sales_linkage_scoring_20260224.json`
  - `scripts/migration/output/fwsea_sales_linkage_scoring_20260224.md`
- A37 station probe:
  - `scripts/migration/output/a37_station_probe_20260224.csv`

## Supporting artifacts from immediate FT sales discovery
- `scripts/migration/output/ft_sales_discovery_20260224_132838/ft_sales_data_residency_report.md`
- `scripts/migration/output/ft_sales_discovery_20260224_132838/sales_object_counts.csv`
- `scripts/migration/output/ft_sales_discovery_20260224_132838/internal_delivery_sales_action_metadata_parameter_distribution.csv`
- `scripts/migration/output/ft_sales_discovery_20260224_132838/internal_delivery_a73_ring3_4_5_6_samples_deduped.csv`
- `scripts/migration/output/ft_sales_discovery_20260224_132838/s03_1801_1803_operation_metadata_all_parameters.csv`

## Deterministic extraction contract (new tool)
Tool: `scripts/migration/tools/fwsea_sales_linkage_scoring_extract.py`

### Deterministic row grain
- One output row per sales action:
  - `InternalDelivery.SalesOperationID`
  - `Action.ActionType = 7`
  - `SaleActionID` unique row key.

### Deterministic status tie-break (exact operation timestamp)
When multiple `PublicStatusValues` rows exist for the same `(PopulationID, StatusTime = operation_start)`:
1. Prefer non-zero `SalesCount` or `SalesBiomassKg`.
2. Then higher `SalesCount`.
3. Then higher `SalesBiomassKg`.
4. Then higher `CurrentCount`.
5. Then higher `CurrentBiomassKg`.

### Scoring formula
- +25 customer present (`ParameterID=220`)
- +20 ring present (`ParameterID=96`)
- +20 trip present (`ParameterID=184`, `TripID` tag)
- +25 status sales count > 0 at exact operation time
- +10 status sales biomass > 0 at exact operation time
- Total: 0..100
- Bands: `strong >= 80`, `medium >= 60`, `weak >= 40`, else `sparse`

### Run command (repro)
```bash
python3 scripts/migration/tools/fwsea_sales_linkage_scoring_extract.py \
  --since "2023-01-01" \
  --only-fw-sources \
  --output-csv "scripts/migration/output/fwsea_sales_linkage_scoring_20260224.csv"
```

### Key run summary (from JSON artifact)
- Row count: `1470`
- Distinct sales operations: `1006`
- Distinct sale actions: `1470`
- Rows with customer: `1470`
- Rows with ring: `945`
- Rows with trip: `1006`
- Rows with status sales count > 0: `1470`
- Score bands: `strong=1095`, `medium=140`, `weak=235`, `sparse=0`

## FW->Sea data residency conclusions (this session)
- Sales quantity/biomass evidence lives in:
  - `PublicStatusValues`, `Ext_StatusValues_v2`, `Ext_DailyStatusValues_v2`, `PublicPlanStatusValues`.
- Internal-delivery sales semantics are strongly represented via:
  - `OperationType=7` (sales side) and `OperationType=5` (input side),
  - `ActionMetaData` parameter family for those operations:
    - `96` = ring text
    - `220` = destination/customer GUID -> `Contact.Name`
    - `184` = TransportXML payload (trip ID present in this backup).

## S03 user case alignment (1801 / 1803)
From targeted extracts:
- `1801` + `A73 Hvannas.Norður`:
  - `Ringur 4 -> SalesCount 60000`
  - `Ringur 5 -> SalesCount 80086`
  - `Ringur 6 -> SalesCount 80086`
- `1803` + `A73 Hvannas.Norður`:
  - `Ringur 3 -> SalesCount 83776`
  - `Ringur 4 -> SalesCount 24000`

This is captured in:
- `scripts/migration/output/ft_sales_discovery_20260224_132838/internal_delivery_a73_ring3_4_5_6_samples_deduped.csv`

## User-provided B-class FT observations (record for next agent)
- `SF JUL 25` — container `H061` — start `2025-07-10` (FW22 assumption):
  - count `35,636`
  - input number `25.03`, year class `2025`
  - biological Y-axis value (Fish Group Number): `25.04.038`
- `SF SEP 25` — container `H2_049` — start `2025-09-11` (FW22 assumption):
  - count `36,915`
  - input number `25.04`, year class `2025`
  - biological Y-axis value: `25.03.066`
- `SF MAR 25` — container `H004` — start `2025-03-27` (FW22 assumption):
  - count `30,545`
  - input number `25.01`, year class `2025`
  - biological Y-axis value: `25.01.004`
- `SF SEP 24` — container `H037` — start `2024-09-26` (FW22 assumption):
  - count `33,272`
  - input number `24.08`, year class `2024`
  - biological Y-axis value: `24.08.029`
- `Stofnfiskur desembur 2023` — container `A23` — start `2023-09-08` (S21 / hall `Gamalt` assumption from user):
  - count `89,757`
  - input number `23.04`, year class `2023`
  - biological Y-axis value: `23.04.024`

## Missing event lookup resolved (requested by user)
- Requested: `Stofnfiskur Septembur 2023 — container A37 — start 2023-09-08`.
- Source evidence:
  - `scripts/migration/output/a37_station_probe_20260224.csv`
- Resolved location/context:
  - Site: `S24 Strond`
  - Container group: `A Høll`
  - Container name: `A37`
  - Official ID: `Høll A;02437`
  - Start: `2023-09-08 08:43:33`
  - InputName: `Stofnfiskur Septembur 2023`
  - InputNumber: `3`
  - YearClass: `2023`

## Next-agent execution checklist (FWSEA-focused session)
1. Use the scoring module as the canonical extraction entrypoint:
   - start with full FW window (`--since 2023-01-01 --only-fw-sources`)
   - then run constrained cohorts (e.g., customer/site/ring specific filters).
2. Validate transport semantics depth:
   - verify whether `TransportXML` contains stable vessel/compartment/truck IDs across cohorts.
   - map `CarrierID`/`TransporterID` when present to transport tables (if populated).
3. Build deterministic FW->Sea acceptance logic on top of scoring output:
   - require source stage class FW,
   - require customer/ring/trip evidence thresholds,
   - require non-zero status sales count at operation time.
4. Cross-check with known user examples:
   - S03 `1801` / `1803` ring 3-6 chain and counts.
5. Keep `DATA_MAPPING_DOCUMENT.md` unchanged until semantics are proven stable as durable mapping rules (do not add run scoreboards there).

## Gate recommendation
- FW stabilization gate remains unchanged by this session.
- This session materially improves FWSEA traceability tooling and should be used as the basis for a dedicated FWSEA linkage validation pass in the next agent session.
