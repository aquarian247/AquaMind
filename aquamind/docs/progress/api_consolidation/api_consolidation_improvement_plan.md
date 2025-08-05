# AquaMind API Consolidation Improvement Plan

## Overview
This plan addresses the API structure inconsistencies identified in the "AquaMind Django REST API Structure Analysis Report.md" and "scenario_integration_tests_todo.md", focusing on router registration, basename usage, namespace issues, testing URL construction, and related problems. The goal is to standardize the API for consistency, maintainability, and reliable contract synchronization (e.g., OpenAPI.yaml generation and Schemathesis validation), while unblocking skipped tests (e.g., the 7 scenario integration tests).

The plan is structured as **phases**, each designed for a single agent session (using Claude 4 Opus via factory.ai, handling the backend repo). Phases are scoped to 3-5 focused steps to leverage agent strengths (sophisticated refactoring, adherence to DRF best practices) while mitigating weaknesses (tendency to overlook global impacts or create incomplete fixes). Work exclusively on the backend repo (https://github.com/aquarian247/AquaMind).

**Key Principles for Agent Alignment**:
- **Incremental Implementation**: Fix and test small chunks to prevent widespread breakage or debug hell.
- **Explicit QA Focus**: Every phase ends with validation (e.g., Schemathesis, coverage checks, test runs); agents must not proceed without verifying no regressions.
- **Reference Documents**: In each phase, reference relevant sections from provided docs (e.g., api_contract_synchronization.md for spec regen, testing_guide.md for Schemathesis/commands, scenario_integration_tests_todo.md for skipped tests) to ground agents without overload.
- **Prompt/Context Engineering**: Treat each phase as a self-contained prompt: Start sessions by copying the phase description verbatim, then provide repo access and prior phase outputs.
- **Session Termination**: End each session immediately after running and verifying QA steps—no further work.
- **Coverage Tooling**: Use `coverage run --source='.' manage.py test && coverage report` for backend (per testing_guide.md). Run Schemathesis with 10 examples, hooks, and flags.
- **Agent Guidelines Summary**: Include this at session start: "Prioritize consistent DRF patterns (explicit basenames, clean routers). No duplicates—implement meaningful fixes. Run Schemathesis and tests incrementally; fix failures before completing. Reference api_contract_synchronization.md for any spec changes."
- **Tools & Environment**: Assume factory.ai has repo access.

**Git/GitHub Approach**: Merge the existing QA improvement PR/branch now (if stable and tests pass), as it's only ~25% done and provides a clean baseline. Create a new branch `api-consolidation` from main for this project—keep it separate to avoid entangling API fixes with ongoing QA work. Final merge via one PR after all phases.

**Success Metrics**: No router conflicts, 100% basename consistency, all skipped tests (e.g., 7 in scenario) enabled and passing, Schemathesis clean (no 404 noise). If issues arise (e.g., breaking changes), use API versioning (/v2/) as fallback.

## Phase 1: Audit Current State and Fix Router Duplication
This phase assesses the router setup and removes duplications to eliminate conflicts and Schemathesis noise; reference the report's "Router Registration Issues" and TODO's "Double Registration" example.

Reference documents & sections:
* `docs/progress/api_consolidation/AquaMind Django REST API Structure Analysis Report.md` → "Router Registration Duplication" (shows `router.registry.extend` and duplicate `path()` includes).
* `docs/progress/api_consolidation/scenario_integration_tests_todo.md` → "Router Registration Problems" (bullets 1-3) for concrete failure context.
* `docs/quality_assurance/testing_guide.md` → Section 3 "Running Tests" for commands; Section 4 for Schemathesis invocation.
* `README.md` → "Getting Started / Installation" for quick local run.

1. Check the status of the repo (per README.md).
2. Run `python manage.py show_urls` to document current URL patterns; identify duplicates/conflicts (e.g., from registry extend + path includes in aquamind/api/router.py).
3. Update aquamind/api/router.py to use clean path includes only (remove registry.extend calls; add consistent namespaces like namespace='api' per TODO Option A).
4. Commit to `api-consolidation` branch with message "Phase 1: Router audit and duplication fix".
5. **QA Steps**: Run full tests (python manage.py test), Schemathesis (per testing_guide.md: generate token, 10 examples), and `python manage.py show_urls` to verify no duplicates/404 noise. Enable and run the 7 skipped scenario tests (per scenario_integration_tests_todo.md) if fixed; document coverage delta. **End session here after QA passes.**

## Phase 2: Standardize Basename Usage Across Apps
Focus on adding explicit basenames to prevent naming collisions; reference report's "Inconsistent Basename Usage" examples and kebab-case convention.

Reference documents & sections:
* `docs/progress/api_consolidation/AquaMind Django REST API Structure Analysis Report.md` → "Inconsistent Basename Usage" list and code snippets.
* `docs/quality_assurance/code_organization_guidelines.md` → "Django-Specific Organization → Views and ViewSets" for ordering & naming; also general kebab-case advice.
* `docs/architecture.md` → "API Contract Synchronization" table stressing spec generation importance—basenames must be stable for OpenAPI.

1. For each app (batch, infrastructure, health, etc.), update api/routers.py to use explicit basenames (e.g., router.register(r'species', SpeciesViewSet, basename='species')).
2. Ensure kebab-case consistency (e.g., 'batch-composition') and uniqueness project-wide.
3. Update any affected tests/reverse() calls to match new basenames.
4. Commit to `api-consolidation` branch with message "Phase 2: Basename standardization".
5. **QA Steps**: Run full tests, Schemathesis (10 examples), and coverage report. Verify no naming errors in OpenAPI gen (regenerate yaml per api_contract_synchronization.md if needed). Enable/run skipped scenario tests if impacted. **End session here after QA passes.**

## Phase 3: Centralize Testing Utilities and Migrate Tests
Implement shared helpers to eliminate duplication; reference report's "Standardized Testing URL Construction" proposal and TODO's isolation fixes (e.g., transaction.atomic()).

Reference documents & sections:
* `docs/progress/api_consolidation/AquaMind Django REST API Structure Analysis Report.md` → "Testing Approach Consistency" & "Duplicated Helper Functions".
* `docs/quality_assurance/testing_guide.md` → Section 2 (Directory Layout) & Section 3 (Running Tests) for placement and commands.
* `docs/progress/api_consolidation/scenario_integration_tests_todo.md` → "Additional Test Isolation Issues" for concrete fixes needed.

1. Create tests/utils/api_helpers.py with APITestHelper (including get_api_url and get_named_url methods per report example).
2. Create tests/base.py with BaseAPITestCase (extending APITestCase, force_authenticate).
3. Migrate high-priority app tests (e.g., batch, environmental, scenario) to use the new helpers; fix scenario isolation issues (e.g., unique data, missing fields like scenario.species).
4. Commit to `api-consolidation` branch with message "Phase 3: Centralized testing utils and migration".
5. **QA Steps**: Run full tests and coverage (target no drop). Run Schemathesis; enable/run all 7 skipped scenario tests (update with new utils). Document any fixed isolation violations. **End session here after QA passes.**

## Phase 4: Add Namespace Fixes and Enhance Contract Testing
Resolve 'api' namespace errors to unblock skipped tests; reference TODO's Option A and report's "Enhanced Schemathesis Integration".

Reference documents & sections:
* `docs/progress/api_consolidation/scenario_integration_tests_todo.md` → "API Namespace Issues" section for failing reverse lookups.
* `docs/api_contract_synchronization.md` → Sections 2 & 4 (Automatic Flow and Contract Testing Quick-Ref) for spec sync flow and Schemathesis flags.
* `docs/progress/api_consolidation/AquaMind Django REST API Structure Analysis Report.md` → "Enhanced Schemathesis Integration" recommendations.

1. Update aquamind/api/router.py to add namespace='api' to all path includes (e.g., path('batch/', include((batch_router.urls, 'batch'), namespace='api'))).
2. Update affected tests (e.g., scenario integration) to use reverse('api:...') consistently.
3. Implement new contract tests in tests/contract/ (e.g., test_api_contract_compliance per report example; add test_all_endpoints_documented).
4. Commit to `api-consolidation` branch with message "Phase 4: Namespace fixes and contract enhancements".
5. **QA Steps**: Run full tests, Schemathesis (10 examples, verify no namespace errors), and coverage. Confirm all 7 scenario integration tests pass. Regenerate openapi.yaml (per api_contract_synchronization.md) and test frontend sync simulation. **End session here after QA passes.**

## Phase 5: Final Polish, App Structure Standardization
Standardize app structures and decide on operational app; reference report's "Standard App API Structure".

Reference documents & sections:
* `docs/progress/api_consolidation/AquaMind Django REST API Structure Analysis Report.md` → "Standard App API Structure" & "Implementation Priority".
* `docs/quality_assurance/code_organization_guidelines.md` → Entire doc for file size, directory conventions.
* `docs/architecture.md` → "Component Architecture" for official app responsibilities, ensuring directories align.

1. For each app, enforce standard API dir structure (api/routers.py, api/viewsets.py, etc.; add linter checks if possible).
2. Update docs (e.g., testing_guide.md with new utils) and add monitoring (e.g., GitHub Action for OpenAPI validation on PRs).
3. Commit to `api-consolidation` branch with message "Phase 5: App structure polish".
4. **QA Steps**: Run full tests, Schemathesis, and coverage (aim for 80%+ in affected apps). Verify no regressions in skipped tests or contract sync. If changes affect API, regenerate yaml and document. Merge `api-consolidation` to main after verification. **End session here after QA passes; project complete.**

## Progress Tracking

### Phase 1: Audit Current State and Fix Router Duplication
**Started:** August 5, 2025

**Current Status:** In progress

**Findings:**
- Confirmed router duplication issue in `aquamind/api/router.py` where the main router both extends the registry using `router.registry.extend()` AND includes URLs explicitly with `path()` statements
- This dual approach is causing duplicate URL patterns and conflicts
- The issue is exactly as described in the API Structure Analysis Report under "Router Registration Duplication"
- This duplication is likely causing the "404 noise" in Schemathesis tests and conflicts in URL resolution

**Next Steps:**
- Update `aquamind/api/router.py` to use clean path includes only
- Remove all `router.registry.extend()` calls
- Add consistent namespaces to path includes
