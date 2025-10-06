# ADR 0001 – Lightweight Intercompany Handling & Finance Dimensions

- **Status:** Accepted
- **Date:** 2025-10-06
- **Deciders:** Harvest & Finance Working Group
- **Consulted:** Operations, Finance, BI Platform

## Context

AquaMind must support inter-company (IC) reporting and Power BI analytics without introducing heavy cross-app coupling or disrupting the existing operational schema. The current system has no dedicated legal entity model. User segmentation relies on `geography` and `subsidiary` enums stored on `users.UserProfile` and reflected in infrastructure objects. Issue 2 introduces harvest destinations (`dest_geography`, `dest_subsidiary`) to capture receiving entities.

The finance program requires:

- Reliable IC detection when source and destination legal entities differ.
- Dimensional facts for analytics and NAV exports, derived from operational data.
- Zero impact on operational RBAC and minimal migration risk before UAT.

## Decision

1. **Do not introduce an operational `Company` model.** Operations remain agnostic to legal-entity specifics.
2. **Model legal entities in the finance layer** via two new dimension tables:
   - `DimCompany(geography, subsidiary, display_name, currency, nav_company_code, legal_entity_code?)`
   - `DimSite(<infra object PK>, object_type, dim_company)`
3. **Derive company keys** using existing geography/subsidiary values:
   - `source_company_key = (assignment.container → hall/station → geography, inferred subsidiary)`
   - `dest_company_key = (HarvestEvent.dest_geography, HarvestEvent.dest_subsidiary)`
4. **Detect inter-company movements in finance projections.** Create `IntercompanyTransaction` rows only when source and destination keys differ and a matching `IntercompanyPolicy` exists.
5. **Keep RBAC unchanged.** Operational queries continue to filter by geography/subsidiary.

## Consequences

### Positive

- No new foreign keys or migrations in operational apps ahead of UAT.
- Finance owns legal-entity metadata and can evolve it independently via dimension rows.
- RBAC continues to rely on proven geography/subsidiary filters.
- Projection layer can enrich facts with finance metadata without impacting operational performance.

### Trade-offs

- Operational reporting that needs “company” context must reproduce the derivation logic or query finance dimensions.
- Supporting multiple legal entities per `(geography, subsidiary)` pairing will require extending `DimCompany` with `legal_entity_code` and additional mapping logic.
- Finance must maintain the dimension seed process to keep mappings accurate.

## Alternatives Considered

| Option | Outcome |
|--------|---------|
| Introduce `users.Company` and add foreign keys across apps | Rejected due to high migration cost, cross-app coupling, and risk of context rot pre-UAT. |
| Store free-text company codes on harvest events | Rejected because it breaks referential integrity and undermines RBAC filtering. |
| Use only geography (ignore subsidiary) for IC detection | Rejected because it cannot distinguish Broodstock vs. Farming within a geography. |

## Implementation Notes

- Place new finance models (`DimCompany`, `DimSite`) in the forthcoming finance app.
- Extend `HarvestEvent` with optional `dest_geography` and `dest_subsidiary` fields (Issue 2).
- Ensure projection services derive keys consistently and are idempotent.
- Seed dimension tables from existing enums/infrastructure data; design for re-runs.
- Update design documentation to reference finance-owned dimensions instead of an operational company model.

## Status

- [x] ADR documented (`docs/adr/ADR_0001_lightweight_intercompany_finance_dims.md`).
- [ ] Design spec updated with finance dimension ownership.
- [ ] Implementation plan links to this ADR.
- [ ] Schemathesis & API standards revalidated in later phases.

## Follow-up / Open Decisions

Refer to `aquamind/docs/progress/harvest_and_finance_app/IMPLEMENTATION_PLAN.md` for the active decision log.
