# Implement Freshwater Station KPI Summary endpoint (halls, containers, biomass, population, avg weight)

## Endpoint  
`GET /api/v1/infrastructure/freshwater-stations/{id}/summary/`

## Summary  
Add a detail action on `FreshwaterStationViewSet` that returns station-level KPI metrics for KPI cards, eliminating client-side joins currently done in `useStationKpi`.

## Outcome  
The endpoint returns the following fields:

| Field               | Type | Description                                                          |
|---------------------|------|----------------------------------------------------------------------|
| `hall_count`        | int  | Number of Halls belonging to the station                             |
| `container_count`   | int  | Number of Containers inside those halls                              |
| `active_biomass_kg` | dec  | Sum of `BatchContainerAssignment.active_biomass_kg` (active only)    |
| `population_count`  | int  | Sum of `BatchContainerAssignment.population` (active only)           |
| `avg_weight_kg`     | dec  | `active_biomass_kg / population_count` (0 if population is 0)        |

## Scope  
- Add `@action(detail=True, methods=["get"])` named `summary` to **FreshwaterStationViewSet**.  
- Aggregate via ORM:  
  • `hall_count` from `Hall` records linked to the station.  
  • `container_count` from `Container` records in those halls.  
  • Biomass & population from **active** `BatchContainerAssignment` rows for those containers.  
  • Compute `avg_weight_kg`, guarding against division-by-zero.  
- Decorate action with `@method_decorator(cache_page(60))` (60 s TTL).  
- Document request/response using `drf-spectacular`’s `@extend_schema` and an explicit `FreshwaterStationSummarySerializer`.

## References  
- Recommendations document: `aquamind/docs/progress/aggregation/server-side-aggregation-kpi-recommendations.md`  
- `apps/infrastructure/api/viewsets/station.py` → `FreshwaterStationViewSet`  
- `apps/batch/api/viewsets.py` → `BatchContainerAssignmentViewSet.summary` (aggregation patterns)  
- Front-end hook: `client/src/hooks/aggregations/useStationKpi.ts`  
- API standards: `aquamind/docs/quality_assurance/api_standards.md`

## Implementation Steps  
1. In `FreshwaterStationViewSet`, add:  
   ```python
   @method_decorator(cache_page(60), name="summary")
   @action(detail=True, methods=["get"], url_path="summary")
   @extend_schema(
       responses=FreshwaterStationSummarySerializer,
       description="Return KPI roll-up for a single Freshwater Station."
   )
   def summary(self, request, pk=None):
       ...
   ```  
2. Query halls: `Hall.objects.filter(freshwater_station_id=pk)` → derive `hall_count`.  
3. Query containers in those halls → derive `container_count`.  
4. Join active `BatchContainerAssignment` rows for those containers and aggregate:  
   * `active_biomass_kg = Sum("biomass_kg")`  
   * `population_count = Sum("population")`  
5. Compute `avg_weight_kg` (set to `0` if `population_count` is `0`).  
6. Build `FreshwaterStationSummarySerializer` with the five fields and example values.  
7. Write unit tests and regenerate OpenAPI schema.

## Testing  
Create `apps/infrastructure/tests/api/test_freshwater_station_summary.py` with scenarios:  
1. Station with no halls → all metrics `0`.  
2. Station with halls but **no containers** → hall_count reflects halls, other metrics `0`.  
3. Station with containers but **no active assignments** → biomass & population `0`.  
4. Station with mixed halls/containers/assignments → verify all metrics.  
5. Division-by-zero protection (`avg_weight_kg == 0` when `population_count == 0`).  
6. Cache neutrality: consecutive calls within 60 s return identical payload faster.

## Acceptance Criteria  
- Metrics correct; all tests pass.  
- drf-spectacular schema validates without warnings.  
- Endpoint path and router use kebab-case conventions under `/api/v1/`.  
- Endpoint respects existing permission classes.  
- Response time < 200 ms when served from cache.  
