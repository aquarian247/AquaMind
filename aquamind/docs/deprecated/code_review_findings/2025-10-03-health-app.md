## Health App Code Review Findings

### Overview
- Focus: `apps.health` models, serializers, and viewsets with emphasis on mortality, lice count, treatment, sampling, and lab sample flows.
- Method: static review of modularized code, mixins, and tests under `apps/health/tests`.

### High-Risk Issues
1. **Mortality Viewset/User Assignment Conflict**  
   - `MortalityRecordViewSet` inherits `UserAssignmentMixin`, yet `MortalityRecord` has no `user` field. Any create request raises `TypeError("got an unexpected keyword argument 'user'")`.  
   - Filter overrides reference nonexistent fields (`mortality_date`, `recorded_by`), invoking `FieldError` during list queries.  
   - *Mitigation*: remove `UserAssignmentMixin` or extend the model to support `recorded_by`; scrub the override to filter only on actual fields (`event_date`, `batch_id`, `container_id`). Add integration tests covering POST and filtered GET requests.

2. **Lice Count/Treatment Filtering on Absent Columns**  
   - `LiceCountViewSet` filters on `batch_container_assignment`, `fish_count`, and `lice_count` fields that do not exist; `TreatmentViewSet` filters on `withholding_end_date`, which is a property. Each leads to `FieldError` on querystring usage.  
   - *Mitigation*: align `filterset_fields` and manual filters with concrete model fields (e.g., use `batch_id`, `container_id`, computed annotations). Add serializer-level validations or query param schema updates.

3. **Health Sampling Aggregates and Serializer Robustness**  
   - `HealthSamplingEventSerializer` accepts `individual_fish_observations` as raw dicts, bypasses validation, and suppresses `calculate_aggregate_metrics` during POST, leaving persisted stats stale.  
   - The model’s `calculate_aggregate_metrics` embeds test-specific branches (`sorted(weights) == [...]`) causing misleading results in production.  
   - *Mitigation*: convert list field to nested serializer, validate parameter IDs eagerly, remove hard-coded std-dev shortcuts, and recalc aggregates after creation. Backfill metrics with a data migration or management command.

4. **HealthLabSample Assignment and Error Messaging**  
   - Validation ignores `departure_date`, allowing samples to attach to inactive assignments; error responses mix string and dict formats, complicating API consumers.  
   - *Mitigation*: enforce upper bound check against `assignment.departure_date` and normalise all `ValidationError` payloads. Expand tests to cover historical assignment edge cases.

5. **Serializer Field Requirements**  
   - `MortalityRecordSerializer` and `LiceCountSerializer` flag `container` as required although models allow null, rejecting legitimate submissions.  
   - *Mitigation*: mark those `PrimaryKeyRelatedField`s as `required=False, allow_null=True` and assert behaviour with unit tests.

### Test Coverage Gaps
- API tests rely on setup print statements and miss the failure paths above; viewset mixins are untested.  
- *Mitigation*: add regression tests that POST/GET via DRF client with problematic parameters, and spinning up targeted serializer tests for aggregation workflows.

### Follow-Up Opportunities
- Introduce DRF filtersets (e.g., via `django-filter` classes) to centralise request validation.  
- Consider data integrity constraints (unique-together, soft-deletes) across health sampling tables for calmer downstream analytics.  
- Draft observability tasks (logging/auditing) once critical blockers are cleared.

---
Prepared by: Droid code review agent (Factory)
