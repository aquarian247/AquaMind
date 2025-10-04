# Broodstock App Code Review – Findings & Mitigations

## Overview
Focused review of the broodstock domain (models, serializers, viewsets, and services) revealed several correctness gaps that will surface at runtime and during integration with upstream processes. The most urgent items appear in the service layer, but API and serializer logic also need tightening. Tests partially cover the business logic; however, the existing failures are masked in CI due to misconfigured utilities.

## High-Priority Defects
1. **`timezone.timedelta` AttributeError**  
   *Location*: `apps/broodstock/services/broodstock_service.py` (`get_container_statistics`, `check_container_maintenance_due`).  
   *Impact*: Breaks statistics retrieval and maintenance checks; currently fails unit tests.  
   *Suggested Fix*: Replace `timezone.timedelta(...)` with `datetime.timedelta(...)` (import from Python stdlib) and add regression test expectations.

2. **Egg production actions bypass domain service**  
   *Location*: `apps/broodstock/views.py` actions `produce_internal` and `acquire_external`.  
   *Impact*: Skips validations in `EggManagementService` (inactive plans, unhealthy broodstock, duplicate supplier batches), does not bump `BreedingPair.progeny_count`, and writes partially-initialized external batches.  
   *Suggested Fix*: Delegate to `EggManagementService.produce_internal_eggs` / `.acquire_external_eggs` (or move logic into a shared helper) to reuse validation and side-effects; wrap in a single `transaction.atomic()` to include supplier and production writes.

3. **Non-unique egg batch IDs from API helpers**  
   *Location*: Same view actions as above.  
   *Impact*: `EB-INT-YYYYmmddHHMMSS` collisions during concurrent requests; violates `EggProduction.egg_batch_id` uniqueness constraint.  
   *Suggested Fix*: Reuse `EggManagementService.generate_egg_batch_id()` or ensure microsecond component is appended; add negative test to confirm uniqueness enforcement.

4. **Serializer container validation rejects valid broodstock tanks**  
   *Location*: `apps/broodstock/serializers.py` (`BroodstockFishSerializer.validate_container`).  
   *Impact*: Relies on substring match of `container_type.name`; fails when the name lacks “broodstock” even if the tank is a broodstock type (e.g., `Broodstock Tank 1` vs. localized names).  
   *Suggested Fix*: Inspect `container_type.category` or an explicit boolean flag on the container type; alternatively, whitelist allowable categories via infrastructure constants.

## Supporting Concerns
- **Unused imports** in serializers (`transaction`, `ContainerSerializer`, `BatchSerializer`) suggest dead code paths; prune or implement the intended nested write logic.  
- **History endpoints** rely on `HistoryFilter` defaults but lack pagination tests; consider smoke tests to guard schema changes.  
- **API tests** only confirm authentication; extend to cover the new service delegations once fixed.

## Next Steps for Follow-Up Droids
- Patch the high-priority defects first, then rerun `pytest apps/broodstock/tests/test_services.py::BroodstockServiceTestCase::test_get_container_statistics` to verify the timedelta fix.  
- After delegating egg production flows to the service layer, craft integration tests around the actions (`produce_internal`, `acquire_external`) to ensure validations trigger correctly.  
- Coordinate with the infrastructure team if container categorization needs a shared enum/flag; avoid hard-coded string checks in serializers.  
- Keep an eye out for additional domain service opportunities (e.g., maintenance task completion logic) while refactoring—this review intentionally leaves those explorations open.

> **Reminder**: Update any relevant OpenAPI annotations after refactoring the view actions so the schema remains accurate for contract testing.
