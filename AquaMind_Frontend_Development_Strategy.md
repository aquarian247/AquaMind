# AquaMind Frontend Development Strategy  
_Branch: `feature/api-contract-unification` · Last updated: 2025-07-22_

## 1 · Gap Analysis – Existing vs Missing

| Domain | Current Assets | Gaps / Missing Pieces | Consequence for Testing |
|--------|----------------|-----------------------|-------------------------|
| **Authentication** | JWT token helpers (`client/src/api/index.ts`), generated `AuthService` | _No visible login page / route_ | Cannot obtain token → every API call is `401` |
| **Species & Lifecycle Models** | Backend endpoints (`/api/v1/batch/species/`, `/life-cycle-stages/`) fully implemented | _No CRUD UI for Species_ | Cannot create batches in UI |
| **Infrastructure Hierarchy** | Endpoints for `areas`, `stations`, `halls`, `containers` | _No navigation / tables / forms_ | Batch assignment & environmental dashboards unusable |
| **Batch Management** | Pages scaffolded (`batch-management.tsx`, analytics views) | Relies on species & infra data; create/edit forms partial | Only read-only mock data possible |
| **Form Components** | Shadcn/ui primitives, generic `<Form/>` wrapper | Domain-specific form schemas & validation absent | Manual data entry blocked |
| **Global UX Shell** | Layout, sidebar, routing via Wouter already exist | Icons & links for new screens | Users cannot reach new views |

## 2 · Priority-Ordered Development Phases

| Phase | Goal | Key Deliverables | Expected Duration* |
|-------|------|------------------|--------------------|
| **P0** | _Unblock authentication & smoke tests_ | • `/login` page (email/username + password)  <br>• Token storage & redirect  | 0.5-1 day |
| **P1** | _Minimal reference data entry_ | • Species list/table + “Add Species” dialog  <br>• Lifecycle stage select (read-only) | 1 day |
| **P2** | _Infrastructure skeleton_ | • Area → Station → Hall → Container hierarchical tables with Create & Edit modals (simple name/parent fields) | 2-3 days |
| **P3** | _Batch creation happy-path_ | • “Create Batch” wizard (select species, container, dates) | 1 day |
| **P4** | _Integrate into existing dashboards_ | • Replace mock fetches with real TanStack Query hooks  <br>• Display counts/KPIs from live API | 2 days |
| **P5** | _Robust forms & validations_ | • zod schemas, error toasts, optimistic updates | incremental |
| **P6** | _Advanced features & polish_ | • Permissions, pagination, search, bulk import | later |

_*Rough engineer-days assuming existing component library._

## 3 · Dependency Graph

```
Login (P0)
   ↓
Species + Lifecycle (P1)        Infrastructure (P2)
        \                         /
         \                       /
          → Batch Creation (P3) →
                    ↓
          Dashboard/Data Views (P4)
```

• P0 is a **hard gate** for any authenticated API call.  
• Species & Infrastructure are **parallelisable** – different endpoints, no overlap.  
• Batch Creation depends on both reference datasets.  
• Dashboards depend on batches + infra data.

## 4 · Suggested Development Approach

1. **Feature-Flag Routes** – wrap new pages in `DEV_FEATURES` flag so unfinished screens don’t break prod builds.  
2. **TanStack Query First** – build each screen around a dedicated hook (`useSpecies()`, `useAreas()`) to centralise API logic.  
3. **Auto-Generated Types Everywhere** – rely on `PaginatedSpeciesList`, `Area` models to avoid manual typing.  
4. **Form Generator Pattern** – lightweight wrapper that maps Zod schema → Shadcn `<FormField/>` components; reduces boilerplate.  
5. **Iterative PRs** – one PR per phase to keep CI green and unblock parallel backend tests.  
6. **Seed Data via Admin** – until UI exists for every entity, continue seeding complex objects in Django admin or fixtures.

## 5 · Quick Wins vs Long-Term Components

| Quick Wins (≤ 1 day) | Impact |
|----------------------|--------|
| Login page using existing AuthService | Enables all authenticated endpoints |
| Species list + create dialog (name + latin_name) | Unblocks batch creation |
| Simple Area list + create (name only) | Foundation for infra hierarchy |
| Reuse generic `<Table/>` + `<Dialog/>` for CRUD | Speeds up multiple pages |

| Long-Term Investments | Rationale |
|-----------------------|-----------|
| Cascading select pickers (Area → Station → Hall → Container) | Smooth UX, avoids data errors |
| Bulk CSV import for infrastructure | Matches backend capability, saves manual entry |
| Unified Form Generator with Zod | Consistent validation & error handling |
| RBAC-aware UI (hide screens based on user roles) | Meets production security requirements |
| Offline-first caching layer | Nice-to-have, can wait post-MVP |

## 6 · Definition of “Testable State”

A build is considered **test-ready** when:

1. Users can log in and obtain JWT token.  
2. At least one species can be created via UI.  
3. At least one area/station/hall/container can be created via UI.  
4. A batch can be created and listed on “Batch Management” page.  
5. Decimal values display with correct precision (2 dp / 4 dp).  
6. All CI pipelines (lint, type-check, unit tests) pass.

---

### Revision History
| Date | Author | Notes |
|------|--------|-------|
| 2025-07-22 | Janus Lærsson (AI-assisted) | Initial strategy draft |

