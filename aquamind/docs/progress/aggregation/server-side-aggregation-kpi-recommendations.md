# Server-side Aggregation for KPI Cards (v1) — Recommendations & Specs

Audience: **Backend engineers**  
Scope: Replace high-impact client-side aggregations for KPI card-like GUI components with server-side endpoints under `/api/v1/`. Provide concise strategy, prioritized endpoints, and example payloads as inspiration. Address any gaps in the existing FCR trends feature.

---

## Executive Summary

• Adopt small, purpose-built aggregation endpoints to power KPI cards for geographies, areas, stations, and halls.  
• Reuse patterns already present in the codebase (e.g., `/infrastructure/overview`, `container-assignments/summary`, `feeding-events/summary`) to keep it simple and consistent.  
• Prioritize endpoints that eliminate expensive client-side joins (containers × assignments) used by the dashboard and area/station KPI hooks.  
• FCR trends are largely in place; a few improvements will make the feature complete and clearer for consumers.

---

## Current State (What Exists Today)

* **Infrastructure overview endpoint** – totals for containers, capacity, active biomass, and today’s feeding events [6].  
* **Batch container assignments summary** – aggregates active biomass and count [7].  
* **Inventory feeding summary endpoints** – model/viewset for summaries and a `feeding-events/summary` action for quick counts [8][9].  
* **Operational FCR trends endpoint & service** – daily/weekly/monthly intervals, batch/assignment/geography scopes, predicted + actual merge [10][11].  
* **Frontend** performs client-side aggregation for KPI cards (area/station) and various dashboard metrics, causing over-fetching and extra compute in the browser [2][3][5].  
* **ADR** allows client-side aggregation only when backend endpoints are missing; prefer server-side aggregation as endpoints become available [1].

---

## Gaps Driving KPI Server Endpoints

* **Area KPI**: total biomass, average weight, container count, population count computed client-side via multiple list endpoints [2].  
* **Station KPI**: same pattern as area; joins halls → containers → active assignments [3].  
* **Geography-level rollups**: counts of areas, stations, halls, rings, containers; total capacity & active biomass (partly covered by overview) — not available per-entity.  
* **Dashboard KPIs**: mixed sources & client aggregation; can be simplified by reusing new KPI endpoints and existing summaries [5][6][8].

---

## Recommendations (Concise Strategy)

1. Provide small, cached summary endpoints per infrastructure entity following existing naming patterns (kebab-case, explicit basenames, DRF viewsets + `@action` where applicable).  
2. Keep response shapes minimal: counts and sums only (e.g., `container_count`, `ring_count`, `active_biomass_kg`, `population_count`, `avg_weight_kg`). Compute `avg_weight` as `biomass / population`.  
3. Reuse existing models for aggregation: `Container`, `BatchContainerAssignment`, `FeedingEvent`. Use DB-level aggregates (`Sum`/`Count`) and short cache windows (30–60 s).  
4. Keep under `/api/v1/`. Apply standard auth and geography-based filters as needed.  
5. Use `drf-spectacular` for explicit schemas and clear OpenAPI documentation for each endpoint.

---

## Proposed Endpoints (Inspiration Specs)

_All endpoints under `/api/v1/`; payloads are inspirational, not prescriptive._

### 1) Area KPI Summary

* **GET** `/infrastructure/areas/{id}/summary/`  
* Replaces `useAreaKpi` client aggregation [2].  
* Query params: `is_active=true|false` (default `true`)  
* Response:
```json
{
  "container_count": 18,
  "ring_count": 12,
  "active_biomass_kg": 84250.5,
  "population_count": 213400,
  "avg_weight_kg": 0.395
}
```
* Implementation notes  
  • `container_count`: `Container.objects.filter(area_id=id).count()`  
  • `ring_count`: filter by container_type category/name containing “Ring”/“Pen” [5]  
  • Biomass & population: sum over active `BatchContainerAssignment` for containers in area [7]  
  • Cache 30–60 s; document schema via `extend_schema`.

### 2) Freshwater Station KPI Summary

* **GET** `/infrastructure/freshwater-stations/{id}/summary/`  
* Replaces `useStationKpi` client aggregation [3].  
* Query params: `is_active=true|false`  
* Response:
```json
{
  "hall_count": 6,
  "container_count": 42,
  "active_biomass_kg": 35670.8,
  "population_count": 90500,
  "avg_weight_kg": 0.394
}
```
* Implementation notes  
  • `hall_count`: `Hall.objects.filter(freshwater_station_id=id).count()`  
  • Biomass & population: assignments in containers under those halls [7].

### 3) Hall KPI Summary

* **GET** `/infrastructure/halls/{id}/summary/`  
* Response:
```json
{
  "container_count": 14,
  "active_biomass_kg": 12100.2,
  "population_count": 31000,
  "avg_weight_kg": 0.39
}
```

### 4) Geography KPI Summary

* **GET** `/infrastructure/geographies/{id}/summary/`  
* Response:
```json
{
  "area_count": 5,
  "station_count": 3,
  "hall_count": 11,
  "container_count": 124,
  "ring_count": 48,
  "capacity_kg": 250000.0,
  "active_biomass_kg": 132500.0
}
```
* Implementation notes: blend counts plus capacity (`Container.max_biomass_kg`) & active biomass (see overview) [6].

### 5) Generic Container/Assignment Summary (Optional)

* **GET** `/infrastructure/containers/summary/?area={id}&station={id}&hall={id}&geography={id}`  
* Returns counts & biomass; useful fallback when bespoke endpoints aren’t available.

### 6) Batch Assignment Summary (Enhance Existing)

* **GET** `/batch/container-assignments/summary/?is_active=true&geography={id}&area={id}&station={id}&container_type={slug}`  
* Extend current summary with standard location filters [7].

### 7) Feeding Events Summary (Enhance Existing)

* **GET** `/inventory/feeding-events/summary/?date=today|YYYY-MM-DD&batch={id}&container={id}&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`  
* Add `start_date`/`end_date` range alternative [8].  
* Response unchanged: `events_count`, `total_feed_kg`.

---

## Prioritization (Do First → Next)

1. Area summary (replaces `useAreaKpi`) [2]  
2. Station summary (replaces `useStationKpi`) [3]  
3. Geography summary (feeds top-level dashboard cards) [6]  
4. Hall summary (infra drill-down)  
5. Enhance `container-assignments/summary` with filters  
6. Extend `feeding-events/summary` to support date ranges

---

## Integration Notes (Frontend Migration)

* **useAreaKpi** → call `GET /infrastructure/areas/{id}/summary/`; remove container/assignment joins [2].  
* **useStationKpi** → call `GET /infrastructure/freshwater-stations/{id}/summary/` [3].  
* **Dashboard KPI cards** → reuse `/infrastructure/overview` [6], geography summary, and `/inventory/feeding-events/summary` [8]; keep client-only values (e.g., nextFeedingHours) until backend design exists.  
* **api.ts**: switch to server summaries where available; retain graceful fallbacks [5].

---

## FCR Trends — Completion Checklist

1. **Weighted averaging** – replace simple average with weighting by `total_feed_kg` or `biomass_gain_kg` in `aggregate_container_fcr_to_batch` [12].  
2. **Explicit schema** – ensure serializer/docs specify units (ratio), meaning of `data_points`, and semantics of `confidence`/`estimation_method` [10][11].  
3. **Geography defaulting** – document default aggregation behavior and always return explicit `aggregation_level` [10][11].  
4. **Series bucketization** – confirm bucket edges match interval semantics (DAILY, WEEKLY Mon–Sun, MONTHLY calendar) and are documented [10][11].  
5. **Scenario metadata** – keep `scenarios_used`; optionally surface model/version metadata [11].  
6. **Confidence alignment** – ensure weighing-date logic via `GrowthSampleService` feeds into summaries [11][12].

---

## Testing & Quality

* Add API tests mirroring existing patterns (see tests for container-assignments summary) to validate metrics, filters, and caching [7].  
* Update OpenAPI via drf-spectacular (`extend_schema`) for each new summary endpoint [6][10].  
* Keep cache windows short (30–60 s) to avoid stale dashboards.

---

## Sources

[1] AquaMind-Frontend/docs/architecture.md — ADR: API Aggregation Strategy (hybrid approach)  
[2] AquaMind-Frontend/client/src/hooks/aggregations/useAreaKpi.ts — client-side area KPI aggregation  
[3] AquaMind-Frontend/client/src/hooks/aggregations/useStationKpi.ts — client-side station KPI aggregation  
[4] AquaMind-Frontend/client/src/hooks/aggregations/useBatchFcr.ts — client-side batch FCR aggregation  
[5] AquaMind-Frontend/client/src/lib/api.ts — dashboard and infrastructure aggregations  
[6] AquaMind/apps/infrastructure/api/viewsets/overview.py — infrastructure overview aggregation endpoint  
[7] AquaMind/apps/batch/api/viewsets.py — `BatchContainerAssignmentViewSet.summary` aggregation  
[8] AquaMind/apps/inventory/api/viewsets/feeding.py — `FeedingEventViewSet.summary` aggregation  
[9] AquaMind/apps/inventory/api/viewsets/summary.py — batch feeding summary viewset  
[10] AquaMind/apps/operational/api/viewsets/fcr_trends.py — FCRTrendsViewSet  
[11] AquaMind/apps/operational/services/fcr_trends_service.py — FCR trends service logic  
[12] AquaMind/apps/inventory/services/fcr_service.py — batch/container FCR calculation and aggregation
