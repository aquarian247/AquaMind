# Server-side Aggregation for KPI Cards — Implementation Plan (Issue-ready)

Audience: **Backend engineers**  
Purpose: Split the recommendations into outcome-driven, single-session tasks with standardized guidance to minimize context rot. Each task below is presented as an **issue** (title + body, issues 44 through 53 in github). This must all be done in the same feature branch: features/aggregations-for-frontend

---

## Shared context to read before any task

* Recommendations: `aquamind/docs/progress/aggregation/server-side-aggregation-kpi-recommendations.md`
* API standards: `aquamind/docs/quality_assurance/api_standards.md`
* Existing aggregates to mirror  
  * `apps/infrastructure/api/viewsets/overview.py`  
  * `apps/batch/api/viewsets.py` → `BatchContainerAssignmentViewSet.summary`  
  * `apps/inventory/api/viewsets/feeding.py` → `FeedingEventViewSet.summary`
* FCR trends reference  
  * `apps/operational/api/viewsets/fcr_trends.py`  
  * `apps/operational/services/fcr_trends_service.py`  
  * `apps/inventory/services/fcr_service.py`

### Session Playbook (use for every task)

1. Pre-read shared context (5–10 min) **and** the task’s References list.  
2. Add endpoint/action skeleton with explicit kebab-case basename and `extend_schema`. Keep under `/api/v1/`.  
3. Implement DB-level aggregates (`Sum` / `Count`), add 30–60 s cache via `cache_page`.  
4. Add tests (success, edge cases, filters, caching neutrality) and update OpenAPI schema.  
5. Run Django tests **and** OpenAPI validation; ensure no drf-spectacular warnings.  
6. Update Sources/notes if anything deviates from recommendations.

**Definition of Done (applies to all tasks)**  
✔ Endpoint functional with documented schema and inputs.  
✔ Tests cover happy-path + edge cases + filter variations.  
✔ OpenAPI validates; CI passing locally.  
✔ Caching set to 30–60 s where applicable.  
✔ Naming/routers follow `api_standards.md`.

---

## Issue 1 (no. 44 in github) — Establish Aggregation Implementation Playbook (patterns, tests, docs)

**Title:** Establish Aggregation Implementation Playbook (patterns, tests, docs)

**Body**

**Summary**  
Make sure we are on a main and everything is pruned and remnant feature branches are deleted. Then create features/aggregations-for-frontend branch for this side-quest. 
Create a small shared “playbook” to standardize how we build aggregation endpoints for KPI cards (patterns, caching, schema, tests). This reduces context rot across sessions.

**Outcome**  
A concise doc and example snippet(s) that every subsequent task follows. CI validation steps are codified.

**Scope**  
* Add a short doc section (or sibling doc) with:  
  * Required imports, `@action` vs APIView selection, example `extend_schema`, `cache_page`.  
  * Test example structure using `reverse()` with kebab-case basenames.  
  * OpenAPI validation command and expectations.  
* **No business endpoint implementation here.**

**References**  
See shared context list.

**Approach**  
Add “Session Playbook” section (if not already) + minimal code & test template.

**Acceptance Criteria**  
* Playbook published; linked from recommendations doc.  
* Includes code templates, test template, and validation commands.

---

## Issue 2 (no. 45 in github) — Area KPI Summary endpoint (/infrastructure/areas/{id}/summary/)

**Title:** Implement Area KPI Summary endpoint (containers, biomass, population, avg weight)

**Body**

**Summary**  
Add a detail action that returns area-level KPI metrics for KPI cards, replacing client-side joins in `useAreaKpi`.

**Outcome**  
GET returns: `container_count`, `ring_count`, `active_biomass_kg`, `population_count`, `avg_weight_kg`.

**Scope**  
* `@action(detail=True, methods=['get'])` on `AreaViewSet`.  
* Compute via ORM aggregates across Containers in area and active BatchContainerAssignments.  
* 30–60 s cache; `extend_schema`.

**References**  
Frontend hook, recommendations doc, overview & assignment summaries.

**Implementation Steps**  
1. Add action `summary(self, request, pk=None)`.  
2. Query containers; calc counts/sums; derive avg weight.  
3. Schema + caching + tests.

**Testing**  
`apps/infrastructure/tests/api/test_area_summary.py` with multiple scenarios.

**Acceptance Criteria**  
Endpoint metrics correct; tests pass; OpenAPI validates.

---

## Issue 3 (no. 46 in github) — Freshwater Station KPI Summary endpoint (/infrastructure/freshwater-stations/{id}/summary/)

**Title:** Implement Freshwater Station KPI Summary endpoint (halls, containers, biomass, population, avg weight)

**Body**

(Same template; focus on station-level metrics.)

---

## Issue 4 (no. 47 in github) — Hall KPI Summary endpoint (/infrastructure/halls/{id}/summary/)

**Title:** Implement Hall KPI Summary endpoint (containers, biomass, population, avg weight)

**Body**

(Same template; hall-level.)

---

## Issue 5 (no. 48 in github) — Geography KPI Summary endpoint (/infrastructure/geographies/{id}/summary/)

**Title:** Implement Geography KPI Summary endpoint (area/station/hall/container/ring counts, capacity, biomass)

**Body**

(Same template; geography-level plus capacity.)

---

## Issue 6 (no. 49 in github) — Enhance /batch/container-assignments/summary with location filters

**Title:** Enhance container-assignments summary with geography/area/station/container_type filters

**Body**

(Same template; add optional filters.)

---

## Issue 7 (no. 50 in github) — Extend /inventory/feeding-events/summary to support date ranges

**Title:** Extend feeding-events summary with start_date/end_date range (keep date param)

**Body**

(Same template; range support.)

---

## Issue 8 (no. 51 in github) — FCR Trends: Weighted averaging and correctness pass

**Title:** FCR Trends — implement weighted averaging and unit tests

**Body**

(Same template; update weighting logic.)

---

## Issue 9 (no. 52 in github) — FCR Trends: Schema semantics and default behavior

**Title:** FCR Trends — clarify schema (units, data_points, confidence) and default aggregation behavior

**Body**

(Same template; docs & serializer clarity.)

---

## Issue 10 (no. 53 in github) — Integration notes + examples for dashboards

**Title:** Publish integration notes and example requests for dashboard KPI consumption

**Body**

(Same template; append examples to recommendations doc.)

---
