# Environmental App Code Review Findings (2024-10-03)

## Scope
- Reviewed `apps/environmental` models, serializers, viewsets, and API layer.
- Examined environment-facing configurations impacting these modules (e.g. serializer-field contracts, query actions).

## High-Priority Issues

### PhotoperiodData serializer/model drift
- **Symptom**: `PhotoperiodDataSerializer` (API layer) exposes `artificial_light_start`, `artificial_light_end`, and `notes`, but the model lacks these columns.
- **Impact**: All POST/PUT requests via the API serializer raise `FieldError` and responses leak internal exceptions; browsing the endpoint fails.
- **Suggested mitigation**:
  - Align the serializer with the model (drop the phantom fields) **or** add the missing fields to the model/migrations if they were intended.
  - Add serializer tests against real model instances to catch divergence early.

### WeatherData serializer omissions
- **Symptom**: API serializer omits `wave_period` (present on the model) and constrains `wind_speed`/`precipitation` to `max_digits=5` instead of the model’s `max_digits=6`.
- **Impact**: Legitimate data is silently truncated or rejected; wave-period readings never surface through the API.
- **Suggested mitigation**:
  - Mirror model field definitions exactly in serializer and include `wave_period`.
  - Add regression tests for round-tripping high-precision values.

### EnvironmentalParameter precision mismatch
- **Symptom**: Serializer allows four decimal places while the model stores two.
- **Impact**: Client-provided values round unexpectedly after save, breaking validation expectations.
- **Suggested mitigation**:
  - Match serializer precision to the model or upgrade the model field precision if increased fidelity is required.
  - Document precision expectations in API schema comments if changing.

## Medium-Priority Gaps

### EnvironmentalReading create semantics
- Requires `container` even though model allows `null`; clients can set `recorded_by`, bypassing audit expectations.
- **Mitigation ideas**: Make `container` optional in create serializer; default `recorded_by` to the requesting user in `perform_create` and mark field read-only.

### Query parameter handling in custom actions
- `by_container` / `by_area` actions accept raw strings for `start_time`, `end_time`, and `limit` without validation.
- **Impact**: Bad inputs raise `ValueError` (500s) or allow naive datetimes.
- **Mitigation ideas**: Validate/parse with DRF serializers or `parse_datetime` + explicit error responses; enforce sensible caps for `limit`.

## Optimization Opportunities

### “Recent” actions use N+1 loops
- Iterates over unique pairs issuing separate queries.
- **Mitigation ideas**: Replace with subqueries or window functions (`distinct on` or `Subquery` with `OuterRef`), then add coverage tests for sort order.

### Duplicate viewset implementations
- We maintain both `apps/environmental/views.py` and `apps/environmental/api/viewsets.py` with overlapping logic.
- **Mitigation ideas**: Consolidate into one implementation or share mixins to avoid drift; add smoke tests for both router paths before refactor.

## Follow-Up Actions
- Assign ownership for serializer/model alignment work.
- After fixes, add contract tests (pytest + API client) covering create/update flows and time-filter endpoints.
- Consider adding `select_related`/`prefetch_related` on heavy list endpoints once correctness issues are resolved.

> **Note for future droids**: The above outlines the immediate defects; feel free to expand with performance instrumentation, schema evolution, or stricter permission policies once the core issues are fixed.
