# Implement Area KPI Summary endpoint (containers, biomass, population, avg weight)

## Endpoint  
GET `/api/v1/infrastructure/areas/{id}/summary/`

## Summary  
Add a detail action that returns area-level KPI metrics for KPI cards, replacing the client-side joins in `useAreaKpi`.

## Outcome  
Response MUST include the following fields:  
- `container_count`  
- `ring_count`  
- `active_biomass_kg`  
- `population_count`  
- `avg_weight_kg`

## Scope  
- Add `@action(detail=True, methods=["get"])` on **AreaViewSet**.  
- Compute metrics via ORM aggregates across `Container` rows in the area and **active** `BatchContainerAssignment` rows.  
- Apply `@method_decorator(cache_page(60))` for a 60 s cache window.  
- Document the endpoint with `@extend_schema`, providing an explicit response serializer.

## References  
- Recommendations doc: `aquamind/docs/progress/aggregation/server-side-aggregation-kpi-recommendations.md`  
- `apps/infrastructure/api/viewsets/overview.py`  
- `apps/batch/api/viewsets.py` → `BatchContainerAssignmentViewSet.summary`  
- Front-end hook: `client/src/hooks/aggregations/useAreaKpi.ts`

## Implementation Steps  
1. In **AreaViewSet**, add:
   ```python
   @method_decorator(cache_page(60), name="summary")
   @action(detail=True, methods=["get"], url_path="summary")
   @extend_schema(
       responses=AreaSummarySerializer,
       description="Return KPI roll-up for a single Area."
   )
   def summary(self, request, pk=None):
       ...
   ```
2. Inside `summary`:
   - Fetch containers: `Container.objects.filter(area_id=pk)`  
   - `container_count = containers.count()`  
   - `ring_count = containers.filter(container_type__icontains="ring").count()`  
   - Join active `BatchContainerAssignment` for those containers, aggregate:  
     - `active_biomass_kg = Sum("biomass_kg")`  
     - `population_count = Sum("population")`  
   - Compute `avg_weight_kg = active_biomass_kg / population_count` (guard against division-by-zero).  
3. Serialize the five metrics; convert `Decimal` to `float` where appropriate.  
4. Add `AreaSummarySerializer` with explicit field types and examples.  
5. Write unit tests and regenerate OpenAPI schema.

## Testing  
File: `apps/infrastructure/tests/api/test_area_summary.py`

Scenarios:  
- Empty area → all metrics zero.  
- Area with containers but **no active assignments** → biomass & population zero.  
- Mix of ring / non-ring containers → verify `ring_count`.  
- Division-by-zero protection (`avg_weight_kg == 0` when `population_count == 0`).  
- Cache neutrality: second call within 60 s returns identical payload faster.

## Acceptance Criteria  
- Metrics correct; all tests pass.  
- drf-spectacular schema validates without warnings.  
- Endpoint path and router use kebab-case conventions under `/api/v1/`.  
- Response time < 200 ms with warm cache; respects existing authentication/permissions.
