# Implement Hall KPI Summary endpoint (containers, biomass, population, avg weight)

## Endpoint  
`GET /api/v1/infrastructure/halls/{id}/summary/`

## Summary  
Add a detail action on `HallViewSet` that returns hall-level KPI metrics for KPI cards, eliminating the need for client-side aggregation.

## Outcome  
The endpoint returns the following fields:

| Field               | Type | Description                                                     |
|---------------------|------|-----------------------------------------------------------------|
| `container_count`   | int  | Number of Containers in the hall                                |
| `active_biomass_kg` | dec  | Sum of `BatchContainerAssignment.active_biomass_kg` (active only) |
| `population_count`  | int  | Sum of `BatchContainerAssignment.population` (active only)      |
| `avg_weight_kg`     | dec  | `active_biomass_kg / population_count` (0 if population is 0)   |

## Scope  
- Add `@action(detail=True, methods=["get"])` named `summary` to **HallViewSet**.  
- Aggregate via ORM:  
  • `container_count` from `Container` records linked to the hall.  
  • Biomass & population from **active** `BatchContainerAssignment` rows for those containers.  
  • Compute `avg_weight_kg`, guarding against division-by-zero.  
- Decorate action with `@method_decorator(cache_page(60))` (60 s TTL).  
- Document request/response using `drf-spectacular`’s `@extend_schema` and an explicit `HallSummarySerializer`.  

## References  
- Recommendations document: `aquamind/docs/progress/aggregation/server-side-aggregation-kpi-recommendations.md`  
- `apps/infrastructure/models` and `api/viewsets` for **Hall** and **Container**  
- `apps/batch/api/viewsets.py` → `BatchContainerAssignmentViewSet.summary` (aggregation patterns)  
- API standards: `aquamind/docs/quality_assurance/api_standards.md`

## Implementation Steps  
1. In `HallViewSet`, add:  
   ```python
   @method_decorator(cache_page(60), name="summary")
   @action(detail=True, methods=["get"], url_path="summary")
   @extend_schema(
       responses=HallSummarySerializer,
       description="Return KPI roll-up for a single Hall."
   )
   def summary(self, request, pk=None):
       ...
   ```  
2. Query containers: `Container.objects.filter(hall_id=pk)` → derive `container_count`.  
3. Join active `BatchContainerAssignment` rows for those containers and aggregate:  
   * `active_biomass_kg = Sum("biomass_kg")`  
   * `population_count = Sum("population")`  
4. Compute `avg_weight_kg` (set to `0` if `population_count` is `0`).  
5. Build `HallSummarySerializer` with the four fields and example values.  
6. Add/extend unit tests; regenerate OpenAPI schema.

## Testing  
Create `apps/infrastructure/tests/api/test_hall_summary.py` with scenarios:  
1. Hall with no containers → all metrics `0`.  
2. Hall with containers but **no active assignments** → biomass & population `0`.  
3. Typical hall with mixed containers/assignments → verify all metrics.  
4. Division-by-zero protection (`avg_weight_kg == 0` when `population_count == 0`).  
5. Cache neutrality: consecutive calls within 60 s return identical payload faster.

## Acceptance Criteria  
- Returned metrics match ground-truth queries; unit tests pass.  
- OpenAPI schema validates without warnings.  
- Endpoint respects existing permission classes and kebab-case router conventions.  
- Response time < 200 ms when served from cache.
