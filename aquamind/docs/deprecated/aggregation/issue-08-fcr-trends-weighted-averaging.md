# FCR Trends — implement weighted averaging and unit tests

## Endpoint / Scope
Existing: `/api/v1/operational/fcr-trends/` (ViewSet + Service)

## Summary
Replace simple averaging with **weighted averaging** when aggregating container-level FCR into batch / geography scopes.

## Outcome
- Aggregations are weighted by `total_feed_kg` (or `biomass_gain_kg` where available) across containers in a bucket.  
- Results remain stable across differing container sizes and feeding volumes.

## Scope
- Update aggregation in `apps/inventory/services/fcr_service.py` (e.g., `aggregate_container_fcr_to_batch`) and ensure `FCRTrendsService` consumes it correctly.  
- Confirm bucketization aligns with interval semantics (**DAILY, WEEKLY, MONTHLY**) and does not regress.  
- Update / extend serializer or service to round ratios consistently.

## References
- `apps/operational/api/viewsets/fcr_trends.py`  
- `apps/operational/services/fcr_trends_service.py`  
- `apps/inventory/services/fcr_service.py`  
- Recommendations doc (FCR checklist)

## Implementation Steps
1. Introduce a weighting factor (prefer `total_feed_kg`; fallback to `biomass_gain_kg` if available and more appropriate).  
2. Adjust aggregation formulas to compute a weighted mean FCR:  
   `weighted_fcr = Σ(feed_kg * fcr) / Σ(feed_kg)` (or analogous for biomass_gain).  
3. Validate edge cases (zero weight, missing data) with sensible defaults and guards.  
4. Update unit tests to include containers with very different feed amounts; assert weighted results.

## Testing
- Add tests at `apps/operational/tests/api/test_fcr_trends_weighting.py`.  
- Cases: equal vs unequal weights; zero-weight containers; multiple intervals (DAILY, WEEKLY, MONTHLY).

## Acceptance Criteria
- Weighted averages are correct; all tests pass; OpenAPI unchanged unless new fields are added.  
- No regressions in existing FCR trends behavior.
