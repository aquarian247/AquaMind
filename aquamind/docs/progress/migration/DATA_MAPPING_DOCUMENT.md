# FishTalk → AquaMind Data Mapping Blueprint

> **Blueprint:** This document defines field-level mapping rules. It should not contain run status or counts.

**Version:** 5.9  
**Date:** 2026-03-11  
**Status:** Updated - sea-side input initiation model for FWSEA pairing + guarded anchor-scoped provisional continuation contract + FW terminal depletion fallback rule + scope-file child-flag forwarding hardening + transfer-rich descendant replay contract + transfer rerun prune-and-rebuild contract + semantic bridge lineage fallback hardening + lifecycle progression basis interpretation guard + transfer-inclusive scope expansion contract + transfer mix-lineage backfill contract + exact-start duplicate-timestamp tie-break + exact-start transfer count authority + assignment biomass precision guardrail + station-split lineage qualification + scope-60 feed-lineage contract + OrgUnit fallback anchoring for lineage-scoped feed stores  

## 1. Overview

This document provides detailed field-level mapping specifications for migrating data from FishTalk to AquaMind. Each section covers entity relationships, field transformations, and business logic required for accurate data migration.

### 1.1 Environments & Schema Snapshots

- **Source:** FishTalk SQL Server (Docker container `sqlserver`, port `1433`, read-only login `fishtalk_reader`).
- **Target:** `aquamind_db_migr_dev` (Django alias `migr_dev`). Keep `aquamind_db` untouched for day-to-day development—the two databases have diverged (159 vs 154 tables).
- **Schema Provenance:** Run `scripts/migration/tools/dump_schema.py` whenever the FishTalk schema changes (`--label fishtalk`) and whenever the AVEVA Historian schema is refreshed (`--label aveva --profile aveva_readonly --database RuntimeDB --container aveva-sql`). Snapshot outputs (`*_schema_snapshot.json`) live under `docs/database/migration/schema_snapshots/`. CSV/TXT exports are generated on demand and are not tracked in the repo.

**Key Revision Notes (v5.9 - 2026-03-05):**
- **Sea-side input initiation model (FWSEA):** for current backup behavior, especially early-2023+, marine cohorts should be treated as **new sea-side inputs** rather than assuming continuous FW `InputName` identity across the geography boundary.
- **FWSEA endpoint-pairing rule:** when matching FW to sea, pair **FW terminal depletion/sales** at `S*` with **sea input / first-fill / first non-zero** signals at `A*` in the same geography and near-term time window. Input-side sea evidence is the primary destination-side signal because sea batches are separate FishTalk batches.
- **FW terminal depletion fallback:** absence of a visible FW sales action does **not** block candidate generation. A sudden FW tank/population drop to zero followed by a proximate sea input/start remains a valid but weaker candidate class.
- **Guarded provisional continuation contract:** linked full-lifecycle continuation must use explicit anchor-scoped sea populations by default (`--sea-anchor-population-id`, optional `--sea-block-population-id`). Full sea-component ingestion is unsafe for provisional rows and now opt-in only via explicit override.

**Key Revision Notes (v5.9 - 2026-03-09):**
- **Transfer-rich replay contract corrected:** for stitched FW scopes/chunks, the replay-safe default is `--expand-subtransfer-descendants --transfer-edge-scope source-in-scope`. The transfer migrator must expand `SourcePopBefore -> SourcePopAfter -> DestPopAfter` chains into root-source conservation edges before any scope filter is applied. Older `internal-only` guidance can drop sibling split legs on transfer-rich cohorts.
- **Culling-tail fold-back contract:** same-container same-stage residual `SourcePopAfter` rows that exist only to be fully culled should not survive as standalone AquaMind assignments. Fold them back into the predecessor assignment and attach the culling `MortalityEvent` there.

**Key Revision Notes (v5.9 - 2026-03-11):**
- **Transfer rerun prune-and-rebuild contract:** transfer-only reruns must prune existing FishTalk-mapped transfer workflows/actions for the target batch before rebuilding current scoped edges. Otherwise stale internal relay actions can survive alongside corrected `source-in-scope` edges and distort semantic validation.
- **Bridge lineage fallback hardening:** semantic validation may seed missing temporary-bridge timing metadata from stitched `population_members.csv` when `ext_populations.csv` omits a relay population. Temporary bridge detection must consider inbound `SourcePopAfter` relays as well as `DestPopAfter`, and predecessor-graph fallback must continue through previous-stage temporary bridge nodes instead of treating them as authoritative count sources.

**Key Revision Notes (v5.8 - 2026-03-03):**
- **OrgUnit fallback anchoring (lineage feed stores):** when `FeedStore` cannot be anchored through `FeedStore*Assignment` containers or consumption-container mappings, fallback anchoring is allowed via `FeedStore.OrgUnitID` to FW station/hall (`OrgUnit_FW`) for scoped freshwater replay. This fallback is auditable (`resolution_method=orgunit`) and must still respect deterministic idempotent mapping through `ExternalIdMap`.
- **Unresolved classification contract:** lineage feed runs must report unresolved stores split into `primary` vs `upstream_only` impact classes, and provide per-class skipped-line counts.

**Key Revision Notes (v5.7 - 2026-03-03):**
- **Scope-60 residual feed/inventory extraction contract:** for hall-stage mapped freshwater scope (<30m, including trusted `FW13 Geocrab` mapping), feed/inventory extraction must start from scoped cohort seeds and expand population lineage through `SubTransfers` (`SourcePopBefore -> SourcePopAfter`, `SourcePopBefore -> DestPopAfter`) before selecting feed data.
- **Feed lineage authority contract:** do not scope purchases/stock solely through `FeedStoreUnitAssignment` on fish containers. Authoritative feed scoping is `Feeding` consumption (`Action.PopulationID`) + `FeedBatch` lineage expansion via upstream `FeedTransfer`; then hydrate dependent entities (`FeedReceptionBatches`, `FeedReceptions`, `FeedStore`, `FeedStoreUnitAssignment`, `FeedTypes`, suppliers) from the included feed-batch set.

**Key Revision Notes (v5.5 - 2026-02-28):**
- **Scope-file replay mode (input-batch runner):** `pilot_migrate_input_batch.py` now supports `--scope-file` to run a deterministic ordered batch-key sweep from a CSV scope artifact. Scope rows can be `batch_key` rows directly, or population rows that are resolved back to `batch_key` via stitched `input_population_members.csv`.
- **Transfer-inclusive scope expansion contract:** `build_transfer_inclusive_scope.py` keeps all original stitched members, then appends destination populations for `SubTransfers` edges whose source population is already in scope, preserving unresolved destinations in output for audit visibility.
- **Mix-lineage backfill contract:** transfer-path replay is now explicitly followed by `pilot_backfill_transfer_mix_events.py`, which materializes `BatchMixEvent` / `BatchMixEventComponent` from completed transfer actions and sets `allow_mixed=True` on qualified action rows.

**Key Revision Notes (v5.6 - 2026-03-02):**
- **Scope-file child-flag forwarding hardening:** in `pilot_migrate_input_batch.py`, scope-mode child invocations now forward `--expand-subtransfer-descendants`, `--transfer-edge-scope`, and `--dry-run`. Missing forwarding previously allowed silent seed-only replays for transfer-rich cohorts.
- **Transfer-rich replay contract:** when replaying stitched scopes/chunks, run with `--expand-subtransfer-descendants --transfer-edge-scope source-in-scope` and preserve root-source split-leg expansion before any destination filtering.
- **Lifecycle progression interpretation guard:** History lifecycle progression default (`basis=stage_entry`) is entry-count semantics (first positive assignment per `(container, stage)`), not concurrent stock. Use assignment timeline / peak-concurrent analysis for biological stock checks.

**Key Revision Notes (v5.4 - 2026-02-25):**
- **FW inter-station station-split lineage qualification:** a biological cohort can branch from one freshwater station to another and appear with different `InputName` labels across station branches; deterministic lineage proof must rely on operation linkage, not `InputName` equality.
- **Qualified operation-link signature for station-split branches:** paired `InternalDelivery` operations (`SalesOperationID` type `7` + `InputOperationID` type `5`) at the same start timestamp, destination `Ext_Inputs_v2` row at that timestamp with `InputCount > 0`, and (when present) shared transport trip metadata (`ActionMetaData.ParameterID=184` `TripID`) across sales/input operations.
- **Supplier-label caveat (qualified):** destination `Ext_Inputs_v2.SupplierID` can resolve to source-station contact (for example `S08 Gjógv`) while cohort-start supplier remains broodstock contact at `L01 Við Áir`; therefore supplier label alone is not identity proof for station-split branches.

**Key Revision Notes (v5.3 - 2026-02-24):**
- **Exact-start duplicate-timestamp tie-break (completed populations):** when multiple `PublicStatusValues` rows share the same (`PopulationID`, `StatusTime`) at `member.start_time`, authoritative count resolution is deterministic: prefer non-zero over zero, then highest `CurrentCount`, then highest `CurrentBiomassKg`.
- **Cross-mode snapshot parity guard:** the same duplicate-timestamp tie-break is applied in both CSV and SQL snapshot selection paths so replay behavior does not depend on source row order.

**Key Revision Notes (v5.2 - 2026-02-23):**
- **Completed-population transfer count authority:** when an exact status snapshot exists at `member.start_time` and is non-zero, assignment `population_count` is set from that snapshot (prevents lane-level drift where conservation-only splits produced synthetic `20,000/10,000` style rows).
- **Open-population count authority (confirmed):** open populations (`member.end_time IS NULL`) continue to use latest measured status counts as authoritative.
- **Biomass precision guardrail:** status-implied average weight is retained at higher internal precision before model rounding, preventing biomass under-rounding regressions (for example `7.10 -> 6.99`) when counts are corrected.
- **S08 R-Høll dual-stage refinement:** first **material** holder in an `R-Høll` container (duration >= 6h, or open) is treated as `Parr`; subsequent in-hall rows resolve `Smolt`. Pre-initial micro bridge fragments are retained as history rows but forced to zero count to avoid duplication.

**Key Revision Notes (v5.1 - 2026-02-20):** 
- **Input-Based Stitching:** Use `Ext_Inputs_v2` (InputName + InputNumber + YearClass) as the biological batch key. Project tuples are administrative and can mix year-classes.
- **Feeding Schema Corrected:** `dbo.Feeding` is ActionID‑based and has no PopulationID/ContainerID columns; join via `Action` and `Operations`.
- **Health Journal Corrected:** Use `UserSample` + `Action` join path (one JournalEntry per ActionID), not `HealthLog`.
- **Environmental Sources Updated:** Use `Ext_DailySensorReadings_v2` + `Ext_SensorReadings_v2` (with `is_manual` distinction).
- **Assignments (v5.1 behavior, superseded in v5.2):** Populate counts/biomass from `PublicStatusValues` snapshots (prefer non‑zero after start).
- **Weight Samples:** `Ext_WeightSamples_v2` and `PublicWeightSamples` are duplicates in this backup. Use **Ext only** and treat `AvgWeight` as **grams** (no kg heuristic).
- **Infrastructure Naming:** Do not prepend `FT` or append `FW`/`Sea`. Strip those tokens if present in source labels.
- **Harvest Mapping:** Use `HarvestResult` (ActionID‑keyed) for harvest events and lots; `Harvest` table is not used.
- **FWSEA Endpoint Diagnostics (tooling-only):** `fwsea_endpoint_pairing_gate.py` + `fwsea_endpoint_gate_matrix.py` now emit blocker-family classification in JSON/TSV/Markdown (`reverse_flow_fw_only`, `true_fw_to_sea_candidate`, `true_fw_to_sea_sparse_evidence`, `unclassified_nonzero_candidate`), with strict and diagnostic profiles tracked explicitly.
- **Trace Target Prepack:** `fwsea_trace_target_pack.py` builds deterministic `OperationID` trace packs from blocker cohorts to drive targeted SQL extraction and local XE/Profiler sessions.
- **Site Prefix Semantics (operator-confirmed):** `L*` = Lívfiskur (broodstock), `S*` = station, `A*` = sea area. Treat `L* -> S*` as broodstock/egg supply context (not FW→Sea linkage); FW→Sea candidate boundary is `S* -> A*`.
- **Assignment History Calibration (S21 parity hardening):** same-stage superseded assignment handling now keeps short-lived bridge rows suppressed while preferring status-at-start for long-lived superseded companions and blank-token external-mixing rows.
- **Inter-station FW transfer policy (2026-02-17):** FW->FW transfer across stations is normal for some cohorts; station preflight mismatch is now documented as a policy signal (strict by default, `--allow-station-mismatch` for transfer-confirmed cohorts), not automatic invalid-data contamination.
- **Semantic gate refinement (2026-02-17):** bridge-aware positive deltas without mixed-batch evidence are downgraded to `incomplete_linkage` when consolidation shape (`many linked sources -> fewer linked destinations`) indicates likely missing lineage context.
- **FW->Sea temporal candidate policy (2026-02-17):** when canonical FW->Sea edges are absent in current extract, generate review-only candidates from FW terminal depletion date `X` to sea entry date `[X, X+2 days]` within the same geography and `S* -> A*` boundary.
- **FW hard-data closure calibration (2026-02-20):** active-holder tie-break now ranks by latest status timestamp, open membership, latest status count, and latest membership start timestamp; open populations (`end_time IS NULL`) use latest measured status counts; stage-mismatch deactivation keeps recent non-zero holders active when they fall inside the lifecycle frontier window.

## 2. Infrastructure & Geography Mapping

### 2.1 Geography Mapping (FishTalk: Locations + Site Grouping)

| FishTalk Source | AquaMind Target | Data Type | Transformation | Notes |
|----------------|----------------|-----------|----------------|-------|
| Locations.NationID | infrastructure_geography.name | varchar(100) | Direct | Fallback geography if site grouping fails |
| Ext_GroupedOrganisation_v2.SiteGroup / Site | infrastructure_geography.name | varchar(100) | Resolve to `Faroe Islands` or `Scotland` | SiteGroup takes precedence; see resolution order below |

**Geography resolution order**
1. `SiteGroup` in `{West, North, South}` ⇒ **Faroe Islands**
2. `SiteGroup` present (any other value) ⇒ **Scotland**
3. Site name membership in curated lists (FAROE_SITES_* / SCOTLAND_SITES_*) ⇒ **Faroe Islands** or **Scotland**
4. Site-code heuristic fallback:
   - `A*`, `S` + 2 digits, `L*`, `H*` ⇒ **Faroe Islands**
   - `S` + 3 digits, `N*`, `FW*`, `BRS*` ⇒ **Scotland**
5. `Locations.NationID`
6. `Unknown`

**Hierarchy handling rule (updated):**
- FishTalk area groups (for example Faroe `North/South/West`) are persisted as `infrastructure_areagroup` and linked from `infrastructure_area.area_group_id`.
- For now, migration creates top-level `AreaGroup` nodes (`parent=NULL`) from `SiteGroup`; deeper Scotland trees can be added by iterative parent linkage in follow-up runs.

**Operational guard (updated 2026-02-17):**
- `pilot_migrate_input_batch.py` runs station preflight from three sources (`InputProjects`, `Ext_Inputs_v2`, member-derived grouped-organisation sites).
- Inter-station freshwater (`FW->FW`) transfers are normal in some cohorts and should not be treated as invalid data by default.
- Station preflight therefore serves as a policy gate:
  - strict mode (default): fail on site mismatches,
  - controlled mixed-site mode: allow replay with `--allow-station-mismatch` for transfer-confirmed cohorts.

### 2.2 Freshwater Station Mapping (FishTalk: OrganisationUnit + Locations + Ext_GroupedOrganisation_v2)

**Reality check (2026-01-22):** `OrganisationUnit.LocationID` is sparsely populated (4106/4215 missing). Geography and station naming should rely primarily on `Ext_GroupedOrganisation_v2.Site/SiteGroup` with `OrganisationUnit.Name` as fallback.

| FishTalk Source | AquaMind Target | Data Type | Transformation | Notes |
|----------------|----------------|-----------|----------------|-------|
| OrganisationUnit.OrgUnitID | ExternalIdMap (OrganisationUnitStation) | uuid | Store for idempotency | `source_identifier = OrgUnitID` |
| Ext_GroupedOrganisation_v2.Site / OrganisationUnit.Name | infrastructure_freshwaterstation.name | varchar(100) | Prefer `Site`, fallback to `OrgUnit.Name` | Trim to 100 chars |
| OrganisationUnit.LocationID → Locations.Latitude/Longitude | infrastructure_freshwaterstation.latitude / longitude | numeric(9,6) | Direct | Default `0` if missing |
| Derived | infrastructure_freshwaterstation.station_type | varchar(20) | `BROODSTOCK` for `L*`/`BRS*`, otherwise `FRESHWATER` | |
| Geography (from 2.1) | infrastructure_freshwaterstation.geography_id | bigint | FK lookup | |

**Current migration behavior note:**
- Station names are still validated before replay, but mismatch is interpreted as cohort-shape evidence (single-site vs mixed-site), not automatic contamination.
- Use strict station mode for station-pure cohorts; use controlled mismatch override for cohorts with confirmed FW->FW transfer behavior.
- Guardrail: `A*` and other marine-inferred sites are never created as `FreshwaterStation`.
- Idempotent station lookup must be scoped by `(name, geography)` to avoid cross-geography collisions.

### 2.3 Hall Mapping (FishTalk: Ext_GroupedOrganisation_v2 + Containers)

**Coverage note (2026-01-22):** `Ext_GroupedOrganisation_v2` has 10,183 rows vs 17,066 containers; ~6,883 containers will not have hall metadata and must fall back to `Containers.OfficialID` or remain unmapped.

| FishTalk Source | AquaMind Target | Data Type | Transformation | Notes |
|----------------|----------------|-----------|----------------|-------|
| Ext_GroupedOrganisation_v2.ContainerGroup | infrastructure_hall.name | varchar(100) | Normalize whitespace; strip `FT` prefix/`FW`/`Sea` suffix; `A Høll` → `Hall A` | `Høll` is Faroese for Hall |
| Containers.OfficialID | infrastructure_hall.name | varchar(100) | Fallback: prefix before `;`, normalize | Used when `ContainerGroup` is empty |
| Ext_GroupedOrganisation_v2.ContainerGroupID | ExternalIdMap (OrganisationUnitHall) | uuid | Store `OrgUnitID:ContainerGroupID` | Ensures per-station uniqueness |
| OrganisationUnit.OrgUnitID | infrastructure_hall.freshwater_station_id | bigint | FK lookup | Hall belongs to station |

**Nested physical hierarchy (important):**
- FishTalk may contain `Hall -> Skáp (rack) -> Incubation Tray`.
- AquaMind now supports container hierarchy via `infrastructure_container.parent_container_id` + `hierarchy_role`.
- Migration maps `StandName/StandID` (for example `Skáp 1..5`) to structural rack containers (`hierarchy_role=STRUCTURAL`) and links tray/holding containers as children.

**Lifecycle note:**
- Hall mapping supports infrastructure placement and lifecycle resolution, but lifecycle truth is stage/hall logic in section 3.3 (not `ProdStage` alone).

### 2.4 Sea Area Mapping (FishTalk: OrganisationUnit + Locations)

| FishTalk Source | AquaMind Target | Data Type | Transformation | Notes |
|----------------|----------------|-----------|----------------|-------|
| OrganisationUnit.Name / Ext_GroupedOrganisation_v2.Site | infrastructure_area.name | varchar(100) | Prefer `Site`, fallback to `OrgUnit.Name` | Trim to 100 chars |
| Ext_GroupedOrganisation_v2.SiteGroup | infrastructure_areagroup.name / infrastructure_area.area_group_id | varchar(100) | Normalize group label; create/reuse top-level area group per geography | Supports Faroe `North/South/West` and similar hierarchies |
| OrganisationUnit.LocationID → Locations.Latitude/Longitude | infrastructure_area.latitude / longitude | numeric(9,6) | Direct | Default `0` if missing |
| Derived | infrastructure_area.max_biomass | numeric | Default `0` | |
| Geography (from 2.1) | infrastructure_area.geography_id | bigint | FK lookup | |
| Derived | infrastructure_area.active | boolean | `true` | |

**Container routing note:**
- Sea area assignment is only used for containers classified as sea; freshwater containers resolve to halls/stations.

### 2.5 Container Mapping (FishTalk: Containers + Ext_GroupedOrganisation_v2)

**Reality check (2026-01-22):** `Containers` contains `OrgUnitID` but not `LocationID`; join path is `Containers.OrgUnitID → OrganisationUnit.LocationID → Locations`. Location is usually missing, so geography should be derived from `Ext_GroupedOrganisation_v2` first.

| FishTalk Source | AquaMind Target | Data Type | Transformation | Notes |
|----------------|----------------|-----------|----------------|-------|
| Containers.ContainerID | infrastructure_container (ExternalIdMap) | uuid | Store for idempotency | `source_model = Containers` |
| Containers.ContainerName | infrastructure_container.name | varchar(100) | Use raw name; strip `FT` prefix/`FW`/`Sea` suffix if present | Trim to 100 chars |
| Containers.ContainerType | infrastructure_container.container_type_id | bigint | Map to `FishTalk Imported Tank` / `FishTalk Imported Pen` | Created during migration |
| Ext_GroupedOrganisation_v2.ProdStage | classification | - | `MARINE`/`SEA` ⇒ sea | Otherwise freshwater |
| Ext_GroupedOrganisation_v2.ContainerGroup / Containers.OfficialID | infrastructure_container.hall_id | bigint | Assign hall for freshwater | Uses hall mapping above |
| Derived | infrastructure_container.area_id | bigint | Assign area for sea | Uses sea area mapping |
| Ext_GroupedOrganisation_v2.StandName / StandID | infrastructure_container.parent_container_id | bigint | Create/reuse structural rack container and link child container | Rack created with `hierarchy_role=STRUCTURAL` |
| Derived | infrastructure_container.hierarchy_role | varchar(20) | `HOLDING` for fish-holding containers; `STRUCTURAL` for synthetic rack nodes | Structural nodes are non-assignable for fish populations |

**Notes**
- Infrastructure classification is `ProdStage` first, then curated site/site-code semantics; there is no implicit freshwater fallback from hall-label presence.
- Pilot component migration still allows member-stage evidence (sea if any member stage is sea), but unresolved rows are skipped with telemetry.
- Container ExternalIdMap metadata stores `site`, `site_group`, `company`, `prod_stage`, `container_group`, `container_group_id`, `stand_name`, `stand_id`, and hierarchy metadata (`parent_container_id`, `hierarchy_role`) where available.
- Names are **presentation only**; `ContainerID` remains the stable identity.
- Missing grouped-organisation rows are expected in current extracts; migration falls back to `Containers.OfficialID` hall label or creates station-scoped placeholder halls.

#### Container Type Mapping (unchanged)

## 3. Batch & Production Mapping

### 3.0 Population Stitching Strategy (Critical)

#### 3.0.0 NEW RECOMMENDED APPROACH: Input-Based Stitching via Ext_Inputs_v2 (2026-01-22)

**CRITICAL DISCOVERY:** The `Ext_Inputs_v2` table tracks **egg inputs/deliveries** — the best available biological input key **for a lifecycle phase**. This is superior to project tuples for identifying the biological cohort at that phase.

**Why Input-Based Stitching:**
- Project tuple `(ProjectNumber, InputYear, RunningNumber)` is a **financial/administrative grouping** that can mix multiple year-classes
- `Ext_Inputs_v2` tracks actual egg deliveries from suppliers (Stofnfiskur, Bakkafrost, etc.)
- The `InputName` field corresponds to "Árgangur" (year-class) shown in FishTalk exports
- A batch should stay in ONE station → ONE area (geography changes are biologically impossible)
- FishTalk `Populations` represent **container/time segments** (often transfers within the same stage), not biological batch identities

| Source | Purpose | Records | Status |
|--------|---------|---------|--------|
| **`dbo.Ext_Inputs_v2`** | Egg input tracking | Links to ~350K populations | **NEW PRIMARY KEY** |
| `dbo.Populations` | Population segments (container/time) | ~350K | Linked via PopulationID |
| `SubTransfers` | Physical movements | ~205K | Transfer workflows |

**Ext_Inputs_v2 Table Structure:**

| Column | Type | Description |
|--------|------|-------------|
| PopulationID | uniqueidentifier | **Direct link to Populations** |
| InputName | nvarchar | Batch name (e.g., "Stofnfiskur S21 okt 25", "BM Jun 24") |
| InputNumber | int | Numeric identifier for the input (opaque; part of batch key) |
| YearClass | nvarchar | Year class (e.g., "2025", "2024") |
| Supplier | uniqueidentifier | Egg supplier ID |
| StartTime | datetime | When eggs arrived |
| InputCount | float | Number of eggs |
| InputBiomass | float | Input biomass |
| Species | int | Species identifier |

**Batch Key:** `InputName + InputNumber + YearClass`

```sql
-- Input-based batch identification
SELECT 
    i.InputName, i.InputNumber, i.YearClass,
    COUNT(DISTINCT i.PopulationID) as pop_count,
    MIN(i.StartTime) as earliest,
    MAX(i.StartTime) as latest,
    DATEDIFF(day, MIN(i.StartTime), MAX(i.StartTime)) as span_days,
    SUM(i.InputCount) as input_count_estimate
FROM dbo.Ext_Inputs_v2 i
WHERE i.InputName IS NOT NULL AND i.YearClass IS NOT NULL
GROUP BY i.InputName, i.InputNumber, i.YearClass
ORDER BY input_count_estimate DESC
-- Result: input_count_estimate is an aggregate; validate with domain knowledge
```

**Sample Results:**

| InputName | InputNumber | YearClass | Pops | Span (days) | InputCount (est) |
|-----------|-------------|-----------|------|-------------|------|
| 22S1 LHS | 2 | 2021 | 317 | 42 | 6.9M* |
| Heyst 2023 | 1 | 2023 | 108 | 275 | 6.3M* |
| Stofnfiskur Aug 22 | 3 | 2022 | 40 | 21 | 5.1M* |
| Rogn okt 2023 | 3 | 2023 | 567 | 19 | 4.7M* |

*`InputCount` is recorded per population segment; summing provides an estimate and must be validated against expected egg counts.

**Algorithm:**
1. Group all populations by `(InputName, InputNumber, YearClass)` from Ext_Inputs_v2
2. Each unique combination = one AquaMind Batch **for that lifecycle phase**
3. Validate: single geography, reasonable time span, and that `InputCount` totals align with expected egg counts (flag for review if not)
4. Map populations to BatchContainerAssignments; use SubTransfers to create transfer workflows

**Operational rollout guardrails (2026-02-16):**
- CSV input-batch migrations run extract freshness preflight by default.
- Default required extract horizon is pinned to backup cutoff `2026-01-22`.
- Migration behavior is profile-driven (`--migration-profile`, default `fw_default`) to keep one core migration engine with auditable cohort-family variants.
- Recommended throughput mode for cohort sweeps remains `--skip-environmental`; full environmental replay is used as canary validation.

### 3.0.0.1 Supplier Codes & Naming Conventions (2026-01-22)

FishTalk uses supplier abbreviations in reporting. These map to full `InputName` values:

| Abbreviation | Supplier | Station(s) | Example InputName |
|--------------|----------|------------|-------------------|
| **BM** | Benchmark Genetics | S24 Strond | "Benchmark Gen. Juni 2024" |
| **BF** | Bakkafrost | S08 Gjógv, S21 Viðareiði | "Bakkafrost S-21 sep24" |
| **SF** | Stofnfiskur | S03, S16, S21, FW22 Applecross | "Stofnfiskur Juni 24" |
| **AG** | AquaGen | S03 Norðtoftir, FW22 Applecross | "AquaGen juni 25" |

**Display Name Format:** `{Supplier Code} {Month} {Year}` (e.g., "BM Jun 24").
Note: some fish groups retain the full `InputProjects.ProjectName` (e.g., “Benchmark Gen. Desembur 2024”) in UI exports; treat abbreviations as **presentation**, not identity.

**Mixed Batches:** When two inputs are combined (e.g., "BF/BM Mai 2024" or "BM Mar/Jun 24"), use `batch_batchcomposition` to track source batches.

**Benchmark Gen. Desembur 2024 (example, verified 2026‑01‑29):**
- `InputProjects.ProjectName`: **Benchmark Gen. Desembur 2024** (fish group label in UI)
- `InputProjectID`: **FE206D1D-C98D-4362-8E19-E18B388E43F3**
- `YearClass`: **2024**
- `ProjectNumber`: **4**
- `Site`: **S24 Strond**
- Supplier code mapping: **BM** (Benchmark Genetics)

### 3.0.0.2 InputName Changes at FW→Sea Transition

**Observed behavior (verify per fish group):**
1. A **new PopulationID** is created when fish transfer between environments (FW → Sea).
2. **InputName continuity is not guaranteed** in `Ext_Inputs_v2`; sea populations often lack `InputName` rows even when FW identity is known.
3. `Ext_Transfers_v2` can contain **explicit FW → MarineSite edges**; when present, it is the canonical, non‑inferred linkage.
4. In the current backup shape, especially from early 2023 onward, sea cohorts frequently appear as **new marine-side input/start events** rather than as a continuous FW batch identity carried into sea geography.
5. Operational implication: FWSEA matching should start from the **destination-side sea input/start signal** and pair it back to the closest plausible **FW depletion/sales** endpoint, not from `InputName` continuity.
6. If no FW sales action is visible, a sudden FW terminal zero followed by a same-geography sea input/first non-zero ring fill remains a valid but lower-confidence candidate.

**Operational code semantics (domain-confirmed, 2026-02-12):**
- `L*` site codes denote **Lívfiskur (broodstock)** stations (for example `L01 Við Áir`).
- `S*` site codes denote freshwater/production **stations** (for example `S08`, `S21`, `S24`).
- `A*` site codes denote marine **areas** (for example `A04`, `A11`, `A12`, `A47`, `A85`).
- `L* -> S*` flows are broodstock/egg supply context and **must not** be classified as FW→Sea linkage evidence.
- FW→Sea linkage candidates are expected at the `S* -> A*` boundary.
- Concrete example (S21, operator-confirmed): on `2025-01-06`, broodstock branch `Lívfiskur -> L01 Við Áir` (`D*..F*` source containers) fans into `S21 Viðareiði -> Rogn -> R1..R7` for `Bakkafrost S-21 jan 25`; classify this as egg-origin/station-seed provenance, not FW→Sea linkage.
- Concrete in-station transition example (S21, operator-confirmed): `Bakkafrost S-21 jan 25` Fry->Parr window (`~2025-07-07..09`) has deterministic lane topology `5M 1/2 -> A01,A03,A05,B10,B11`, `5M 3 -> A01,A05,B10`, `5M 4/5/6 -> A01,A03,B11`; treat this as same-station stage progression evidence (not cross-environment linkage).

**FW->FW station-split lineage qualification (qualified, 2026-02-25):**
- Some cohorts branch between freshwater stations and can surface as destination **Input** lanes with different `InputName` labels.
- Canonical proof for this branch pattern is operation linkage, not naming:
  1. paired `InternalDelivery` sales/input operations at the same start timestamp,
  2. sales-side source populations in station `X`, input-side destination populations in station `Y` (`X != Y`),
  3. destination `Ext_Inputs_v2` row at that timestamp with `InputCount > 0` (often `DeliveryID` blank),
  4. shared `TripID` across sales/input operation metadata when `ParameterID=184` is populated.
- Interpretation guard:
  - destination rows with exact-start zero followed by first non-zero status within 24h should be treated as qualified station-split branch evidence when the operation-link signature above is present; do not classify solely from `InputName` mismatch.
- Qualified examples (semantics only): `S08 Gjógv -> S16 Glyvradalur` (`BF (Fiskaaling) okt. 2023` branch into `Bakkafrost Okt 2023`) and `S08 Gjógv -> S04 Húsar` (`Fiskaaling sep 2022` branch rows).

**Transition sanity semantics (validator, updated 2026-02-16):**
- Bridge-aware transition deltas are downgraded to `incomplete_linkage` (advisory, not hard regression failure) when either condition holds:
  - entry populations have external pre-existing linkage evidence (including `DestPopBefore` outside selected component), or
  - lineage-graph fallback was required to resolve transition sources.
- This prevents false-positive regression-gate failures for cohorts where direct edge linkage is incomplete at stage boundaries.
- Semantic report window end is capped by default to backup horizon date `2026-01-22` (`--window-end-cap-date`) so open-ended rows do not drift to report run time.

**Canonical FW→Sea linkage (CSV extracts, verified 2026‑02‑03):**
- **Full scan (current extract):** `analysis_reports/2026-02-03/fw_to_sea_linkage_scan_2026-02-03.md`
  - `Ext_Transfers_v2` contains **283** FW→MarineSite edges (SourceStage in `{FreshWater, SmoltProduction, Hatchery}`, DestStage = `MarineSite`, classified via `Grouped_Organisation.ProdStage`).
  - **0** of those edges have `SourcePop` or `DestPop` directly in `Ext_Inputs_v2`.
  - **2** edges yield a **unique** `Ext_Inputs_v2` root **via SubTransfers lineage** (`DestPopAfter → SourcePopBefore`).
  - These two unique-root examples are **historical (2010–2011)**; see **Live DB scan** note below for timing.

**Example A (InputName salmoBreed/Bolaks | 1 | 2011):**
- **Ext_Inputs_v2 root:** `6188822A-FC18-4336-B25E-97B014AB4F95`
- **Lineage (SubTransfers):** `45E48633-6E15-4E8C-AD86-919586B0B936 → A702F922-F3DA-41C2-9205-1860DBE384E7 → 5BC9B35B-9D44-4ECD-9B94-15D4BF2828C5 → 6188822A-FC18-4336-B25E-97B014AB4F95`
- **FW population (source):** `45E48633-6E15-4E8C-AD86-919586B0B936`
  - Container: `T5m-28`
  - `Grouped_Organisation.Site = FW11 Barvas`, `ProdStage = Hatchery`
- **Sea population (dest):** `94B34C30-DF7F-4F62-A46C-FDD4AABD6CEF`
  - Container: `MM12`
  - `Grouped_Organisation.Site = S342 MeallMhor`, `ProdStage = MarineSite`
- **Transfer evidence:** `Ext_Transfers_v2` row `SourcePop → DestPop` with `TransferredCount = 23754`, `TransferredBiomassKg = 1683.64`
- **Operation time (SubTransfers):** `OperationID = AB58187A-E38A-442B-BB4B-D607A8F34428`, `OperationTime = 2011‑11‑14 15:28:24`

**Example B (InputName SalmoBreed/Bolaks | 2 | 2010):**
- **Ext_Inputs_v2 root:** `4FDB8EDA-47F5-40CF-97DB-F6E0929D3E55`
- **Lineage (SubTransfers):** `9E3C28A2-9ED6-49A5-AA44-4E06C9CF0CD1 → FB880D26-69EA-41AC-903E-3ED2DC5B913A → 69459EF4-C70B-4B67-8757-FDAD1F7F8CE5 → 7BC27B95-A0AB-4BA5-8B65-60EC1229C39D → 9A39B301-1CE6-4FC8-9F9E-8182659A7D88 → EC7D5D77-8060-4677-8111-C696A49C69F0 → A1AB24B7-E372-4C1A-8E2C-65FCBA00790B → 47AFAE00-AA8C-4D6B-A726-4B6733DAE953 → 4FDB8EDA-47F5-40CF-97DB-F6E0929D3E55`
- **FW population (source):** `9E3C28A2-9ED6-49A5-AA44-4E06C9CF0CD1`
  - Container: `T5m-07`
  - `Grouped_Organisation.Site = FW11 Barvas`, `ProdStage = Hatchery`
- **Sea population (dest):** `F3A4F0AE-8A20-4B3C-86A1-8C99066C5C84`
  - Container: `VB11`
  - `Grouped_Organisation.Site = VuiaBeag`, `ProdStage = MarineSite`
- **Transfer evidence:** `Ext_Transfers_v2` row `SourcePop → DestPop` with `TransferredCount = 19225`, `TransferredBiomassKg = 1463.02`
- **Operation time (SubTransfers):** `OperationID = B45601EF-CE22-42BD-8754-73CCE4A5BF7D`, `OperationTime = 2011‑03‑28 10:46:55`

**Live DB scan (schema + timing, verified 2026‑02‑03):**
- See `analysis_reports/2026-02-03/fishtalk_schema_scan_fw_sea_2026-02-03.md`.
- `PublicTransfers` (base table) contains **311,366** rows and **283** FW→MarineSite edges (same count as `Ext_Transfers_v2`).
- FW→Sea `OperationTime` years in current backup: **2010 (38)**, **2011 (190)**, **2012 (54)**, **2014 (1)**. **No FW→Sea edges exist in 2023+** in the current backup (2026‑01‑22).
- `Ext_Transfers_v2` view definition is **not readable** with `fishtalk_reader` (no `sp_helptext` output), but its columns are visible and its FW→Sea edge count matches `PublicTransfers`.

**Stofnfiskur Aug 2024 (no FW→Sea linkage in current extracts; verified 2026‑01‑29 with 2026‑01‑22 backup):**
- FW anchor (fish group label): `InputProjects.ProjectName = "Stofnfiskur Aug 2024"`
- `InputProjectID`: **AEEDBACC-168E-454E-9C7C-84FAE328D604**
- `YearClass`: **2024**, `ProjectNumber`: **4**, `Site`: **S16 Glyvradalur**
- `Ext_Inputs_v2`: `InputName = "Stofnfiskur Aug 2024"`, `InputNumber = 4`, `YearClass = 2024`, `StartTime = 2024‑08‑08`
- `FishGroupHistory` yields **183 PopulationIDs**, all at **S16 Glyvradalur** (no sea sites)

**Sea populations observed in `Ext_Populations_v2` (name‑based evidence only, not a proven link):**
- **A25 Gøtuvík**: `S01 S16 SF NOV 25 (AUG 24) (*MO)` (container S01)
- **A47 Gøtuvík**: `N01 S16 SF NOV 25 (AUG 24) (*MO)` / `N01 S16 SF NOV 25 (AUG 24) (*½MO)` / `N03 S16 SF NOV 25 (AUG 24)`
- **A11 Hvannasund S**: `03 S16 SF DES 25 (AUG 24) (*MO)`
- **A21 Hvannasund S**: `05 S16 SF DES 25 (AUG 24) (*MO)`

**Linking check (current CSV extracts):**
- `PopulationLinks` and `TransferEdges` show **no cross‑site links** from **S16 Glyvradalur → A25/A47/A21/A11** for this cohort.
- `InputProjects` has **no entries** for the sea population names; `Ext_Inputs_v2` has **no InputName rows** for these sea populations.
- `InternalDelivery` (3155 rows total) contains **10 rows** with `InputSiteID = S16 Glyvradalur`; all **InputOperationID are null**, and none of the linked `SalesOperationID` actions reference **Stofnfiskur Aug 2024** populations (no overlap with `FishGroupHistory` for `AEEDBACC-168E-454E-9C7C-84FAE328D604`).
- `Ext_Transfers_v2` includes cross‑site transfers overall, but **no S16 Glyvradalur cross‑site edges** for this cohort were found in the current extract.
- Backtrace from sea populations (`S16 .* (AUG 24)` in A25/A47/A21/A11) using `Ext_Transfers_v2` yields **only MarineSite→MarineSite** edges within A25/A47 (no FW or S16 sources). See `analysis_reports/2026-01-30/sea_transfer_backtrace_stofnfiskur_aug_2024_2026-01-30.md`.

**Activity Explorer “Input” chain check (S03 → A11 example, verified 2026‑02‑04):**
- **GUI row:** Source `S03 Norðtoftir / Hall 18 Høll A / Unit 1802` → Destination `A11 Hvannasund S / Ring 07 / Official ID A‑11;01093`, Fish group `“07 S03 SF JAN 26 (SEP 24) (MO)”`, Carrier `Tangi 3`, trip `1`, compartment `1`.
- **Container mapping (current CSV extract):**
  - Source container `1802` → `ContainerID = 8197B471-F78A-47B5-A21E-BFE8050DE65E`, `Grouped_Organisation.Site = S03 Norðtoftir`, `ContainerGroup = 18 Høll A`.
  - Destination container `07` → `ContainerID = 468A8053-2CDE-4B9E-AE87-1E5A3FD64D2E`, `OfficialID = A‑11;01093`, `Grouped_Organisation.Site = A11 Hvannasund S`.
- **InternalDelivery evidence:**
  - `InternalDelivery` row: `SalesOperationID = 08F2E1FF-C12F-4ABA-AA79-581F0E170DC7`, `InputSiteID = A11 Hvannasund S`, `InputOperationID = NULL`, `PlannedActivityID = 9E7F2816-E2DC-4325-8A40-B02F54CB758D`.
  - `PlannedActivities` row: `DueDate = 2026‑01‑21 13:29:40`, `Description = "Internal delivery from site S03 Norðtoftir"` (site = A11 Hvannasund S).
  - `internal_delivery_actions` for `SalesOperationID` map **only** to source populations in container `1802` (PopulationIDs `C55D88A4‑B5EA‑4277‑9FE7‑0CCF4E685FA6`, `3D809DA5‑A0E1‑4288‑B4D1‑FF452F65BBE0`); **no actions** found for destination container `07`.
- **Transport metadata:** No carrier/trip/compartment fields appear in `Operations` or `PlannedActivities`, and the schema snapshot contains **no** transport trip/compartment tables or columns. `Ext_Inputs_v2.Transporter` is **null** for all rows in the current extract.
- **Transport tables (CSV, 2026‑02‑04):** `TransportCarrier` now extracted; **Tangi 3** exists (`TransportCarrierID = E3E6DA23‑7A3C‑4E82‑8AA5‑49827D33CE4A`), but there is **no** join path from `InternalDelivery`/`Operations` to this carrier in the current schema/extract.
- **CSV + schema scan (2026‑02‑04):** The only transport‑related columns in extracted CSVs are `Ext_Inputs_v2.Transporter` (all empty), `Ext_Transporters_v2.TransporterID`, `TransportCarrier.TransportMethodID`, and `TransportMethods.TransportMethodID`. Schema transport IDs appear primarily in **Feed/Harvest** tables (`FeedReceptions`, `FeedTransfer`, `HarvestPrognosis*`, `HarvestReports`, `PlanHarvestTrain`, `RHPSingleHarvest`), with **no** linkage to `InternalDelivery`/`Operations` in the current extract.
- **Conclusion (no inference):** The current CSV extract provides a **site‑level internal delivery record** (S03 → A11) but **does not** provide a deterministic link to the destination population or carrier/trip/compartment metadata. This **cannot** be used as canonical FW→Sea linkage yet.
- **Migration runtime-compat workaround (2026‑03‑05):** Because transport leg metadata is non-deterministic/missing, transfer migration persists historical FishTalk edges as **completed direct actions** and forces migrated workflows to **non-dynamic** mode (`is_dynamic_execution=false`, `dynamic_route_mode=NULL`, action `created_via=PLANNED`, `leg_type=NULL`, `executed_at` from operation time). This intentionally side-steps dynamic runtime `handoffs/start` compliance requirements that depend on mandatory start snapshots per physical leg.
- **Sea creation workflow policy guard (2026‑03‑05):** Component migration now skips synthetic `BatchCreationWorkflow` creation for **sea-only** components by default so sea populations are treated as continuation of FW lineage, not egg-origin creates. Business-approved harvested exceptions can opt in explicitly via `--allow-sea-only-creation-workflow`.
- **Continuation rerun safety guard (2026‑03‑05):** Component reruns now block destructive membership shrink by default (safety abort when report membership is smaller than existing mapped membership) and support explicit merge mode (`--merge-existing-component-map`) for linked FW->Sea continuation runs.
- **Sea feed-store bridge (2026‑03‑05):** Feed-store master data was materialized for sea scope and area-linked feed containers were promoted to `BARGE` to ensure sea feed events/purchases are anchored to explicit sea infrastructure assets.
- **MIX placeholder semantics (2026‑03‑05):** `MIX-FTA-*` rows are expected **container-scoped mixed-population placeholders** (not canonical evolving lineage batches), consistent with PRD `3.1.2` and data model `4.2` (`batch_batchmixevent` + `batch_batchmixeventcomponent`). Migration guards now treat these as expected unresolved lineage artifacts in map coverage checks (non-MIX operational assignments must remain fully mapped).
- **Provisional FWSEA continuation caution (2026‑03‑05):** For rows without canonical transfer linkage (`no_canonical_transfer_edge_in_row`), applying **full sea-component membership** to one FW batch can still absorb populations that appear in deferred conflicting candidates for the same sea component. Unique-sea row selection alone is insufficient in this case; continuation apply should use anchor/lineage-scoped sea population subsets or remain manual-review only.
- **Provisional continuation hard guard (2026‑03‑05):** `pilot_migrate_input_batch.py` now blocks linked full-lifecycle continuation runs without explicit anchor scope by default. Operators must provide `--sea-anchor-population-id` (optional `--sea-block-population-id`, lineage tuning via `--lineage-max-hops` / `--lineage-descendants-only`) or explicitly override with `--allow-full-sea-component-for-continuation`.
- **Continuation batch naming (2026‑03‑05):** Linked FW->Sea continuation runs now default to batch naming `<FW batch> - <Sea batch>` (example: `Bakkafrost Jan 2024 - Vár 2025`). Renames are applied through normal model save paths (`save_with_history`) so batch history/audit trail records the name-change event.

**Implication:** `Ext_Transfers_v2` / `PublicTransfers` + `Populations` + `Grouped_Organisation` provide the **only proven FW→Sea linkage** in current extracts (when present). `Ext_Inputs_v2` remains the **only** deterministic batch identity, but sea endpoints often surface as **new input/start rows** with no direct FW identity carry-through. In practice, active-cohort FWSEA matching is an **endpoint-pairing** problem: FW depletion/sales vs sea input/first-fill, then anchor-scoped lineage. Do **not** infer FW→Sea linkage purely from naming.

**Active‑batch constraint (current backup):**
- `InputProjects.Active` exists in the extract (948 active, 1227 inactive as of 2026‑01‑22).
- **No FW→Sea edges exist in 2023+**, so **active cohorts cannot be stitched** via `Ext_Transfers_v2`/`PublicTransfers` in the current backup.
- If we migrate **active batches only**, FW and Sea segments will remain **unlinked** until a newer FishTalk dataset or explicit transfer report provides deterministic FW→Sea linkage.

**Endpoint-pairing diagnostic status (tooling-only, 2026-02-12):**
- Gate-matrix artifacts now include explicit blocker-family fields and cohort-level recommended actions (`scripts/migration/tools/fwsea_endpoint_gate_matrix.py`).
- FW20 strict profile (`max-source-candidates=2`, `min-candidate-rows=10`): `PASS 1/20`, non-zero candidate cohorts `7` split into `1` true candidate, `1` sparse candidate, `3` reverse-flow FW-only, `2` unclassified.
- FW20 combined diagnostic profile (`max-source-candidates=3`, `min-candidate-rows=4`): `PASS 3/20`, non-zero candidate cohorts `7` split into `3` true candidates, `1` sparse candidate, `3` reverse-flow FW-only.
- Reverse-flow blocker family remains stable across profiles (`direction_mismatch`, `input_to_sales`, dominant stage pair `fw->fw`) and is excluded from FW→Sea policy evidence.
- Reverse-flow blocker rows centered on `L01 Við Áir -> S08/S21` are consistent with broodstock supply semantics (`L* -> S*`) and remain outside FW→Sea evidence scope.
- Reference artifacts:
  - `analysis_reports/2026-02-12/fw20_endpoint_gate_matrix_blocker_family_tooling_integration_2026-02-12.md`
  - `analysis_reports/2026-02-12/fw20_endpoint_gate_matrix_with_blocker_family_2026-02-12/fw20_endpoint_gate_matrix.summary.json`
  - `analysis_reports/2026-02-12/fw20_endpoint_gate_matrix_diag_source3_min4_with_blocker_family_2026-02-12/fw20_endpoint_gate_matrix.summary.json`
  - `analysis_reports/2026-02-12/fw20_reverse_flow_xe_capture_readiness_2026-02-12.md`

**Reverse-flow targeted SQL signature confirmation (read-only source extract, 2026-02-12):**
- Deterministic trace-target pack published for all persistent reverse-flow blockers (`3` rows, `6` operation IDs):
  - `analysis_reports/2026-02-12/fw20_reverse_flow_trace_target_pack_2026-02-12.md`
  - `analysis_reports/2026-02-12/fw20_reverse_flow_trace_target_pack_2026-02-12.summary.json`
- Targeted SQL extraction (`targeted_action_extract.py`, `fishtalk_readonly`) confirms stable operation signature:
  - sales-side `OperationType=7` with broader metadata (includes `ParameterID=220`),
  - component-side `OperationType=5` with no `ParameterID=220`,
  - all observed endpoint stage classes are FW.
- Reference artifact:
  - `analysis_reports/2026-02-12/fw20_reverse_flow_targeted_sql_extract_signature_2026-02-12.md`

**Non‑canonical heuristic candidates (review only, 2026‑02‑03):**
- `analysis_reports/2026-02-03/fw_to_sea_heuristic_candidates_postsmolt_2026-02-03.md` (summary) and `fw_to_sea_heuristic_candidates_postsmolt_2026-02-03.csv` (top‑5 candidates per sea population).
- Method (heuristic): parse sea `PopulationName` pattern (e.g., `S07 S21 SF NOV 25 (JUN 24)`), match FW station code to `Grouped_Organisation.Site`, and rank FW candidates by **date proximity** (FW `EndTime` vs sea `StartTime`) with **optional count alignment** (`status_values.csv` last FW count vs first sea count).
- **Overlay applied:** FW candidates restricted to **Post‑Smolt halls** using qualified Faroe hall mappings.
- **Result (2026‑02‑03 run):** 1,315 sea populations matched the naming pattern with post‑smolt FW candidates; **0** candidates matched `Benchmark Gen. Juni 2024` (BM/JUN 2024) and **0** matched `Bakkafrost S‑21 sep24` (BF/SEP 2024). Heuristic stitching for those two batches produced **0** FW→Sea additions.
- **Heuristic validation (non‑canonical, 2026‑02‑03):**
  - **Bakkafrost feb 2024|1|2024:** 4 heuristic additions (**2 sea + 2 FW**) when using default `--heuristic-min-score 70` (sea names: `21 S16 BF JUN 25 (FEB 24)` and `22 S16 BF JUN 25 (FEB 24)` at **A13 Borðoyavík**; FW source halls in **S16 Glyvradalur** `E1/E2 Høll` with day deltas ~‑2 to ‑1 and count ratios ~1.2–1.4 where counts exist). See `scripts/migration/output/input_stitching/full_lifecycle_population_members_Bakkafrost_feb_2024_1_2024.csv` (flag `heuristic_fw_sea`) and `heuristic_fw_sea_links_Bakkafrost_feb_2024_1_2024.csv` (all scored candidate pairs).
  - **Migration run (heuristic, 2026‑02‑03):** Full‑lifecycle migration for `Bakkafrost feb 2024|1|2024` completed against `aquamind_db_migr_dev` using CSV‑only + heuristic stitching (`--full-lifecycle --heuristic-fw-sea --heuristic-min-score 70 --include-fw-batch 'Bakkafrost feb 2024|1|2024' --max-fw-batches 1 --max-pre-smolt-batches 0`). Resulting batch: **id 347**, `batch_number = "Bakkafrost feb 2024"`. Counts: **assignments 24**, **transfer workflows 3 / actions 20** (stage workflows), **feeding 263**, **growth samples 84**, **mortality 720**. Treatments/lice/journal were **skipped** (CSV‑only mode), and environmental/feed‑inventory were **explicitly skipped**. GUI: `http://localhost:5002/batch-details/347`.
  - **Resulting stage totals (DB‑verified, 2026‑02‑03):** Egg&Alevin **1,440,000**; Fry **359,684**; Post‑Smolt **260,803**; Adult **284,810**. (Smolt/Parr absent in this run.)
  - **Important limitation (qualified):** S16 hall `Uppstilling broytt ‑ A Høll` remains **unmapped**; any populations in that hall still rely on FishTalk stage fallback (last stage). Confirming this hall’s stage is needed for full accuracy.
  - **Stofnfiskur Juni 2023|2|2023:** 169 heuristic additions (flagged in `full_lifecycle_population_members_Stofnfiskur_Juni_2023_2_2023.csv`). Candidate scores/ratios in `heuristic_fw_sea_links_Stofnfiskur_Juni_2023_2_2023.csv` are broad and require manual verification.
  - **Stofnfiskur Septembur 2023|3|2023:** 82 heuristic additions (flagged in `full_lifecycle_population_members_Stofnfiskur_Septembur_2023_3_2023.csv`). Candidate scores/ratios in `heuristic_fw_sea_links_Stofnfiskur_Septembur_2023_3_2023.csv` are broad and require manual verification.
- **Do not use** for deterministic stitching; this is a **review aid** only until a transfer report or newer backup provides canonical linkage.

**Temporal depletion->fill pairing policy (non-canonical, review only, 2026-02-17):**
- Use this when canonical `PublicTransfers` / `Ext_Transfers_v2` FW->Sea edges are absent for in-scope cohorts.
- Candidate boundary is restricted to `S* -> A*` transitions inside the same geography; exclude `L* -> S*` broodstock and FW->FW flows.
- Define FW terminal signal date `X` from source segment end/depletion evidence (segment `EndTime`, transfer-out, culling, mortality footprint).
- Accept sea candidate entry rows with start/fill timestamps in `[X, X+2 days]` (tunable to +3 days only with explicit operator sign-off).
- Rank by time delta first; use count/biomass alignment as secondary tie-breakers when snapshot evidence exists.
- Persist these links as **provisional migration-tooling evidence**, never as deterministic runtime truth, until corroborated by transfer tables or external report evidence and semantic gate pass.

**Linkage sources (ranked):**
- **Boundary qualifier (operator-confirmed):** Treat only `S* -> A*` transitions as FW→Sea candidate boundary. Classify `L* -> S*` as broodstock/egg supply context and exclude from FW→Sea linkage evidence.
- **Primary (edge):** `PublicTransfers` / `Ext_Transfers_v2` + `Populations` + `Grouped_Organisation` (filter FW‑stage → `MarineSite`)
- **Primary (identity):** `SubTransfers` lineage (`DestPopAfter → SourcePopBefore`) to a **unique** `Ext_Inputs_v2` root
- **Fallback candidates:** `InternalDelivery` (SalesOperationID / InputSiteID / InputOperationID), Sales/Delivery/Closing tables if present
- **Fallback semantic candidates (non-canonical):** temporal depletion->fill pairing (`FW terminal date = X`, sea entry `[X, X+2 days]`) in same geography and `S* -> A*` boundary.
- **Diagnostic-only acceptance tooling:** `fwsea_endpoint_pairing_gate.py` + `fwsea_endpoint_gate_matrix.py` (deterministic cohort classification for policy-readiness evidence); `fwsea_trace_target_pack.py` for SQL trace target generation.
- **Activity Explorer “Input” (GUI‑observed):** Appears to encode FW unit → Sea unit moves with **TransportCarrier / trip / compartment** metadata. CSV extracts now include `TransportCarrier`, `TransportMethods`, `Ext_Transporters_v2` (2026‑02‑04), and operation-linked metadata (`ActionMetaData` params `184/220`) can be scoped through `InternalDelivery` operation chains; however, there is still **no deterministic join path** from those operation chains to transport entities/trip-compartment records in the current extract, and `Ext_Inputs_v2.Transporter` is **null** in the 2026‑01‑22 extract.
- **Name hints only:** `Ext_Populations_v2.PopulationName`
- **External transfer reports (non‑canonical, 2026‑02‑04):** Week‑5 FW/Sea PDF analyses provide **explicit FW hall → sea area** plans (e.g., Hvannasund S transfer plan). See `analysis_reports/2026-02-04/fw_sea_transfer_report_candidate_scan_2026-02-04.md` for a candidate mapping and DB cross‑checks. These links are **external‑report–sourced** unless corroborated by transfer tables.

Use `SubTransfers` for lineage stitching (including FW→Sea). It **can** include FW→MarineSite transitions in the current extract.

### 3.0.0.3 AquaMind Batch Naming Strategy

**Scope:** This section documents how migration tooling assigns `batch_batch.batch_number`. It is not a FishTalk field.

**Verified behavior (migration scripts, 2026‑01‑30):**
- `scripts/migration/tools/pilot_migrate_input_batch.py` sets `batch_number = args.batch_number or batch_info.input_name` → **default is `Ext_Inputs_v2.InputName`** for the batch key.
- `scripts/migration/tools/pilot_migrate_component.py` uses `--batch-number` if provided; otherwise defaults to `FT-{component_key[:8]}-{slug}` (slug derived from the representative population label), truncated to 50 chars.
- `Batch.batch_number` max length is 50; current `ext_inputs.csv` has **max InputName length = 39** (no values > 50 in the 2026‑01‑22 extract).

**History & traceability (code‑verified):**
- `Batch` is tracked by `django-simple-history` (`history = HistoricalRecords()`), and migration scripts use `save_with_history` when creating/updating batches, so **batch_number changes are recorded** in `HistoricalBatch`.
- `ExternalIdMap` entries for `source_model = "PopulationComponent"` store `metadata.batch_number` at creation time (from `pilot_migrate_component.py`).

**Not implemented in migration scripts:**
- No automatic rename to supplier‑code display format is present; any rename would require an explicit `--batch-number` override or a post‑migration edit.

### 3.0.0.4 Ext_Populations_v2 - Supplementary Batch Data

**Observed columns (current extract, 2026‑01‑22 backup):**

| Column | Type | Description |
|--------|------|-------------|
| PopulationID | uniqueidentifier | Links to `Populations` |
| ContainerID | uniqueidentifier | Container location |
| PopulationName | nvarchar | Free‑text label (heterogeneous formats) |
| SpeciesID | int | Species identifier |
| StartTime | datetime | Population segment start |
| EndTime | datetime | Population segment end (nullable) |
| InputYear | char(2) | Project tuple field (two‑char code, digits or letters) |
| InputNumber | char | Project tuple field (digits or letters) |
| RunningNumber | int | Project tuple field |
| Fishgroup | nvarchar | Fish group number/code (always populated in extract) |

**Field behavior (observed in extract):**
- `StartTime/EndTime` in `Ext_Populations_v2` **match `Populations.StartTime/EndTime` exactly** for all 184,234 rows (0 mismatches).
- `EndTime` is **missing in 1,682 rows**; treat these as open segments until closed in source data.
- `PopulationName` is **not uniform**; 5 rows are blank.
- `InputYear` is **always 2 characters**; 5,889 rows use **non‑digit codes** (e.g., `AA`, `AB`).
- `InputNumber` can be **digits or letters**; 13,418 rows are non‑numeric.
- `Fishgroup` format aligns with tuple fields for almost all rows:
  - `Fishgroup ~= InputYear + InputNumber + "." + RunningNumber(4-digit zero-padded)`
  - Verified for **184,229 / 184,234** rows in current extract.
  - 5 observed outliers are all `InputNumber=99` special-format cases (`Fishgroup=23999.000` while tuple formatting would produce `2399.000x`).

**PopulationName patterns (MarineSite only, observed—not guaranteed):**
Examples from the current extract include:
- `07 S16 SF OKT 24 (APR 23)`
- `HS_SB 20 S1`
- `Vár 2009`
- `S08-FA`

Only **1,667 of 56,800** MarineSite names match the previously assumed
`"{Ring} {Station} {Supplier} {Month} {Year} ({YearClass})"` pattern. Treat `PopulationName` as a **hint only**; do not rely on it for deterministic FW→Sea or batch identity.

**Usage guidance (qualified):**
- `PopulationName`, `InputYear`, `InputNumber`, `RunningNumber`, and `Fishgroup` are **project‑tuple attributes**, not a biological batch key (see 3.0.1).
- Use `Ext_Populations_v2` mainly for **additional labeling/context** and for verifying `PopulationID → ContainerID` + time ranges.
- In current migration code, `first_stage/last_stage` token signals (from stitched member rows) are operational stage hints only; they are not identity keys.
- Some FW22 rows have blank stage tokens and sparse grouped-organisation metadata; migration tooling now uses controlled fallback (batch lifecycle stage + telemetry) for those rows instead of aborting the entire cohort.

### 3.0.0.5 FishGroupHistory + InputProjects (Fish group anchor)

**Purpose (schema‑level):** `FishGroupHistory` maps `PopulationID → InputProjectID`. `InputProjects` holds the project attributes for each `InputProjectID`.

**Key facts (current extract, 2026‑01‑22 backup):**
- `FishGroupHistory` has **2 columns**: `PopulationID`, `InputProjectID` (232,007 rows; 205,010 unique PopulationIDs; 2,078 unique InputProjectIDs).
- All `FishGroupHistory.PopulationID` values exist in `Populations` (**0 missing**).
- All `FishGroupHistory.InputProjectID` values exist in `InputProjects` (**0 missing**).
- `InputProjects` columns in extract: `InputProjectID`, `SiteID`, `Species`, `YearClass`, `ProjectNumberOld`, `ProjectName`, `Active`, `ProjectNumber`.
- `Ext_Populations_v2` includes a `Fishgroup` code column (0 blanks in extract) and **does not include a FishGroupName column**.
- For `Stofnfiskur S-21 nov23` (`B884F78F-1E92-49C0-AE28-39DFC2E18C01`), `FishGroupHistory` resolves all **288** component populations to a single `InputProjectID` (`DE478E8A-34C5-4C12-86BA-6A20B16AEBF2`).

**Recommended usage (for container history tracing, qualified):**
1. If you have an `InputProjectID`, use `FishGroupHistory` to collect all `PopulationID` values.
2. Join those populations to `Populations` / `Ext_Populations_v2` for container/time and to `Ext_GroupedOrganisation_v2` for hall/site context.
3. If you need a **human‑readable label**, use `InputProjects.ProjectName` (this is how the batch overview reports label fish groups; UI parity is not asserted here).

**UI observation (FishTalk, 2026‑02‑04):**
- The GUI view **“Input projects for A11 Hvannasund S”** lists per‑site inputs with columns: *Site, Species, Year class, Project number, Input name, # of fish, Avg weight, Biomass (kg), # of eggs, Active*.
- This supports that `InputProjects` are **site‑scoped** (`InputProjects.SiteID`) and represent what is **entered/active at a site**. The counts shown in the GUI are **not present** in `InputProjects` extract columns, so they are likely computed from status/weight tables rather than stored on `InputProjects`.

**Identity note:** `InputProjects` is a project‑level grouping, not a biological batch key (see 3.0.1). Use `Ext_Inputs_v2` for biological batch identification.

#### 3.0.0.6 Population Semantics (Migration Handling, 2026-01-30)

**What the extracts show (current CSVs):**
- Many operational tables are keyed by `PopulationID` (e.g., `feeding_actions.csv`, `mortality_actions.csv`, `ext_weight_samples_v2.csv`, `status_values.csv`).  
  `public_weight_samples.csv` is a duplicate of `ext_weight_samples_v2.csv` in this backup; **use Ext only**.
- `Ext_Transfers_v2` links **SourcePop → DestPop** (both PopulationIDs). In the current extract: 311,366 rows and **0 self‑edges** (`SourcePop != DestPop` for all rows).
- `SubTransfers` tracks `SourcePopBefore/After` and `DestPopBefore/After` (PopulationIDs), implying before/after segment IDs are distinct in transfer history.

**Migration behavior (code‑verified):**
- `pilot_migrate_component.py` creates **one `batch_batchcontainerassignment` per PopulationID** and stores an `ExternalIdMap` entry with `source_model = "Populations"`.
- Batches are created **per component** (`PopulationComponent`) or **per input key** (`Ext_Inputs_v2.InputName|InputNumber|YearClass`), not per PopulationID (see `pilot_migrate_component.py` and `pilot_migrate_input_batch.py`).

**Implications (migration policy):**
- Treat `PopulationID` as the **atomic assignment/transfer node** used by event tables and transfer edges.
- Do **not** create `batch_batch` per PopulationID; batch identity comes from `Ext_Inputs_v2` (biological input) or the stitched component key.

#### 3.0.0.7 Event Replay Blueprint (Schema-Level, 2026-02-04)

**Goal:** Establish a deterministic, schema-driven event stream that can be “replayed” to rebuild batch history in AquaMind. This is **schema-only** guidance; data completeness must be validated per extract.

**Core tables (actuals):**
- **`Operations`**: time axis (`OperationID`, `StartTime`, `OperationType`).
- **`Action`**: per‑population event rows (`ActionID`, `OperationID`, `PopulationID`, `ActionType`, `ActionOrder`).
- **Domain tables** keyed by `ActionID` (e.g., Feeding, Mortality, WeightSamples, Lice, Treatments, etc.).
- **Transfer edges**: `SubTransfers`, `PublicTransfers`, `PopulationLink` (lineage/moves via `OperationID` + PopulationIDs).

**Reference decoding:**
- `PublicOperationTypes` maps `Operations.OperationType → Text` (CSV: `public_operation_types.csv`, 44 rows).
- No schema‑level mapping exists for `Action.ActionType`; decoding must be inferred via domain tables or UI references. **Targeted scan (2026‑02‑04)** only matched InternalDelivery actions (ActionType 4/7/25), so broader sampling is still required.
- **Empirical ActionType mapping (domain tables, 2026‑02‑04):** `3→Mortality`, `5→Feeding`, `16→Culling`, `18→Escapes`, `21/22/58→Treatment`, `30→HistoricalSpawning`, `31→HistoricalHatching`, `32→HistoricalStartFeeding`, `46→SpawningSelection`, `53→HarvestResult`, `54→UserSample*`. Weight samples and several health/environment categories still lack ActionType decoding because their tables do **not** expose `ActionID`.

**Replay order (schema‑level):**
1. Build a chronological event list from `Operations` (use `StartTime` as event time; join to `PublicOperationTypes` for labels).
2. Attach `Action` rows by `OperationID` to get the affected `PopulationID` set and per‑op event ordering (`ActionOrder`).
3. Enrich each Action from domain tables via `ActionID` (Feeding, Mortality, Lice, Treatments, WeightSamples, etc.).
4. Apply lineage/movement edges:
   - `SubTransfers` for within‑environment lineage and share propagation (`SourcePop*` → `DestPop*`).
   - `PublicTransfers` for legacy explicit transfers (`SourcePop` → `DestPop`).
   - `PopulationLink` for additional cross‑population links (when present).
5. Treat `Plan*` tables (`PlanPopulation`, `PlanTransfer`, `PlanAction`, `PublicPlanPopulationAttributes`) as **planning context**, not actuals.

**Extraction guidance:** `Action` + `ActionMetaData` are very large; use **targeted extraction** by date window or OperationID set (see `scripts/migration/tools/targeted_action_extract.py`).
For FWSEA blocker follow-up, generate deterministic operation target packs from gate-matrix outputs first (see `scripts/migration/tools/fwsea_trace_target_pack.py`), then run targeted extraction and local XE/Profiler capture on that exact operation set.
For cohort in-station lifecycle topology (e.g., `Rogn -> 5M -> A/BA/BB -> C/D -> E/F`), derive deterministic `SubTransfers` `SourcePopBefore -> DestPopAfter` edges from an `Ext_Inputs_v2` batch key using `scripts/migration/tools/cohort_subtransfer_transition_report.py` (reference: `analysis_reports/2026-02-13/s21_bakkafrost_jan25_subtransfers_deterministic_transition_evidence_2026-02-13.md`).

##### MVP Replay Spec (Draft, 2026‑02‑04)

**Objective:** Build a deterministic, auditable event stream that can reconstruct **within‑environment** history for each PopulationID and persist it in AquaMind. Cross‑environment links are only included when explicit edges exist.

**Inputs (minimum):**
- `Operations`, `Action`, domain tables keyed by `ActionID` (Feeding, Mortality, Treatment, Culling, UserSample, etc.).
- Transfer edges: `SubTransfers`, `PublicTransfers`, `PopulationLink`.
- Reference tables: `PublicOperationTypes`, `ProductionStages`, `Grouped_Organisation`, `Populations`, `Containers`.
- Sample tables without ActionID: `PublicLiceSamples`/`PublicLiceSampleData` and `Ext_WeightSamples_v2` (eventized by SampleDate).

**Event model (per event row):**
`event_id`, `event_time`, `population_id`, `operation_id` (nullable), `action_id` (nullable), `event_type`, `event_subtype`, `metrics`, `source_table`, `external_id`.

**Replay steps:**
1. **Reference maps**:  
   - `OperationType → label` from `PublicOperationTypes`.  
   - `ActionType → label` from empirical mapping (domain‑table sampling).  
   - `PopulationID → container/site/stage` from `Populations` + `Grouped_Organisation`.
2. **Action events (primary):**  
   - Join `Action` → `Operations` for time and type, then enrich via domain tables keyed by `ActionID`.  
   - Use `ActionOrder` for within‑operation ordering.
3. **Operation events (secondary):**  
   - Create an event for any `Operations` row that has **no Action** rows (retains timeline continuity).
4. **Sample events (no ActionID):**  
   - Lice: `PublicLiceSamples` + `PublicLiceSampleData` (and `Ext_` variants) → event type `lice_sample` (time = `SampleDate`).  
   - Weight: `Ext_WeightSamples_v2` → event type `weight_sample` (time = `SampleDate`), **filter `OperationType=10`**.  
   - These events are **not** linked to `Action`/`Operation`.
5. **Transfer/lineage events:**  
   - `SubTransfers`/`PublicTransfers` become `transfer` events (time from `Operations.StartTime` or `OperationTime`).  
   - `PopulationLink` becomes `link` events (time from `Operations.StartTime`).
6. **Ordering:**  
   - Sort by `event_time`, then by `operation_id`, then `action_order` (if present).  
   - Stable tie‑break: `event_id`.
7. **Persistence (AquaMind):**  
   - Create/attach `batch_batchcontainerassignment` per `PopulationID`.  
   - Emit events into domain models (feeding, mortality, treatments, weight samples, lice samples).  
   - Record `ExternalIdMap` per source event (`event_id`) for idempotency.

**Success criteria (MVP):**
- Replays **within‑environment** history deterministically for a batch/component.  
- Preserves event ordering and key metrics from FishTalk.  
- Produces a single event stream that can be re‑run idempotently.

**Known limits (current backup):**
- FW→Sea links missing for 2023+ (replay cannot create cross‑environment lineage without explicit edges).
- Some domains lack `ActionID`/`OperationID` (lice/weight samples) → sample‑date eventization only.

#### 3.0.1 Deprecated: Project-Based Stitching (Legacy Only)

**Status:** Not used in current migration flow. Kept for historical context and to discourage reuse.

**What “project‑based” means:** Grouping populations by the tuple `(ProjectNumber, InputYear, RunningNumber)` from `Populations` / `Ext_Populations_v2`.

**Why deprecated (policy):** The current migration pipeline uses **input‑based** or **component‑based** identifiers instead of project tuples.

**Current strategy (code‑verified):**
- **Input‑based:** `Ext_Inputs_v2` key `InputName|InputNumber|YearClass` via `scripts/migration/tools/pilot_migrate_input_batch.py`.
- **Component‑based:** `PopulationComponent` key via `scripts/migration/tools/pilot_migrate_component.py`.

**Legacy tooling (do not use for new runs):**
- `scripts/migration/legacy/tools/pilot_migrate_project_batch.py`
- `scripts/migration/legacy/tools/project_based_stitching_report.py`

#### 3.0.2 Transfer Workflows (SubTransfers‑based, current extracts)

**What’s in the extract (2026‑01‑22 backup):**
- `sub_transfers.csv`: 204,788 rows
- `transfer_operations.csv`: 71,287 rows
- `transfer_edges.csv`: 307,417 rows
- `operation_stage_changes.csv`: 26,937 rows (stage change events; used by analysis tooling, not transfer migration)

**SubTransfers structure (from extract):**
- Keys: `SubTransferID`, `OperationID`
- Edges: `SourcePopBefore/After`, `DestPopBefore/After` (PopulationIDs)
- Timing: `OperationTime`
- Shares: `ShareCountFwd`, `ShareBiomFwd`, `ShareCountBwd`, `ShareBiomBwd`

**Observed behavior (qualified):**
- Using `Grouped_Organisation.ProdStage` as environment classification, `SubTransfers` contains **283 FW→MarineSite edges** in the current extract (SourcePopBefore → DestPopAfter). This means SubTransfers **can** include FW→Sea transitions in this dataset.

**Migration usage (code‑verified):**
- `scripts/migration/tools/pilot_migrate_component_transfers.py` uses SubTransfers when `--use-subtransfers` is supplied.
- PublicTransfers are **not present in current CSV extracts**; the script’s PublicTransfers path requires live SQL and is not validated here.

**Notes:**
- `transfer_edges.csv` / `transfer_operations.csv` are available in extracts but are **not used** by `pilot_migrate_component_transfers.py` as of 2026‑01‑30.

#### 3.0.3 Deprecated: Hybrid Cross‑Project Linking (Legacy Only)

**Status:** Not used in current migration flow. Kept to discourage re‑introducing project‑tuple chaining.

**What it was:** A legacy attempt to connect SubTransfers chains across project tuples, aggregating multiple populations into a single batch.

**Why deprecated (policy):** Current migration identifies batches via **input‑based** (`Ext_Inputs_v2`) or **component‑based** (`PopulationComponent`) keys. Chaining by project tuple is inconsistent with that strategy.

**Operational guidance:** Do not use the legacy `--link-by-project` flag (if encountered in older scripts or notes).

### 3.1 Batch Mapping (FishTalk: Ext_Inputs_v2 + derived aggregates)

**Current migration behavior (code‑verified):**

| Source / Derivation | AquaMind Target | Data Type | Transformation | Notes |
|---------------------|-----------------|-----------|----------------|-------|
| `PopulationComponent` key | `ExternalIdMap` (Batch) | uuid | `source_model = "PopulationComponent"`, `source_identifier = component_key` | Idempotency anchor for batches in `pilot_migrate_component.py`. |
| `--batch-number` argument (if supplied) | `batch_batch.batch_number` | varchar(50) | Direct | Overrides default naming. |
| `InputName` (input‑based pipeline default) | `batch_batch.batch_number` | varchar(50) | Direct | Set by `pilot_migrate_input_batch.py` when `--batch-number` is not provided. |
| Component fallback (no `--batch-number`) | `batch_batch.batch_number` | varchar(50) | `FT-{component_key[:8]}-{slug}` | Used by `pilot_migrate_component.py` when no override is supplied. |
| `members` (stitched populations) | `batch_batch.start_date` | date | `min(member.start_time).date()` | Derived from population start times. |
| Active frontier stage set (profile default) | `batch_batch.lifecycle_stage_id` | bigint | Most advanced stage among active-container frontier candidates within `lifecycle_frontier_window_hours` (default 24h) | Profile mode `frontier` (`fw_default`) in `pilot_migrate_component.py`. |
| Stage fallback modes | `batch_batch.lifecycle_stage_id` | bigint | Fallback to latest-member stage, then first resolvable stage across members | Used when frontier candidates are unavailable or profile mode is `latest_member`. |
| Activity window (see below) | `batch_batch.status` | varchar | `ACTIVE` / `COMPLETED` | Based on latest status vs active window. |
| Activity window (see below) | `batch_batch.actual_end_date` | date | `component_status_time.date()` or latest member end date | Only set when batch is not active. |
| Script notes | `batch_batch.notes` | text | `FishTalk stitched component {component_key}; representative='{representative}'` | Current migration note string. |
| Defaults | `batch_batch.batch_type` | varchar | Model default | No explicit assignment in migration script. |
| Defaults | `batch_batch.expected_end_date` | date | None | Not set by migration scripts. |

#### Status Mapping (Derived from Activity)

- Source: `PublicStatusValues` (`status_values.csv` in extracts).
- The script computes `global_status_time = max(StatusTime)` across all populations.
- `active_cutoff = global_status_time - active_window_days` (default 365; `--active-window-days`).
- `component_status_time = max(latest_status_time_by_pop)` for the batch’s member populations.
- The script evaluates whether each population’s **latest** status snapshot is non-zero (`CurrentCount > 0` or `CurrentBiomassKg > 0`).
- Active container ownership is constrained to one latest non-zero holder per container and can exclude candidates when a later outside-component holder exists (profile default behavior).
- Batch `status = ACTIVE` only when there is non-zero latest status evidence within `active_cutoff` (fallback: open-ended `member.end_time is None` if status evidence is missing).
- `actual_end_date` is set only when not active; it uses `component_status_time.date()` if available, else latest member `end_time`.

#### Snapshot Alignment with AquaMind Data Model

FishTalk status rows are treated as **state snapshots**, not as identity or event rows. They do **not** map 1:1 to a dedicated runtime table in AquaMind.

Current mapping into `aquamind/docs/database/data_model.md` entities is:
- `status_values.csv` / `PublicStatusValues` -> `batch_batch.status` + `batch_batch.actual_end_date` (batch activity classification).
- `status_values.csv` / `PublicStatusValues` -> `batch_batchcontainerassignment.population_count` (status-authority overlays), `batch_batchcontainerassignment.biomass_kg`, `batch_batchcontainerassignment.avg_weight_g`, `batch_batchcontainerassignment.is_active`, `batch_batchcontainerassignment.departure_date`.
- Snapshot-implied weight/biomass context -> event replay calculations (for example mortality/culling/escape biomass estimation when source biomass is absent).

This keeps AquaMind runtime FishTalk-agnostic: operational truth remains in normalized AquaMind entities (`batch_batchcontainerassignment`, `batch_batchtransferworkflow`, `batch_transferaction`, `batch_mortalityevent`, `inventory_feedingevent`, `batch_growthsample`, `health_*`), while snapshots are migration-time evidence inputs.

### 3.2 Container Assignment Mapping (Stitching Output + PublicStatusValues)

Assignments are created **per PopulationID** from the component stitching output (`population_members.csv`), and enriched with status snapshots from `status_values.csv`.

**Source files used by `pilot_migrate_component.py` (CSV mode):**
- `population_members.csv` (generated by `pilot_migrate_input_batch.py` or legacy stitching): `population_id`, `container_id`, `start_time`, `end_time`, `first_stage`, `last_stage`
- `containers.csv` (container FK resolution)
- `status_values.csv` (biomass snapshots + status-authority count overlays)
- `ext_inputs.csv` (InputCount seed for conservation-based counts)
- `sub_transfers.csv` (ShareCountFwd propagation for conservation-based counts)

**Field mapping (code‑verified):**

| Source / Derivation | AquaMind Target | Data Type | Transformation | Notes |
|---------------------|-----------------|-----------|----------------|-------|
| `population_id` | `ExternalIdMap` (Populations) | uuid | `source_model = "Populations"` | Idempotency for assignments. |
| `container_id` | `batch_batchcontainerassignment.container_id` | bigint | FK lookup | Required. |
| `start_time` | `batch_batchcontainerassignment.assignment_date` | date | `start_time.date()` | Required; rows without start_time are skipped upstream. |
| `first_stage` / `last_stage` + hall/site context | `batch_batchcontainerassignment.lifecycle_stage_id` | bigint | Stage resolution order: hall mapping -> component-local unanimous hall fallback -> token mapping (`fishtalk_stage_to_aquamind`). FW22-specific rule: prefer explicit member stage token over static hall mapping when token exists. Last-resort sparse-metadata fallback uses batch lifecycle stage with telemetry. | Requires `LifeCycleStage` master rows. |
| SubTransfers propagation (see below) | `batch_batchcontainerassignment.population_count` | int | Seed with `Ext_Inputs_v2.InputCount`, propagate via `SubTransfers.ShareCountFwd`, then apply status-authority overlays: completed populations use exact start-time status tie-break resolution (same timestamp: non-zero first, then max count/biomass), and if that resolved snapshot is non-zero, use it as authoritative count; open populations use latest measured status count; otherwise fallback overlays apply (zero-conserved + non-zero status, external-mixing uplift, known-removals floor, same-stage bridge suppression/classification). Optional profile guard suppresses orphan zero assignments lacking stage tokens, SubTransfers touch, and count/removal evidence. | Conservation-based with status-priority overlays for lane-level parity. |
| Status snapshot (see below) | `batch_batchcontainerassignment.biomass_kg` | numeric | Start from `CurrentBiomassKg`; if status average weight is available, recompute biomass against the chosen assignment count (`count * status_avg_weight / 1000`) | Keeps count/biomass consistency when count source differs from status count. |
| Derived | `batch_batchcontainerassignment.avg_weight_g` | numeric | Prefer status-implied average weight (`CurrentBiomassKg / CurrentCount * 1000`) at higher internal precision before model rounding; fallback to `biomass_kg / population_count * 1000`; null when count is 0 | Avoids biomass drift when count authority shifts from conserved to status-derived values. |
| Derived | `batch_batchcontainerassignment.is_active` | boolean | See rules below | Ensures only one active assignment per container. |
| Derived | `batch_batchcontainerassignment.departure_date` | date | See rules below | Nullable. |
| Derived | `batch_batchcontainerassignment.notes` | text | `FishTalk PopulationID={population_id}` | Debug trace. |

**ExternalIdMap metadata for population assignments (code‑verified, 2026‑02‑06):**
- `component_key` - component replay identity
- `container_id` - source FishTalk container GUID
- `baseline_population_count` - pre-removal baseline used by mortality/culling/escape replay synchronization

**Status snapshot selection (code‑verified):**
- If `member.end_time` is **None** and a latest status time exists → snapshot **at latest status time**.
- Otherwise → snapshot **near member.start_time**.
- In CSV mode, if the nearest snapshot has **zero count and biomass**, the loader attempts the **first non‑zero snapshot after** the target time. In SQL mode, the loader uses the nearest snapshot (no non‑zero filtering).
- When multiple snapshots exist at the **same timestamp**, selection is deterministic in both CSV and SQL paths: prefer non-zero over zero, then higher `CurrentCount`, then higher `CurrentBiomassKg`.
- **Usage:** snapshots provide status-derived average weight and biomass context. For `population_count`, completed populations with an exact non-zero snapshot at `member.start_time` use that snapshot as authoritative; open populations use latest status counts; additional status overlays still apply for zero-conserved rows, outside-component transfer-mixing rows, and bridge-calibration overlays (long superseded companions + blank-token external-mixing segments).

**Conservation-based count flow (code‑verified, 2026‑02‑02):**
1. **Seed** populations with `Ext_Inputs_v2.InputCount` when present.
2. **Propagate** via `SubTransfers.ShareCountFwd` (`SourcePopBefore → SourcePopAfter` and `DestPopBefore → DestPopAfter`).
3. **Status-authority overlays:**
   - completed populations with exact start-time status resolved by duplicate-timestamp tie-break; if resolved snapshot is non-zero -> set `count = status_count`,
   - open populations (`member.end_time IS NULL`) with latest status evidence -> set `count = latest_status_count`,
   - otherwise fallback to status snapshot count when:
     - no conserved count exists, or
     - conserved count is **0** but snapshot is non-zero, or
     - the population has SubTransfers edges to outside-component populations and `status_count >= conserved_count * external_mixing_status_multiplier` (default multiplier `10.0`), or
     - known removals for that population (`mortality + culling + escapes`) exceed conserved count and status count is higher (prevents impossible baseline < removals).
4. **Same‑stage suppression/classification:** if a SubTransfer moves fish **within the same lifecycle stage** (source and dest stages match), classify superseded rows as:
   - **short bridge (<= `same_stage_supersede_max_hours`) without operational evidence:** zero assignment count to avoid double-counting bridge segments.
   - **long superseded companion** or **operationally material superseded row:** prefer status-at-start count (with known-removals floor) when available.
   - **external-mixing blank-token row (non-superseded):** prefer status-at-start to preserve lane-level parity.
   - **culling-only residual tail (same-container, same-stage, fully culled, no non-culling activity):** fold the tail back into the predecessor assignment and attach culling there instead of preserving a separate AquaMind assignment fragment.
5. **Count/biomass consistency:** when status average weight is available, assignment biomass is recomputed from the final chosen count to prevent impossible implied weights (status average weight is kept at higher internal precision before field rounding).

**Diagnostics:** see `analysis_reports/2026-02-02/conservation_counts_diagnostics_2026-02-02.md`.

**Regression policy guard (assignment counts):**
- For non-zero **completed** assignment rows, expected count authority is exact status count at `member.start_time` after duplicate-timestamp tie-break resolution.
- For non-zero **open** assignment rows, expected count authority is latest status count.
- Component-root seed rows can legitimately diverge from status-count checks when the source population starts before first non-zero status snapshot materializes.

**Active assignment rules (code‑verified):**
1. If the batch itself is not active → all assignments are inactive.
2. Else, if `latest_status_time` is present → active only when:
   - latest snapshot for that population is non-zero, and
   - `latest_status_time >= (global_max_status_time - assignment_active_window_days)`.
3. Else → active if `member.end_time` is None.
4. Additional guards:
   - If assignment lifecycle stage ≠ batch lifecycle stage → force inactive **unless** the holder has recent non-zero evidence inside the lifecycle frontier recency window (`latest_status_time >= component_status_time - lifecycle_frontier_window_hours`).
   - Only the **latest non-zero** population per container can be active; holder tie-break order is: latest status timestamp → open membership (`end_time IS NULL`) → latest status count → latest membership start timestamp.
   - Latest-holder consistency gate (profile default) removes container active-candidates when a later outside-component non-zero holder exists in source status snapshots.
   - Assignment must belong to computed `active_population_by_container`; otherwise force inactive.
   - Assignments with `population_count <= 0` are forced inactive.

**Departure date rules (code‑verified):**
- If assignment is active → `departure_date = None`.
- Else, if `latest_status_time` exists → `departure_date = latest_status_time.date()`.
- Else, if `member.end_time` exists → `departure_date = member.end_time.date()`.
- Else → `departure_date = None`.

### 3.3 Lifecycle Stage Mapping (ProductionStages / PopulationStages)

**Source tables in extract:**
- `production_stages.csv` (StageID → StageName)
- `population_stages.csv` (PopulationID → StageID → StartTime)
- `operation_stage_changes.csv` (PopulationID → StageID → StageStartTime, OperationTime)

**Observed StageName values (current extract):**
`Egg`, `Green egg`, `Eye-egg`, `Alevin`, `Sac Fry/Alevin`, `Fry`, `Parr`, `Smolt`, `Large Smolt`, `Ongrowing`, `Grower`, `Grilse`, `Broodstock`

**Current mapping logic (code‑verified):**

Order below uses the migration script’s stage order (`STAGE_ORDER = Egg&Alevin → Fry → Parr → Smolt → Post‑Smolt → Adult`). Broodstock is **not** part of that order in code. There may be instances, especially in smaller stations, where a stage is not present, so this should not be treated as universal for all historical periods.

| Order | FishTalk StageName token (case‑insensitive) | AquaMind target | Evidence |
|---:|---|---|---|
| 1 | EGG, ALEVIN, SAC | Egg&Alevin | `fishtalk_stage_to_aquamind` in `pilot_migrate_component.py` |
| 2 | FRY | Fry | same |
| 3 | PARR | Parr | same |
| 4 | SMOLT | Smolt | same |
| 5 | SMOLT + (POST or LARGE) | Post‑Smolt | same (only “Large Smolt” matches in current extract) |
| 6 | ONGROW, GROWER, GRILSE | Adult | same |
| — | BROODSTOCK | **No explicit mapping** → returns `None` | verified in code |
| — | Unrecognized | `None` | code default return |

**Coverage notes (extract‑verified):**
- `production_stages.csv` has **13 unique stage names** and **no “Post‑Smolt” literal** string.
- “Large Smolt” is the only stage name that maps to **Post‑Smolt** under current logic.
- `population_stages.csv` covers **102,473 of 355,024** populations (stage data is incomplete in the extract).

**Known accuracy issue (reported by you, not yet resolved in code):**
- You report that **Post‑Smolt is the final freshwater stage after Smolt**. Current mapping assigns “Post‑Smolt” to a separate lifecycle stage but only when “POST”/“LARGE” is present. There is **no “Post‑Smolt” label** in the extract, so this stage is rarely produced by the mapper.

**Hall‑based override (code‑verified, qualified):**
- When a hall mapping exists, it **overrides** the token mapping. Hall labels are taken from `Ext_GroupedOrganisation_v2.ContainerGroup` (these are the same labels shown in the FishTalk GUI; “Høll” = “Hall”).
- **FW22 exception (2026-02-16):** for `FW22 Applecross`, explicit member stage tokens are preferred when present (hall map still applies when tokens are blank).
- **S08 exception (2026-02-23):** hall mappings are enforced before token-stage fallback for mapped halls (`Kleking`, `Startfóðring`, `T‑Høll`); `R-Høll` uses a deterministic dual-stage rule where the first **material** holder in a container (>= 6h lifespan, or open member) resolves to `Parr` and subsequent in-hall redistributions resolve to `Smolt`. Pre-initial micro bridge fragments are retained as zero-count bridge rows for auditability.
- `Ext_GroupedOrganisation_v2.ProdStage` is treated as **context only** (not lifecycle truth). In the 2026-02-10 station-focused Benchmark replay, populations spanning `Parr/Smolt/Post‑Smolt` lifecycle assignments still classify as `ProdStage=Hatchery` in grouped-organisation output; lifecycle mapping therefore remains stage/hall-driven.
- If explicit hall mapping is missing, migration can apply a **component-local hall fallback** only when token-mapped rows for the same `(site, container_group)` unanimously resolve to one lifecycle stage.
- **S24 Strond (qualified 2026‑01‑30):**
  - A Høll → Egg&Alevin
  - B Høll → Fry
  - C Høll, D Høll → Parr
  - E Høll, F Høll → Smolt
  - G Høll, H Høll, I Høll, J Høll → Post‑Smolt
- **S03 Norðtoftir (qualified mapping, 2026‑02‑02):**
  - 5 M Høll → Fry
  - 11 Høll A, 11 Høll B → Smolt
  - 18 Høll A, 18 Høll B → Post‑Smolt
  - 800 Høll, 900 Høll → Parr
- **S08 Gjógv (qualified mapping, updated 2026‑02‑23):**
  - Kleking → Egg&Alevin
  - Startfóðring → Fry
  - R-Høll → Parr and Smolt. First material holder in a container: Parr. Subsequent in-hall redistributions: Smolt. Micro pre-initial bridge fragments remain zero-count.
  - T‑Høll → Post‑Smolt
- **S16 Glyvradalur (qualified mapping, 2026‑02‑02; updated 2026‑02‑03):**
  - A Høll → Egg&Alevin
  - B Høll → Fry
  - C Høll → Parr
  - D Høll → Smolt
  - E1 Høll, E2 Høll → Post‑Smolt
  - Klekihøll → Egg&Alevin
  - Startfóðringshøll → Fry
- **S21 Viðareiði (qualified mapping, updated 2026‑02‑06):**
  - 5M → Fry
  - A, BA, BB → Parr
  - C, D → Smolt
  - E, F → Post‑Smolt
  - Rogn → Egg&Alevin
- **FW22 Applecross (qualified mapping, Scotland, 2026‑02‑02):**
  - A1, A2 → Egg&Alevin
  - B1, B2 → Fry
  - C1, C2 → Parr
  - D1, D2 → Smolt
  - E1, E2 → Post‑Smolt
- **FW13 Geocrab (qualified mapping, Scotland, 2026‑02‑02):**
  - Hatchery → Egg&Alevin
  - Fry → Fry
  - Parr → Parr
  - Smolt → Smolt
  - Grading Tank → Post-Smolt. This is a special case. the Grading Tank is not a hall, but a standalone tank, not inside a hall.   
**Scotland hall inventory (FishTalk GUI export, 2026‑02‑02; stage not explicitly provided):**
- **FW13 Geocrab:** GradingTank, Hatchery, Parr, Smolt
- **FW21 Couldoran:** A Row, B Row, C Row, D Row, E Row, F Row, Hatchery, RAS
- **FW23 KinlochMoidart:** Archive, Hatchery, Parr, Smolt (RAS 1), Smolt (RAS 2)

Note: several Scotland hall labels are **self‑describing** (e.g., “Parr”, “Smolt”), but **no explicit stage column** was provided in the report. These are **inventory only** until a rule is approved.

**Known gaps / not yet mapped (explicitly left unmapped to avoid guesswork):**
- **S08 Gjógv:** Úti (no explicit static hall mapping; currently token/component-local fallback driven).
- **S16 Glyvradalur:** Gamalt, Uppstilling broytt ‑ A Høll (no stage provided).
- **S21 Viðareiði:** C gamla, CD, Gamalt (no stage provided).
- **S04 Húsar:** 801–812 (not present in `ContainerGroup` in current extract; only Gamalt appears).
- **S10 Svínoy:** station listed, no hall mapping provided.
- **Scotland sites:** FW13 Geocrab, FW21 Couldoran, FW23 KinlochMoidart (hall inventory only; stage mapping not provided).

**Remediation options (qualified):**
1. Collect explicit hall → stage mappings for the “gap” halls above (preferred).
2. If approved, add a **“self‑describing hall” rule** (e.g., ContainerGroup == Fry/Parr/Smolt) with explicit sign‑off, and explicitly decide how to treat labels like “Hatchery”, “RAS”, and “Smolt/post Smolt”.
3. Extend hall inference to **StandName/OfficialID** only if a qualified mapping for those labels is provided (not currently in use).

**Progress note (2026‑02‑02):**
- InputProjectID‑based membership + S21 hall mapping resolved stage‑missing failures for **Bakkafrost S‑21 sep24** and enabled full‑lifecycle migration (transfers + feeding + mortality populated).
- Full hall inventory captured for Faroe + Scotland stations; only the Faroe list and FW22 Applecross have **explicit stage** mappings so far.

**Progress note (2026‑02‑11, targeted fix check):**
- `BF mars 2025|2|2025` (`S08 Gjógv`) previously failed at stage resolution (`R‑Høll` unmapped + missing stage token rows). After adding component-local unanimous hall fallback in `pilot_migrate_component.py`, migration completed and semantic gates passed in station-guarded replay (`analysis_reports/2026-02-11/semantic_validation_bf_mars_2025_2026-02-11_fixcheck.md`).

**Domain note (qualitative):**
- Broodstock is a separate breeding division supplying eggs (e.g., Bakkafrost inputs; see 3.0.0.1). Treating Broodstock as a **pre‑Egg&Alevin** stage would require an explicit mapping change plus a controlled re‑run.
- Some stations use a deeper physical hierarchy for egg/alevin handling (Hall → Skáp → Incubation Tray). AquaMind now supports this with container hierarchy (`parent_container_id`, `hierarchy_role`) and migration can map `StandName/StandID` to structural rack nodes.

**Guidance (qualified):**
- Migration is strict by default (explicit hall mapping, unanimous hall fallback, token mapping), but now includes a constrained sparse-metadata fallback to batch lifecycle stage with telemetry to prevent full-cohort aborts on a few unresolved rows.
- Any correction to the Post‑Smolt rule requires a code change and a controlled re‑run.
- Do **not** use `Ext_GroupedOrganisation_v2.ProdStage` for lifecycle stage—this field is an organizational bucket, not a biological stage (observed to be coarse in prior analyses).

### 3.4 Transfer Workflow Type Mapping (FishTalk: SubTransfers/PublicTransfers)

**Cross‑reference (context):**
- PRD batch workflow section: `docs/prd.md` → 3.1.2 / 3.1.2.1
- Data model tables: `docs/database/data_model.md` → `batch_batchtransferworkflow`, `batch_transferaction`, `batch_batchcontainerassignment`

**Data Source Selection (code‑verified, updated 2026‑02‑27):**
- **SubTransfers** when `--use-subtransfers` is supplied (CSV or SQL).
  - **Default scope (`source-in-scope`)**: include operations initiated by in-scope `SourcePopBefore`, then expand in-operation `SourcePopBefore -> SourcePopAfter` chains to effective root-source `SourcePop -> DestPop` edges.
  - **Restricted scope (`internal-only`)**: keep only direct edges where both source and destination populations are component members.
- **PublicTransfers** only when **not** using `--use-subtransfers` **and** running with SQL (no CSV path).
- `transfer_edges.csv` / `transfer_operations.csv` are **not used** by `pilot_migrate_component_transfers.py`.

**Pre‑conditions (code‑verified, updated 2026‑02‑27):**
- Requires source assignment `ExternalIdMap` rows (`source_model = "Populations"`) created by `pilot_migrate_component.py`.
- Destination assignment resolution order:
  1. component-scoped destination assignment map (`SubTransferDestinationPopulationAssignment`),
  2. generic population assignment map (`Populations`),
  3. destination container bootstrap (create/map missing container + hall from `grouped_organisation.csv` / `containers.csv`).
- `workflow_grouping=stage-bucket` relies on CSV hall/stage mapping; SQL mode falls back to `workflow_grouping=operation`.

**Rerun behavior (code-verified, updated 2026-03-11):**
- Before rebuilding transfer workflows/actions for a batch, transfer replay prunes existing FishTalk-mapped transfer workflows from both `TransferStageWorkflowBucket` and `TransferOperation` source models, plus their `PublicTransferEdge` action maps.
- This prune step is required for idempotent transfer correction: reruns must not leave stale same-operation relay actions from earlier scope logic in place beside the rebuilt `source-in-scope` edge set.

**Workflow grouping & typing logic (code‑verified, updated 2026‑02‑27):**
- `workflow_grouping=stage-bucket` (default) groups edges by `(component, station_site, workflow_type, source_stage, dest_stage)` using deterministic `TransferStageWorkflowBucket` identifiers.
- `workflow_grouping=operation` groups by `OperationID`.
- `workflow_type`:
  - `LIFECYCLE_TRANSITION` when resolved source and destination stages differ,
  - `CONTAINER_REDISTRIBUTION` otherwise.
- Stage resolution prefers hall/station mapping (stage-bucket mode), with assignment/token fallbacks where applicable.

**TransferAction creation (code‑verified, updated 2026‑02‑27):**
- One `TransferAction` per scoped edge (`SourcePop -> DestPop`) inside the selected workflow group.
- For each `(OperationID, SourcePop)` group:
  - load one source snapshot at operation time (`CurrentCount`, `CurrentBiomassKg`),
  - allocate counts across all destination edges **from full source total** (not sequential remainder):
    - ratio uses `ShareCountForward` (fallback `ShareBiomassForward`),
    - ratios are normalized when sum exceeds `1.0`,
    - target transfer total is `round(source_count * min(1.0, ratio_sum))`,
    - largest-remainder rounding assigns per-edge integers that sum exactly to target total.
  - allocate biomass from source average kg/fish based on allocated counts; apply final rounding delta to the largest edge to preserve total biomass consistency.
- Edges that resolve to `transferred_count <= 0` are skipped (no zero-count action persisted).
- Idempotency uses `ExternalIdMap` with `source_model = "PublicTransferEdge"` and `source_identifier = "{OperationID}:{SourcePop}:{DestPop}"` (both SubTransfers and PublicTransfers paths).

**Post-action reconciliation guards (code‑verified, updated 2026‑02‑27):**
- Destination assignments touched by transfer edges are synchronized from completed action aggregates (`population_count`, `biomass_kg`, `assignment_date`, `is_active=True`, `departure_date=None`).
- Departed source assignments can be stage-backfilled to workflow source stage when stage-bucket classification proves historical stage.
- Departed source assignments with zero count are count-backfilled from completed action `source_population_before` maxima; biomass is inferred from transfer biomass or average weight when needed.

**Transfer reconciliation invariants (recommended non-regression checks):**
1. Per `(workflow, source_assignment)`: `sum(transferred_count)` equals action-side source authority (`max(source_population_before)` for that source assignment in the workflow).  
   - Do **not** require equality to assignment `population_count` when removals (mortality/culling/escapes) occurred before transfer time.
2. Per active destination assignment touched by workflows: assignment `population_count` equals `sum(transferred_count by dest_assignment)`.
3. Per workflow: total transferred by sources equals total transferred by destinations.

**Transfer mix-lineage backfill (code-verified, updated 2026-02-28):**
- Script: `scripts/migration/tools/pilot_backfill_transfer_mix_events.py`
- Input authority: completed `TransferAction` rows with destination assignments.
- Qualification rule: destination container/date must contain cross-batch co-location (`dest_assignment.container`, transfer date, positive overlapping assignment count from a different batch).
- Writes:
  - `batch_batchmixevent` (`workflow_action`-anchored),
  - `batch_batchmixeventcomponent` (population/biomass percentage split),
  - `batch_batchcomposition` fallback for mixed batch.
- Side effects:
  - sets `TransferAction.allow_mixed=True` for qualified rows,
  - rewires action destination assignment to mixed assignment (`MIX-FTA-{action_id}` batch) unless `--skip-assignment-rewrite` is used,
  - deactivates contributing pre-mix assignments in destination container history.
- Operation mode:
  - order-independent and idempotent at action scope,
  - supports `--dry-run` for qualification-only coverage checks.

**Synthetic lifecycle transitions (code‑verified, updated 2026‑02‑09):**
- Assignment-derived synthetic stage transitions are now **optional** and are skipped when `--skip-synthetic-stage-transitions` is used.
- `pilot_migrate_input_batch.py` now defaults to skip synthetic stage transitions; legacy behavior is available with `--include-synthetic-stage-transitions`.
- When synthetic transitions are enabled, they are built from assignment lifecycle stages (not `OperationProductionStageChange`) and tracked as `PopulationStageTransition` / `PopulationStageTransitionAction`.
- Rationale: synthetic assignment-derived transitions produced many zero-count lifecycle actions in migrated batches due to short-lived intermediate population segments; edge-backed transfer actions (`PublicTransferEdge`) are the canonical transfer-equivalent replay.

**SubTransfers Fields (CSV extract):**
| Field | Description |
|-------|-------------|
| SourcePopBefore | Population ID before transfer (source) |
| SourcePopAfter | Population ID after transfer (remnant in source container) |
| DestPopAfter | Population ID after transfer (fish moved to new location) |
| ShareCountFwd | Fraction of count transferred (0–1) |
| ShareBiomFwd | Fraction of biomass transferred (0–1) |

### 3.5 Batch Creation Workflow Mapping (FishTalk: Stitched Components)

FishTalk does not capture a formal “creation workflow.” For each stitched component migrated into a batch, synthesize a creation workflow that represents initial egg placement into the first assignments.

| Derived Source | AquaMind Target | Data Type | Transformation | Notes |
|----------------|----------------|-----------|----------------|--------|
| Component key | batch_creationworkflow.workflow_number | varchar(50) | `CRT-{batch_number}` trimmed to 50 chars; append `-{component_prefix}` if needed | Deterministic per batch |
| Component key | batch_creationworkflow.external_supplier_batch_number | varchar(100) | Direct | Store component key for traceability |
| Synthetic | batch_creationworkflow.egg_source_type | varchar(20) | `EXTERNAL` | Placeholder for FishTalk legacy eggs |
| Synthetic supplier | batch_creationworkflow.external_supplier_id | bigint | Ensure `EggSupplier` named `FishTalk Legacy Supplier` exists | Create if missing |
| Initial assignments | batch_creationworkflow.total_eggs_planned | integer | Sum of resolved egg counts for initial set | `Ext_Inputs_v2.InputCount` preferred per population; fallback to assignment `population_count`. |
| Initial assignments | batch_creationworkflow.total_eggs_received | integer | Same as planned | No DOA data available |
| Initial assignments | batch_creationworkflow.total_actions | integer | Count of initial assignments | One action per assignment |
| Initial assignments | batch_creationworkflow.actions_completed | integer | Same as total_actions | Set to completed on migration |
| Initial assignments | batch_creationworkflow.planned_start_date | date | Earliest initial-member start date | Also used for actual_start_date |
| Initial assignments | batch_creationworkflow.planned_completion_date | date | Latest initial-member start date | Also used for actual_completion_date |
| Synthetic | batch_creationworkflow.status | varchar(20) | `COMPLETED` when actions exist, else `PLANNED` | No in-progress state from source |

**Initial assignment selection rules**
- Prefer populations whose `start_time.date()` falls within `creation_window_days` from batch start (default 60) and whose stage maps to the batch’s initial lifecycle stage.
- If none match that window+stage rule, include populations starting on batch start date with matching initial lifecycle stage.
- If none match stage, include all populations starting on the batch start date.
- If still empty, fall back to the earliest population in the component.

**Creation actions**
- Create one `CreationAction` per initial assignment:
  - `dest_assignment` = assignment
  - `egg_count_planned` / `egg_count_actual` = resolved egg count (`InputCount` if available, else assignment `population_count`)
  - `expected_delivery_date` / `actual_delivery_date` = assignment `assignment_date`
  - `status` = `COMPLETED`
- Record idempotency via `ExternalIdMap`:
  - `source_model = PopulationComponentCreationWorkflow` (component key → creation workflow)
  - `source_model = PopulationCreationAction` (population id → creation action)

### 3.6 Input‑Based Stitching Report (Batch Selection & Validation)

**Purpose:** Generate `input_batches.csv` and `input_population_members.csv` for input‑based migration (`pilot_migrate_input_batch.py`). This report runs against the **FishTalk SQL source**, not CSV extracts.

**Script (code‑verified):**
- `scripts/migration/tools/input_based_stitching_report.py`

**Outputs (code‑verified):**
- `input_batches.csv` — one row per batch key (`InputName|InputNumber|YearClass`)
- `input_population_members.csv` — population‑level membership with container/time/stage metadata
- `input_records.csv` — raw Ext_Inputs_v2 rows grouped by batch key

**Validation logic (code‑verified):**
- `is_valid` is **True** if:
  - single geography (excluding `Unknown`), **and**
  - `span_days <= max_span_days` (default 900)
- Additional checks **do not invalidate** the batch but are recorded in `validation_issues`:
  - `total_fish < min_fish` (default 100,000)
  - stage progression out of order

**Filters (code‑verified CLI flags):**
- `--since YYYY-MM-DD` → filters Ext_Inputs_v2 by `StartTime`
- `--min-populations` (default 2)
- `--min-fish` (default 100,000)
- `--max-span-days` (default 900)
- `--valid-only` → keep only `is_valid=True`
- `--require-sea` → require sea stages (`Adult`/`Post‑Smolt`)
- `--active-only` → require `latest_activity.year >= 2024`

**Migration preflight (code‑verified, updated 2026‑02‑17):**
- `pilot_migrate_input_batch.py` cross-checks station evidence from:
  - `input_projects.csv` site,
  - `ext_inputs.csv` + `populations.csv` + `grouped_organisation.csv`,
  - selected member population sites.
- Inter-station FW->FW transfer can produce legitimate member-site divergence for a cohort.
- Preflight mismatches fail by default unless explicitly overridden for transfer-confirmed cohorts.
- `--expected-site "<site>"` remains the station anchor; pair with `--allow-station-mismatch` when replaying known mixed-site transfer cohorts.

**Scope-file cohort replay mode (code-verified, updated 2026-02-28):**
- `pilot_migrate_input_batch.py` accepts `--scope-file <csv>` as a batch-runner mode.
- Scope resolution rules:
  1. if scope rows include `batch_key`-compatible columns, those keys are used directly;
  2. else if scope rows include population-id columns, population IDs are mapped to `batch_key` via stitched `input_population_members.csv`.
- Resolution behavior is deterministic (dedupe + preserve input order) and emits scope stats (`scope_rows`, rows with/without `batch_key`, resolved/unresolved population rows).
- If both `--batch-key` and `--scope-file` are supplied, single-batch mode remains authoritative (scope file is ignored with warning).
- Scope child invocations now forward `--expand-subtransfer-descendants`, `--transfer-edge-scope`, and `--dry-run` so scope replay behavior matches single-batch replay behavior.
- Recommended for transfer-rich cohorts: `--expand-subtransfer-descendants --transfer-edge-scope source-in-scope`.

## 4. Feed & Inventory Mapping

### 4.0 Source of Truth (FishTalk)

- **Purchases:** FishTalk does not have a `FeedPurchase` table. Use `FeedReceptions` (header) and
  `FeedReceptionBatches` (line items) as the canonical purchase source.
- **Consumption authority:** Use `Feeding` joined through `Action` (+ `Operations` timestamp) as the authoritative evidence for what feed was consumed by scoped cohort populations.
- **Feed-batch lineage:** Use `FeedTransfer` to expand upstream source feed batches (destination -> source recursion) so transfer-derived stock is included.
- **Stock/infrastructure hydration:** Use `FeedBatch` -> `FeedStore` -> `FeedStoreUnitAssignment` after feed-batch lineage is resolved; treat container assignment links as infrastructure placement evidence, not as the sole feed-scope authority.
- **Flattened support views:** `Ext_FeedDelivery_v2`, `Ext_FeedStore_v2`, `Ext_FeedStoreAssignment_v2`, `Ext_FeedTypes_v2`, and `Ext_FeedSuppliers_v2` are valid convenience sources once lineage scope is fixed.

### 4.1 Feed Type Mapping (FishTalk: FeedType)

| FishTalk Column (FeedType) | AquaMind Target | Data Type | Transformation | Notes |
|----------------------------|-----------------|-----------|----------------|--------|
| FeedID | inventory_feed.id | bigint | Identity map | Confirmed column |
| FeedName | inventory_feed.name | varchar(100) | Direct | |
| Brand | inventory_feed.brand | varchar(100) | Direct | |
| Size | inventory_feed.pellet_size_mm | decimal(5,2) | Direct | |
| SizeCategory | inventory_feed.size_category | varchar(20) | Map to choices | |
| Protein | inventory_feed.protein_percentage | decimal(5,2) | Direct | |
| Fat | inventory_feed.fat_percentage | decimal(5,2) | Direct | |
| Carbs | inventory_feed.carbohydrate_percentage | decimal(5,2) | Direct | |
| Description | inventory_feed.description | text | Direct | |
| Active | inventory_feed.is_active | boolean | Direct | |

### 4.2 Feeding Event Mapping (FishTalk: Feeding, HWFeeding)

FishTalk `dbo.Feeding` is **ActionID-based** (no PopulationID or ContainerID columns).

| FishTalk Source | AquaMind Target | Data Type | Transformation | Notes |
|-----------------|-----------------|-----------|----------------|--------|
| Feeding.ActionID | ExternalIdMap (Feeding) | uuid | Store for idempotency | Key for replay |
| Action.PopulationID | inventory_feedingevent.batch_assignment_id | bigint | ExternalIdMap (Populations) → BatchContainerAssignment | Container inferred from assignment |
| COALESCE(Operations.StartTime, Feeding.OperationStartTime) | feeding_date / feeding_time | date / time | Split datetime | |
| Feeding.FeedAmount | amount_kg | decimal(10,4) | **grams → kg** | Confirmed by pilot |
| FeedBatch + FeedTypes | feed_id | bigint | get_or_create Feed | Use feed name + batch number |
| PublicStatusValues before/after | batch_biomass_kg | decimal(10,2) | Prefer non‑zero snapshot | Avoid zero biomass overflow |
| Feeding.ImportedFrom or HWFeeding | method | varchar(20) | AUTO vs MANUAL | Normalize |
| Operations.Comment | notes | text | Include ActionID + PopulationID | Traceability |

### 4.4 Feed Purchase Mapping (FishTalk: FeedReceptions + FeedReceptionBatches)

| FishTalk Source | AquaMind Target | Data Type | Transformation | Notes |
|-----------------|-----------------|-----------|----------------|--------|
| FeedReceptionBatches.FeedReceptionID | inventory_feedpurchase.id | bigint | Generate new | Source identifier in ExternalIdMap |
| FeedReceptionBatches.FeedBatchID | inventory_feedpurchase.batch_number | varchar | Prefer SuppliersBatchNumber/ReceiptNumber | Fallback to FeedBatch.BatchNumber |
| FeedReceptions.ReceptionTime | inventory_feedpurchase.purchase_date | date | Date part | |
| FeedReceptionBatches.ReceptionAmount | inventory_feedpurchase.quantity_kg | decimal | **grams → kg** | Confirm units per source system |
| FeedReceptionBatches.PricePerKg | inventory_feedpurchase.cost_per_kg | decimal | Direct | |
| FeedReceptions.SupplierID | inventory_feedpurchase.supplier | varchar | Store SupplierID string | Replace with Supplier name if table found |
| FeedReceptionBatches.OutOfDate | inventory_feedpurchase.expiry_date | date | Date part | Nullable |
| FeedReceptionBatches.SuppliersBatchNumber | inventory_feedpurchase.batch_number | varchar | Direct | Preferred over ReceiptNumber |
| FeedReceptionBatches.ReceiptNumber | inventory_feedpurchase.batch_number | varchar | Direct | Fallback |
| FeedBatch.FeedTypeID / FeedTypes.Name | inventory_feedpurchase.feed_id | bigint | FK lookup/create | Use FeedTypes.Name in feed name |

**Extraction rules**
- For broad residual-data scope replay, use lineage-first extraction:
  1. Start from scoped cohort populations.
  2. Expand descendant populations via `SubTransfers` edges (`SourcePopBefore -> SourcePopAfter`, `SourcePopBefore -> DestPopAfter`) up to migration cutoff.
  3. Pull `Feeding` for expanded populations (`Action.PopulationID`).
  4. Build included `FeedBatch` set from feeding rows, then recursively add upstream `SourceFeedBatchID` via `FeedTransfer` where destination is already in scope.
  5. Pull purchases from `FeedReceptionBatches` + `FeedReceptions` for included feed batches.
  6. Pull infra/dependencies from included feed batches (`FeedStore`, `FeedStoreUnitAssignment`, feed types, suppliers, optional `Ext_*` mirrors).
- Component-window container assignment filtering is still useful for narrow QA checks, but it is not sufficient as the only purchase/stock scope rule for transfer-rich cohorts.

### 4.5 Feed Container Stock Mapping (FishTalk: FeedStore + FeedStoreUnitAssignment + FeedBatch)

| FishTalk Source | AquaMind Target | Data Type | Transformation | Notes |
|-----------------|-----------------|-----------|----------------|--------|
| FeedStore.FeedStoreID | infrastructure_feedcontainer.id | bigint | Generate new | Source identifier in ExternalIdMap |
| FeedStore.Name | infrastructure_feedcontainer.name | varchar | Direct | |
| FeedStore.Capacity | infrastructure_feedcontainer.capacity_kg | decimal | Direct | Assume kg | 
| FeedStoreUnitAssignment.ContainerID | infrastructure_feedcontainer.hall/area | FK | Map to container's hall/area | Use container mapping |
| FeedReceptionBatches.ReceptionAmount | inventory_feedcontainerstock.quantity_kg | decimal | **grams → kg** | | 
| FeedReceptions.ReceptionTime | inventory_feedcontainerstock.entry_date | datetime | UTC | |
| FeedReceptionBatches → FeedPurchase | inventory_feedcontainerstock.feed_purchase_id | FK | From 4.4 | |

Notes:
- Feed-store-to-container assignment coverage is sparse relative to feed consumption lineage; do not use assignment presence as a hard precondition for including feed purchases.
- `FeedTransfer` is a core stock-lineage source for scoped replay, not an optional post-step. Some consumed feed batches are transfer-derived and may not have direct reception lines.
- For scoped residual extraction, keep only feed/infrastructure rows connected to included cohort lineage (expanded populations + derived feed-batch lineage) to avoid orphan import noise.

### 4.6 Scoped Residual Feed/Infra Extraction Contract (Scope-60)

Use this contract when extracting feed + dependent infrastructure for the hall-stage mapped freshwater `<30m` scope (all 60 batch keys):

1. Resolve scope batch keys from hall-stage mapped stations (`S24`, `S03`, `S08`, `S16`, `S21`, `FW22`, `FW13`) with trusted `FW13 Geocrab` hall-stage mapping.
2. Seed populations from those batch keys, then expand lineage through `SubTransfers` (`SourcePopBefore -> SourcePopAfter` and `SourcePopBefore -> DestPopAfter`) up to migration cutoff.
3. Extract `Feeding` rows for expanded populations and derive the consumed `FeedBatch` set.
4. Expand feed-batch lineage upstream through `FeedTransfer` destination->source recursion.
5. Hydrate dependent entities from included feed batches only:
   - `FeedReceptionBatches` + `FeedReceptions` (+ optional `Ext_FeedDelivery_v2`)
   - `FeedStore` + `FeedStoreUnitAssignment` (+ optional `Ext_FeedStoreAssignment_v2`)
   - `FeedTypes` / `Ext_FeedTypes_v2` + supplier lookup (`Ext_FeedSuppliers_v2`)
6. Exclusion rule: do not include rows disconnected from the scoped population lineage and derived feed-batch lineage.

### 4.7 FCR Calculation Mapping

| FishTalk Source | AquaMind Target | Data Type | Transformation | Notes |
|-----------------|-----------------|-----------|----------------|--------|
| FCR.ProjectID | inventory_batchfeedingsummary.batch_id | bigint | FK lookup | |
| FCR.PeriodStart | inventory_batchfeedingsummary.period_start | date | Direct | |
| FCR.PeriodEnd | inventory_batchfeedingsummary.period_end | date | Direct | |
| FCR.TotalFeed | inventory_batchfeedingsummary.total_feed_kg | decimal(12,3) | Direct | |
| FCR.StartBiomass | inventory_batchfeedingsummary.total_starting_biomass_kg | decimal(12,2) | Direct | |
| FCR.EndBiomass | inventory_batchfeedingsummary.total_ending_biomass_kg | decimal(12,2) | Direct | |
| FCR.Growth | inventory_batchfeedingsummary.total_biomass_gain_kg | decimal(10,2) | Calculate | |
| FCR.FCRValue | inventory_batchfeedingsummary.fcr | decimal(5,3) | Direct or calc | |

## 5. Health & Medical Mapping

> **Master Data Gaps:**
> - Align FishTalk `MortalityCause` codes with `health_mortalityreason` records before migration.
> - Health parameter labels/scores must match `health_healthparameter` + `health_parameterscoredefinition`; seed any missing entries.
> - Treatment types/vaccine categories require lookup harmonisation (see Sections 5.3 and 5.4).

### 5.1 Health Journal Entry Mapping (FishTalk: UserSample)

FishTalk does not expose a clean `HealthLog` table; health observations are inferred from **UserSample** actions.
We create **one JournalEntry per ActionID**.

| FishTalk Source | AquaMind Target | Data Type | Transformation | Notes |
|-----------------|-----------------|-----------|----------------|--------|
| UserSample.ActionID | ExternalIdMap (UserSampleAction) | uuid | Store for idempotency | One entry per ActionID |
| Action.PopulationID | health_journalentry.batch_id | bigint | FK lookup | Required |
| Action.PopulationID | health_journalentry.container_id | bigint | FK lookup | Optional (via assignment) |
| Operations.StartTime | health_journalentry.entry_date | timestamptz | UTC conversion | |
| UserSampleTypes + UserSampleType | health_journalentry.category | varchar(20) | Map from sample type | Multi-type → summary text |
| Aggregated samples | health_journalentry.description | text | Summary (n fish, avg weight, key parameters) | |
| UserSample.ActionID | health_journalentry.user_id | integer | User lookup | If available |

### 5.2 Mortality Record Mapping

| FishTalk Source | AquaMind Target | Data Type | Transformation | Notes |
|-----------------|-----------------|-----------|----------------|--------|
| Mortality.MortID | batch_mortalityevent.id | bigint | Identity map | |
| Mortality.ProjectID | batch_mortalityevent.batch_id | bigint | FK lookup | Required |
| Mortality.Date | batch_mortalityevent.event_date | date | Direct | |
| Mortality.Count | batch_mortalityevent.count | integer | Direct | |
| Mortality.Cause | batch_mortalityevent.cause | varchar(100) | Direct or map | |
| Mortality.Description | batch_mortalityevent.description | text | Direct | |

**Replay behavior (code‑verified, 2026‑02‑06):**
- Migration writes removal events into `batch_mortalityevent` (`MortalityEvent`) for source models:
  - `Mortality`, `Culling`, `Escapes`.
- Assignment population counts are synchronized per FishTalk population mapping as:
  - `resolved_count = baseline_population_count - (mortality + culling + escapes totals)`
- This replay path is idempotent across reruns because totals are sourced from mapped event rows.

### 5.3 Treatment Mapping

| FishTalk Source | AquaMind Target | Data Type | Transformation | Notes |
|-----------------|-----------------|-----------|----------------|--------|
| Treatment.TreatmentID | health_treatment.id | bigint | Identity map | |
| Treatment.ProjectID | health_treatment.batch_id | bigint | FK lookup | |
| Treatment.UnitID | health_treatment.container_id | bigint | FK lookup | |
| Treatment.TreatmentDate | health_treatment.treatment_date | timestamptz | UTC conversion | |
| Treatment.Type | health_treatment.treatment_type | varchar(20) | Map to choices | |
| Treatment.Description | health_treatment.description | text | Direct | |
| Treatment.Dosage | health_treatment.dosage | varchar(100) | Direct | |
| Treatment.Duration | health_treatment.duration_days | integer | Direct | |
| Treatment.Withdrawal | health_treatment.withholding_period_days | integer | Direct | |

## 6. Environmental Data Mapping

> **Canonical sensor mapping contract (2026-03-05 corrective):** `SensorID` must be mapped to `environmental_environmentalparameter` using FishTalk sensor catalogs (`Ext_Sensors_v2` → `Ext_SensorTypes_v2` → `Ext_MeasuringUnits_v2`, with fallback to `Sensors`/`SensorTypes`/`MeasuringUnits`). Do **not** bucket unknown sensors into Temp/O2 heuristically when metadata exists.
>
> **Temporary Source Strategy:** AVEVA historian access is currently pending, so sensor object metadata and early readings will be extracted from FishTalk. Treat FishTalk sensor names as canonical for now—they must remain aligned with the eventual AVEVA sensor catalog. When AVEVA access becomes available, reconcile the two sources and record any divergences in `migration_support.ExternalIdMap` so the loaders can pivot to AVEVA without duplicating historical FishTalk records.

### 6.1 Sensor Reading Mapping (FishTalk: Ext_SensorReadings_v2 / Ext_DailySensorReadings_v2) - TimescaleDB

| FishTalk Source | AquaMind Target | Data Type | Transformation | Notes |
|-----------------|-----------------|-----------|----------------|--------|
| Ext_SensorReadings_v2.ReadingTime | environmental_environmentalreading.reading_time | timestamptz | UTC conversion | Time‑series |
| Ext_DailySensorReadings_v2.Date | environmental_environmentalreading.reading_time | timestamptz | Date → UTC midnight | Daily aggregates |
| SensorID | environmental_environmentalreading.sensor_id | bigint | FK lookup/create | Sensor per (ContainerID, SensorID) |
| Reading | environmental_environmentalreading.value | numeric | Direct | |
| ContainerID | environmental_environmentalreading.container_id | bigint | FK lookup | Via container mapping |
| Derived | environmental_environmentalreading.is_manual | boolean | Daily = True, Time‑series = False | Critical for TGC |
| Ext_Sensors_v2.SensorTypeID | migration_support.externalidmap (`source_model=SensorParameter`) | uuid→bigint | Join to sensor type/unit catalogs; map to canonical environmental parameter; persist mapping metadata | Preferred path |
| Ext_SensorTypes_v2.SensorTypeName + Ext_MeasuringUnits_v2.MeasuringUnitText | environmental_environmentalparameter (`name`, `unit`) | varchar | Deterministic type+unit rules (e.g., OxygenSaturation→Oxygen Saturation `%`, Temperature→`°C`) | Avoid metric-unit mixing |
| Derived (`container_id`,`reading_date`) | environmental_environmentalreading.batch / batch_container_assignment | bigint | Resolve assignment window by effective `BatchContainerAssignment` at reading date | Prevent cross-batch container bleed |

### 6.2 Environmental Parameters

| FishTalk Parameter | AquaMind Parameter | Unit | Range Validation |
|--------------------|-------------------|------|------------------|
| Temperature | Temperature | °C | -5 to 40 |
| OxygenSaturation | Oxygen Saturation | % | 0 to 200 |
| Dissolved Oxygen | Dissolved Oxygen | mg/L | 0 to 20 |
| Salinity | Salinity | ppt | 0 to 40 |
| pH | pH | - | 0 to 14 |
| CO2 | CO2 | mg/L | 0 to 100 |
| Nitrite (NO2-N) | Nitrite | mg/L (or source unit) | 0 to 20 |
| Nitrate (NO3-N) | Nitrate | mg/L (or source unit) | 0 to 200 |
| TAN / Ammonia | Ammonia | mg/L or µg/L | 0 to 50 mg/L equivalent |
| Alkalinity | Alkalinity | mg/L (or source unit) | 0 to 500 |
| Unknown SensorTypeName | Parameter named from sensor type | Source unit | No coercion to Temp/O2 |

**Coverage policy (updated):**
- Coverage is **sensor-driven by station/time window**, not hard-coded by site size or stage.
- Smaller FW stations/halls can legitimately have fewer parameter streams.
- Replay logic must stay deterministic and idempotent via `ExternalIdMap` (`source_model=SensorParameter`) and must preserve source units where applicable.

**Oxygen normalization guardrails (2026-03-05):**
- If FishTalk metadata says oxygen `mg/L` but the observed sensor max in-scope is `> 30`, treat that stream as **Oxygen Saturation (%)** (legacy unit-label mismatch guard).
- For `Oxygen Saturation` values in `(200, 2000]`, normalize by `/10` before persistence (e.g., `1003.1 -> 100.31%`), preserving deterministic replay behavior.
- These guards are **value-profile based**, not station-name based, so sparse/small stations remain supported without hard-coded site logic.

### 6.3 Historian Tag Catalog Bridge

To keep AVEVA data ingestion isolated from AquaMind’s core domain we added a three-table bridge:

- `historian_tag` – canonical catalog (15,399 rows) copied directly from `_Tag`. Stores `tag_id`, `tag_name`, key metadata, plus the untouched AVEVA payload in `metadata`.
- `historian_tag_history` – 5,033 snapshots imported from `TagHistory` (FK is nullable to allow entries for tags that have been deleted upstream).
- `historian_tag_link` – manual mapping table that ties a historian tag to `infrastructure_sensor`, `infrastructure_container`, and/or `environmental_environmentalparameter`.

Workflow:
1. `python manage.py load_historian_tags --profile aveva_readonly --using <db>` refreshes the catalog for either `aquamind_db` or `aquamind_db_migr_dev`.
2. The AVEVA team populates `historian_tag_link` via CSV to associate tags with real AquaMind assets.
3. When block files are parsed, the loader uses the link table to write directly into `environmental_environmentalreading` (Timescale hypertable) without duplicating the historian schema.

## 7. User & Access Control Mapping

### 7.1 User Account Mapping

| FishTalk Source | AquaMind Target | Data Type | Transformation | Notes |
|-----------------|-----------------|-----------|----------------|--------|
| User.UserID | auth_user.id | integer | Identity map | |
| User.Username | auth_user.username | varchar(150) | Lowercase, validate | Unique |
| User.Email | auth_user.email | varchar(254) | Validate format | |
| User.FirstName | auth_user.first_name | varchar(150) | Direct | |
| User.LastName | auth_user.last_name | varchar(150) | Direct | |
| User.Active | auth_user.is_active | boolean | Direct | |
| User.Password | - | - | Reset required | Email reset link |
| User.LastLogin | auth_user.last_login | timestamptz | UTC conversion | |
| User.CreatedDate | auth_user.date_joined | timestamptz | UTC conversion | |

### 7.2 User Profile Mapping

| FishTalk Source | AquaMind Target | Data Type | Transformation | Notes |
|-----------------|-----------------|-----------|----------------|--------|
| User.UserID | users_userprofile.user_id | integer | FK to auth_user | One-to-One |
| User.Role | users_userprofile.role | varchar(100) | Map roles | |
| User.Site | users_userprofile.geography_id | bigint | FK lookup | |
| User.Department | users_userprofile.subsidiary | varchar(100) | Map subsidiary | |
| User.Phone | users_userprofile.phone_number | varchar(20) | Format validation | |

### 7.3 Role Mapping

| FishTalk Role | AquaMind Role | Permissions Group | Notes |
|---------------|---------------|-------------------|--------|
| Administrator | Admin | admin_group | Full access |
| Manager | Manager | manager_group | Site management |
| Operator | Operator | operator_group | Daily operations |
| Viewer | Operator | operator_group | Read-only variant |
| Veterinarian | Veterinarian | vet_group | Health access |

## 8. Broodstock Specific Mappings

### 8.1 Broodstock Fish Mapping

| FishTalk Source | AquaMind Target | Data Type | Transformation | Notes |
|-----------------|-----------------|-----------|----------------|--------|
| Broodstock.FishID | broodstock_broodstockfish.id | bigint | Identity map | |
| Broodstock.PitTag | broodstock_broodstockfish.external_id | varchar | Direct | Unique |
| Broodstock.UnitID | broodstock_broodstockfish.container_id | bigint | FK lookup | |
| Broodstock.Sex | broodstock_broodstockfish.traits | JSON | {"sex": value} | |
| Broodstock.Weight | broodstock_broodstockfish.traits | JSON | {"weight": value} | |
| Broodstock.Status | broodstock_broodstockfish.health_status | varchar(20) | Map status | |

### 8.2 Breeding Event Mapping

| FishTalk Source | AquaMind Target | Data Type | Transformation | Notes |
|-----------------|-----------------|-----------|----------------|--------|
| Spawning.SpawnID | broodstock_breedingpair.id | bigint | Identity map | |
| Spawning.MaleID | broodstock_breedingpair.male_fish_id | bigint | FK lookup | |
| Spawning.FemaleID | broodstock_breedingpair.female_fish_id | bigint | FK lookup | |
| Spawning.SpawnDate | broodstock_breedingpair.pairing_date | timestamptz | UTC conversion | |
| Spawning.EggCount | broodstock_breedingpair.progeny_count | integer | Direct | |

## 9. Financial/Harvest Mapping (If Applicable)

### 9.1 Harvest Event Mapping (HarvestResult‑based)

**Canonical source:** `dbo.HarvestResult` (ActionID‑keyed). The legacy `Harvest` table is not used for migration.

| FishTalk Source | AquaMind Target | Data Type | Transformation | Notes |
|-----------------|-----------------|-----------|----------------|--------|
| HarvestResult.ActionID | harvest_harvestevent (ExternalIdMap: `HarvestAction`) | uuid | One HarvestEvent per ActionID | Event date = Operations.StartTime |
| Action.PopulationID | harvest_harvestevent.assignment_id | bigint | Resolve assignment by PopulationID | |
| HarvestResult.Count | harvest_harvestlot.unit_count | integer | Direct | One HarvestLot per ActionID + row index |
| HarvestResult.GrossBiomass | harvest_harvestlot.live_weight_kg | decimal | Direct (kg) | |
| HarvestResult.NetBiomass | harvest_harvestlot.gutted_weight_kg | decimal | Direct (kg) | Optional |
| HarvestResult.QualityID + ConditionID | harvest_productgrade | FK lookup/create | `ProductGrade.code` = `FT-Q{QualityID}-C{ConditionID}` | |

## 10. Data Validation Rules

### 10.1 Mandatory Field Validation
```python
REQUIRED_FIELDS = {
    'batch_batch': ['batch_number', 'species_id', 'lifecycle_stage_id', 'status', 'start_date'],
    'batch_batchcontainerassignment': ['batch_id', 'container_id', 'population_count', 'assignment_date'],
    'infrastructure_container': ['name', 'container_type_id', 'active'],
    'inventory_feedingevent': ['batch_id', 'container_id', 'feed_id', 'feeding_date', 'amount_kg']
}
```

### 10.2 Range Validations
```python
RANGE_VALIDATIONS = {
    'latitude': (-90, 90),
    'longitude': (-180, 180),
    'temperature': (-5, 40),
    'ph': (0, 14),
    'percentage': (0, 100),
    'fcr': (0.5, 3.0)
}
```

### 10.3 Business Rule Validations
- Batch assignment dates must be >= batch start date
- Container capacity must not be exceeded
- FCR values must be positive and typically < 3.0
- Mortality count cannot exceed population
- Feed amount must be positive
- Stage transition sanity: population should not increase across lifecycle stages unless mixed-batch composition exists.
- Bridge-aware stage transition checks use SubTransfer-conserved counts for linked populations (fallback to assignment counts only when conserved count is missing or zero), and only when all stage-entry destinations are linkage-covered for that transition.
- Temporary bridge classification uses short-lived population timing from `ext_populations.csv`, with fallback seeding from stitched `population_members.csv` when relay populations are omitted from `ext_populations.csv`.
- Bridge detection and source collection must consider inbound relays on both `DestPopAfter` and `SourcePopAfter`; some real stage-entry populations are linked only through `SourcePopAfter -> SourcePopBefore` relay chains.
- Full SubTransfer linkage, including temporary bridge hops, is treated as bridge-aware count basis in semantic validation; rows that use only direct predecessor coverage are labeled `entry_window_reason=direct_linkage`, while rows that traverse temporary bridge populations are labeled `entry_window_reason=bridge_aware`.
- If direct linkage coverage is incomplete, semantic validation performs deterministic predecessor-graph backtrace across SubTransfer roles (`DestPopAfter<-SourcePopBefore`, `DestPopAfter<-DestPopBefore`, `SourcePopAfter<-SourcePopBefore`) with bounded depth (`--lineage-fallback-max-depth`, default `14`); fallback traversal must continue through previous-stage temporary bridge nodes rather than treating them as authoritative count sources. Unresolved transitions still fall back to entry-window totals.
- If a bridge-aware candidate transition still yields a positive delta with no mixed-batch rows, semantic validation downgrades that transition to `entry_window` with `entry_window_reason=incomplete_linkage` for gate handling when either (a) entry populations receive outside-component incoming sources, (b) lineage-graph fallback was needed, or (c) bridge-aware consolidation shape (`many linked sources -> fewer linked destinations`) indicates likely missing lineage context.
- Mortality biomass (`FishTalk` vs `AquaMind`) is informational only in semantic reports; FishTalk extract biomass is often zero while AquaMind derives event biomass from status snapshots, and this diff is not a regression gate criterion.

### 10.4 Migration Confidence Ramp (2026-02-10)

**Implemented instrumentation (code + reports):**
1. Semantic transition linkage coverage fields are now emitted per transition:
   - `entry_population_count`
   - `linked_destination_population_count`
   - `bridge_aware_eligible` (true when linkage covers all entry populations)
2. Fishgroup tuple-format audit is now part of semantic validation output:
   - check rule: `Fishgroup == InputYear + InputNumber + "." + RunningNumber(4-digit)`
   - supports outlier allowlist (`InputYear|InputNumber|Fishgroup`)
   - default allowlisted pattern: `23|99|23999.000`
3. Regression gates are now implemented in semantic validation (`--check-regression-gates`):
   - fail on positive transition deltas without mixed-batch rows, excluding `entry_window_reason=incomplete_linkage` fallback rows (reported as warnings),
   - fail if zero-count transfer actions reappear (`transferred_count <= 0`),
   - fail when non-bridge zero assignments exceed threshold (`--max-non-bridge-zero-assignments`).
4. Pilot cohort runner added:
   - `scripts/migration/tools/migration_pilot_regression_check.py`
   - reruns semantic reports for migrated pilot components and writes cohort summary with fallback rates.
5. Keep migration-specific classification logic in migration tooling and reports, not in AquaMind runtime API endpoints.

**Single-batch linkage update (Benchmark Gen. Juni 2024, station-focused replay, 2026-02-10):**
- Transition basis changed from `0/4` bridge-aware and `4/4` entry-window to `4/4` bridge-aware and `0/4` entry-window.
- Bridge-aware transitions using lineage fallback: `4`.
- `Egg&Alevin -> Fry` linkage improved to `linked_destination_population_count=12 / entry_population_count=12` under bounded lineage fallback.
- Report: `analysis_reports/2026-02-06/semantic_validation_benchmark_gen_juni_2024_2026-02-10_station_focus.md`

**Additional station-focused replay (Stofnfiskur S-21 feb24, 2026-02-10):**
- Station guard: `S21 Viðareiði`.
- Gates: `PASS` with `non_bridge_zero_assignments=0`.
- Transition basis: `4/4` bridge-aware, `0/4` entry-window.
- Incomplete-linkage fallback transitions: `0`.
- Report: `analysis_reports/2026-02-10/semantic_validation_stofnfiskur_s21_feb24_2026-02-10_station_focus.md`

**Additional station-focused replay (Stofnfiskur Juni 24, 2026-02-10):**
- Station guard: `S03 Norðtoftir`.
- Gates: `PASS` with `non_bridge_zero_assignments=0`.
- Transition basis: `3/4` bridge-aware, `1/4` entry-window.
- Incomplete-linkage fallback transitions: `1` (`Fry -> Parr`).
- `Egg&Alevin -> Fry` now remains bridge-aware after adding S03 hall mapping `Kleking -> Egg&Alevin`.
- Report: `analysis_reports/2026-02-10/semantic_validation_stofnfiskur_juni24_2026-02-10_station_focus_kleking_fix_v3.md`

**Deterministic FW->Sea evidence extractor (tooling-only, 2026-02-10):**
- Script added: `scripts/migration/analysis/fw_to_sea_deterministic_evidence.py`.
- Inputs:
  - `population_members.csv` (stitched component),
  - `sub_transfers.csv` (graph edges),
  - `populations.csv` + `grouped_organisation.csv` (destination context).
- Marine criterion is explicit only: destination `ProdStage` contains `Marine`.
- Heuristic naming/date matching is not used.
- Current outputs for station-focused FW batches (`Benchmark Gen. Juni 2024`, `Stofnfiskur S-21 feb24`, `Stofnfiskur Juni 24`) all show:
  - outside-component linkage present,
  - direct destination context `ProdStage=Hatchery`,
  - `marine_linkage_evidence=false`.

**Current measured status from cohort rerun (`semantic_validation_pilot_cohort_2026-02-10.md`):**
- Components checked: `5`
- Stage transitions checked: `11`
- Bridge-aware transitions: `4/11` (`36.4%`)
- Entry-window transitions (fallback): `7/11` (`63.6%`)
- Positive transition deltas without mixed-batch rows: `0`
- Zero-count transfer actions: `0` across checked components
- Fishgroup tuple-format audit (global extract): `184,229 / 184,234` matched, `5` outliers (all allowlisted `23|99|23999.000`)
- FW-only cohort (`semantic_validation_fw_pilot_cohort_2026-02-09.md`): `3` components, `11` transitions, same basis split (`4` bridge-aware / `7` entry-window), with `Benchmark Gen. Juni 2024` as the only failing gate component.

**Gate result status (current threshold `max_non_bridge_zero_assignments=2`):**
- PASS: `SF NOV 23`, `Stofnfiskur S-21 nov23`
- FAIL: `Benchmark Gen. Juni 2024`, `Summar 2024`, `Vár 2024` (high non-bridge zero-assignment counts)

## 11. Transformation Functions

### 11.1 Date/Time Conversion
```python
def convert_to_utc(dt_value, source_tz='Europe/London'):
    """Convert FishTalk datetime to UTC for AquaMind"""
    if pd.isna(dt_value):
        return None
    local_dt = pd.to_datetime(dt_value)
    local_dt = local_dt.tz_localize(source_tz)
    return local_dt.tz_convert('UTC')
```

### 11.2 Weight Conversion
```python
def normalize_weight_grams(weight_g):
    """FishTalk weight samples are stored in grams; do not apply kg heuristics."""
    if weight_g is None or pd.isna(weight_g):
        return None
    return round(float(weight_g), 2)
```

### 11.3 Status Mapping
```python
def map_status(fishtalk_status, mapping_dict):
    """Map FishTalk status to AquaMind status"""
    default_status = 'INACTIVE'
    if pd.isna(fishtalk_status):
        return default_status
    return mapping_dict.get(fishtalk_status, default_status)
```

## 12. Audit & Tracking

### 12.1 Migration Metadata
Each migrated record should include:
```json
{
    "migration_metadata": {
        "source_system": "FishTalk",
        "source_id": "original_id",
        "migration_date": "2024-12-01T00:00:00Z",
        "migration_batch": "BATCH_001",
        "migration_version": "1.0"
    }
}
```

### 12.2 Audit Trail Continuity
- Preserve original created/modified dates
- Store original user IDs for reference
- Maintain change history where available
- Create migration user for system changes

## 13. Error Handling

### 13.1 Error Categories
1. **Critical Errors** - Stop migration
   - Missing required fields
   - Foreign key violations
   - Duplicate key violations

2. **Warnings** - Log and continue
   - Data truncation
   - Default value substitution
   - Unmapped values

3. **Information** - Log only
   - Successful transformations
   - Row counts
   - Performance metrics

### 13.2 Error Logging Format
```json
{
    "timestamp": "2024-12-01T10:00:00Z",
    "level": "ERROR",
    "source_table": "FishTalk.Project",
    "source_id": 12345,
    "target_table": "batch_batch",
    "field": "species_id",
    "error": "Species 'AtlanticCod' not found in reference table",
    "action": "Record skipped"
}
```

---

## 14. Scenario Model Mapping (TGC, FCR, Temperature)

**Purpose:** Migrate growth model master data to enable AquaMind's projection and planning features.

### 14.1 Temperature Profile Mapping (FishTalk: TemperatureTables + TemperatureTableEntries)

| FishTalk Source | AquaMind Target | Data Type | Transformation | Notes |
|-----------------|-----------------|-----------|----------------|-------|
| TemperatureTables.TemperatureTableID | ExternalIdMap | uuid | Store for idempotency | `source_model = TemperatureTables` |
| "FT-TempProfile-{ID[:8]}" | scenario_temperatureprofile.name | varchar(255) | Generated | Unique name |
| TemperatureTableEntries.IntervalStart | scenario_temperaturereading.day_number | int | Direct (already day-based) | 1-900 range |
| TemperatureTableEntries.Temperature | scenario_temperaturereading.temperature | float | Direct | Celsius |

**Row counts:** 20 profiles, 240 readings

### 14.2 TGC Model Mapping (FishTalk: GrowthModels + TGCTableEntries)

| FishTalk Source | AquaMind Target | Data Type | Transformation | Notes |
|-----------------|-----------------|-----------|----------------|-------|
| GrowthModels.GrowthModelID | ExternalIdMap | uuid | `source_model = GrowthModels_TGC` | Separate from FCR mapping |
| GrowthModels.Comment | scenario_tgcmodel.name | varchar(255) | Prefix with "FT-TGC-" | Trim to 255 chars |
| AVG(TGCTableEntries.TGC) | scenario_tgcmodel.tgc_value | float | Average of day-specific values | Per model |
| "FishTalk Import" | scenario_tgcmodel.location | varchar(255) | Static | |
| "Year-round" | scenario_tgcmodel.release_period | varchar(255) | Static | |
| 0.33 | scenario_tgcmodel.exponent_n | float | Default | Standard exponent |
| 0.66 | scenario_tgcmodel.exponent_m | float | Default | Standard exponent |
| (first available) | scenario_tgcmodel.profile_id | FK | Default profile | Required FK |

**Note:** TGCTableEntries contains day-specific TGC values (7,530 rows). These are averaged to produce a single `tgc_value` per model since AquaMind uses a simpler model structure.

### 14.3 FCR Model Mapping (FishTalk: GrowthModels + FCRTableEntries)

| FishTalk Source | AquaMind Target | Data Type | Transformation | Notes |
|-----------------|-----------------|-----------|----------------|-------|
| GrowthModels.GrowthModelID | ExternalIdMap | uuid | `source_model = GrowthModels_FCR` | |
| GrowthModels.Comment | scenario_fcrmodel.name | varchar(255) | Prefix with "FT-FCR-" | |

**Stage derivation:** FCRTableEntries contains weight/temperature-specific FCR values. Aggregate to lifecycle stages:

| Weight Range (g) | AquaMind Stage | Duration (days) |
|-----------------|----------------|-----------------|
| 0.0 - 0.5 | Egg&Alevin | 90 |
| 0.5 - 5.0 | Fry | 60 |
| 5.0 - 30.0 | Parr | 120 |
| 30.0 - 100.0 | Smolt | 90 |
| 100.0 - 500.0 | Post-Smolt | 90 |
| 500.0+ | Adult | 360 |

| FishTalk Source | AquaMind Target | Data Type | Transformation | Notes |
|-----------------|-----------------|-----------|----------------|-------|
| AVG(FCRTableEntries.FCR) per stage | scenario_fcrmodelstage.fcr_value | float | Weight-bucketed average | |
| (lookup) | scenario_fcrmodelstage.stage_id | FK | LifecycleStage lookup | |
| (from mapping table) | scenario_fcrmodelstage.duration_days | int | Default per stage | |

**Row counts:** 120 GrowthModels → 120 FCRModels, up to 6 stages each

### 14.4 Mortality Model Mapping

FishTalk does not have dedicated mortality model tables. Create default mortality models:

| Name | Frequency | Rate (%) | Purpose |
|------|-----------|----------|---------|
| FT-Mortality-Low | daily | 0.01 | Low mortality scenario |
| FT-Mortality-Standard | daily | 0.05 | Standard mortality |
| FT-Mortality-High | daily | 0.10 | High mortality scenario |

### 14.5 ExternalIdMap Source Models

| source_model | Description |
|--------------|-------------|
| `TemperatureTables` | Temperature profile mapping |
| `GrowthModels_TGC` | TGC model mapping |
| `GrowthModels_FCR` | FCR model mapping |

---

**Document Control**
- Version: 5.5
- Status: Revised
- Last Updated: 2026-02-28
- Next Review: [Pending]

## 15. External ID Mapping Tables

AquaMind now persists source-to-target identifier mappings in the `apps.migration_support.ExternalIdMap` model. Each row captures the FishTalk identifier (`source_system='FishTalk'`) and the AquaMind object it produced.

| Field | Description |
| --- | --- |
| source_system | External system name (e.g., `FishTalk`, `Aveva`). |
| source_model | Source table/entity (Populations, Feeding, etc.). |
| source_identifier | Primary key in the source system (PopulationID, FeedingID...). |
| target_app_label / target_model | Django app + model storing the migrated row. |
| target_object_id | Primary key of the AquaMind object. |
| metadata | JSON payload for auxiliary context (batch numbers, timestamps, etc.). |

Use this table to de-duplicate replays, troubleshoot migrations, and produce reconciliation reports. The mapping scripts should always look up existing entries before creating new AquaMind records to keep migrations idempotent.
