# Infrastructure ETL Plan (FishTalk → AquaMind)

**Goal:** Load infra assets via Django domain methods to preserve audit/history. Use perfect UUID-based mapping; when ambiguous, stage and resolve before load.

## 0) Principles
- **UUIDs are authoritative** (never names).
- **Idempotent replays** via `migration_support.ExternalIdMap`.
- **Django domain methods only** for create/update to populate audit/history.
- **Staging tables** for ambiguous or incomplete mappings.

## 1) Source of Truth (FishTalk)
- Containers → `dbo.Containers`
- OrgUnits → `dbo.OrganisationUnit`
- Geo hint → `dbo.Ext_GroupedOrganisation_v2` (view)
- Locations → `dbo.Locations` (sparse; fallback only)

## 2) Target Entities & ID Strategy
| Target | Source UUID | ExternalIdMap source_model |
|---|---|---|
| infrastructure_geography | derived | GeographyDerived |
| infrastructure_freshwaterstation | OrganisationUnit.OrgUnitID | OrganisationUnitStation |
| infrastructure_hall | OrgUnitID + ContainerGroupID | OrganisationUnitHall |
| infrastructure_area | OrganisationUnit.OrgUnitID | OrganisationUnitArea |
| infrastructure_container | Containers.ContainerID | Containers |

## 3) Staging Tables (needed)
Create staging for resolution where UUID-only mapping is incomplete:
- **stg_infra_container_geo**: ContainerID, OrgUnitID, Site, SiteGroup, LocationID, DerivedGeo, Confidence
- **stg_infra_container_hall**: ContainerID, OrgUnitID, ContainerGroupID, ContainerGroup, HallNameCandidate
- **stg_infra_orgunit_geo**: OrgUnitID, Site, SiteGroup, LocationID, DerivedGeo, Confidence
- **stg_infra_unmapped**: Any record missing mandatory links (container_type, hall/area)

Purpose: human review + corrections before final load.

## 4) ETL Steps
### 4.1 Extract
- Pull raw FishTalk tables into staging schemas (`stg_*`) using SQL scripts.
- Keep full UUIDs and raw source fields.

### 4.2 Transform (staging logic)
- Compute `DerivedGeo` using SiteGroup/Site list fallback rules.
- Compute `HallNameCandidate` from ContainerGroup/OfficialID.
- Classify freshwater vs sea: `ProdStage` + hall presence.

### 4.3 Load (Django domain methods)
- Use management commands or domain services (not direct SQL) to create:
  1) Geography
  2) Freshwater stations
  3) Halls
  4) Sea areas
  5) Containers

- Each create/update:
  - Check ExternalIdMap for idempotency
  - Set audit user = migration user
  - Update `metadata` with source UUID + source fields

## 5) Validation Checklist
- Every container has: type, name, and either hall (FW) or area (Sea)
- Geography resolved for >= 95% of containers
- ExternalIdMap row for each migrated object
- No duplicate names within same station/area

## 6) Open Questions (to resolve before load)
- Canonical rules for identifying FW vs Sea when ProdStage missing.
- Official list of site → geography mappings (FI/SC).
- Hall naming normalisation rules (Høll → Hall, etc.)

---
**Next Action:** draft extract SQL + Django loader skeletons for infra assets.
