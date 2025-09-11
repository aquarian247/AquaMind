# Extend feeding-events summary with start_date/end_date range (keep date param)

## Endpoint  
GET /api/v1/inventory/feeding-events/summary/

## Summary  
Add optional `start_date` and `end_date` query parameters as an alternative to the existing `date` parameter for aggregating feeding-event metrics over arbitrary ranges.

## Outcome  
- Support requests like `start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` that return totals for the inclusive range.  
- Remain backward-compatible: `date=YYYY-MM-DD` continues to work.  
- Precedence rule: when both range and single‐date params are supplied, the range (`start_date`/`end_date`) wins.

## Scope  
- Extend `FeedingEventViewSet.summary` to parse and validate the date range.  
- Apply a `between` filter on `event_date`; retain existing filters (batch, container, geography, etc.).  
- Update `extend_schema` with new parameters and examples.

## References  
- `apps/inventory/api/viewsets/feeding.py` → `FeedingEventViewSet.summary`  
- `apps/inventory/api/viewsets/summary.py` (range-handling patterns)  
- Recommendations doc: `docs/progress/aggregation/server-side-aggregation-kpi-recommendations.md`

## Implementation Steps  
1. Parse `start_date` and `end_date` (ISO-8601). If only one is provided, return `400`. Validate `start_date ≤ end_date`.  
2. If neither range params nor `date` supplied, default to `date=today` (existing behaviour).  
3. Filter queryset with `event_date__range=(start_date, end_date)`; fall back to `event_date=date` for single-day mode.  
4. Aggregate:  
   - `events_count`: `Count('id')`  
   - `total_feed_kg`: `Coalesce(Sum('feed_kg'), 0)`  
5. Wrap response in existing serializer; ensure numeric types remain `int` and `Decimal`/`float` as today.  
6. Decorate action with `@extend_schema` documenting new params, precedence, and examples.  
7. Add 30–60 s `@cache_page` if not already present.

## Testing  
File: `apps/inventory/tests/api/test_feeding_events_summary_range.py`  
Test cases:  
- Single-day range (`start_date == end_date`) equals `date=` result.  
- Multi-day range aggregates correctly across days.  
- Invalid range (`start_date > end_date`) returns `400`.  
- Only one of `start_date`/`end_date` supplied returns `400`.  
- Both range and `date` supplied → range takes precedence.  
- Existing filters (batch, container) still work in range mode.

## Acceptance Criteria  
- Aggregations correct and match database truth for all test cases.  
- All new unit tests pass.  
- OpenAPI schema shows both `start_date` and `end_date` with examples; no `drf-spectacular` warnings.  
- Requests using legacy `date` param continue to succeed unchanged.  
- CI green; caching unchanged or improved.
