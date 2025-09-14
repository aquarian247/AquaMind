# Backend Maintainability Improvement Plan

Date: 2025-09-14 (UTC)

Working mode
- Single feature branch for ALL phases: `feat/backend-maintainability-plan`
- One PR at the very end after all issues are completed and validated
- Keep branch rebased; no partial PRs

Baseline & scope
- Goal: lower cyclomatic/cognitive complexity, improve MI, and resolve analyzer blockers
- Exclude `operational` app from refactors (per metrics scope)
- Baseline artifacts: `aquamind/docs/metrics/*.json`, `aquamind/docs/METRICS_REPORT.md`

Session protocol (apply in every phase)
1) Read these docs first:
   - `aquamind/docs/quality_assurance/code_organization_guidelines.md`
   - `aquamind/docs/quality_assurance/api_standards.md`
   - App-specific docs under `aquamind/docs/progress/*` when touching those modules
2) Verify OpenAPI alignment (`api/openapi.yaml`)
3) Run metrics (radon CC/MI/Halstead/raw + flake8 cognitive) before/after changes
4) Keep changes scoped; add unit tests for extracted helpers

Targets
- MI > 50 for touched files (where feasible)
- CC < 15 per function; reduce cognitive complexity hotspots
- No analyzer errors (e.g., BOMs)

Phases (each sized for a single agent session)

Phase 1 — Fix analyzer blockers and quick wins
- Remove BOM (U+FEFF) from `apps/environmental/api/viewsets.py`
- Address trivial complexity in small hotspots (1–3-line early returns)
- Acceptance: radon/flake8 run clean (no parse errors); no behavior changes

Phase 2 — Extract validation helpers from complex serializers
- Targets:
  - `apps/batch/api/serializers/growth.py` (method `_process_individual_measurements`, CC=24)
  - `apps/batch/api/serializers/composition.py` (validate, CC≈20)
  - `apps/batch/api/serializers/transfer.py` (validate, CC≈17)
- Approach: move cross-field checks into private helpers; use guard clauses
- Acceptance: CC < 15 for these methods; serializer API unchanged; tests added/updated

Phase 3 — Decompose `batch/api/viewsets.py`
- Problem: low MI (≈35.95) and mixed responsibilities
- Approach: split by resource into multiple files or adopt mixins; isolate filter logic
- Acceptance: MI improves (>50 target); routes unchanged; tests green

Phase 4 — Simplify inventory FCR service ✅ COMPLETED
- File: `apps/inventory/services/fcr_service.py` (low MI; multiple CC spikes)
- Approach: separate IO from computation; extract pure functions; early returns
- Acceptance: key functions CC < 15; service behavior verified with unit tests
- **COMPLETED**: Extracted 8 pure helper functions, reduced complexity from C/D to A/B ratings, MI improved to A, all tests passing

Phase 5 — Scenario calculations complexity reduction ✅ COMPLETED
- Files: `apps/scenario/services/calculations/*` (projection_engine, fcr_calculator, mortality_calculator, tgc_calculator)
- Approach: extract algorithmic steps into named helpers; annotate types; reduce nesting
- Acceptance: largest functions CC < 15; tests for new helpers; outputs invariant
- **COMPLETED**: Extracted 4 helper methods from run_sensitivity_analysis (CC 17→4), added 14 unit tests, all functions CC < 15, MI maintained, 145 tests pass

Phase 6 — Introduce metrics guardrails in CI (warn-only) ✅ COMPLETED
- Add radon/flake8-cognitive steps; export JSON/text artifacts; document thresholds
- Acceptance: CI publishes CC/MI/Cognitive tables; no blocking yet
- **COMPLETED**: Added radon (6.0.1) and flake8-cognitive-complexity to requirements.txt, created CI scripts (run_radon_metrics.py, run_cognitive_metrics.py), integrated into GitHub Actions workflow, created comprehensive documentation (CI_METRICS_THRESHOLDS.md, CI_METRICS_REMEDIATION_WORKFLOW.md), tested pipeline locally - all artifacts generated successfully

GitHub issues (one per phase)

Issue 1
- Title: Backend: Resolve analyzer blockers and quick complexity wins (environmental BOM)
- Body:
  Summary
  - Remove U+FEFF from `apps/environmental/api/viewsets.py`; fix minor complexity with guard clauses.

  Outcomes
  - Metrics tools parse all files; baseline CC/MI established.

  Steps
  - Strip BOM; run radon/flake8-cognitive; commit without behavior changes

  Acceptance
  - No parse errors; tests unchanged and passing.

  References
  - `aquamind/docs/METRICS_REPORT.md`, metrics JSON

Issue 2
- Title: Backend: Extract serializer validation helpers (batch serializers)
- Body:
  Summary
  - Reduce CC in `growth.py`, `composition.py`, `transfer.py` by moving checks to helpers.

  Outcomes
  - CC < 15; serializer interfaces unchanged; tests added for helpers.

  Steps
  - Identify logical groups of checks; extract
  - Add unit tests; run radon/flake8-cognitive

  Acceptance
  - CC targets met; tests pass.

  References
  - `aquamind/docs/quality_assurance/code_organization_guidelines.md`

Issue 3
- Title: Backend: Decompose batch/api/viewsets.py and isolate filters
- Body:
  Summary
  - Split viewsets by resource or move shared logic into mixins; isolate filtering.

  Outcomes
  - MI improves (>50 target); route behavior unchanged.

  Steps
  - Identify boundaries; create files/mixins; update imports/routers
  - Run tests and radon; verify openapi matches

  Acceptance
  - MI increase; tests green; openapi unchanged.

  References
  - `aquamind/docs/progress/api_consolidation/api_consolidation_improvement_plan.md`

Issue 4
- Title: Backend: Simplify inventory FCR service (extract pure functions)
- Body:
  Summary
  - Separate IO from computation; add guard clauses; reduce nesting.

  Outcomes
  - CC < 15 for main functions; behavior verified by tests.

  Steps
  - Extract compute steps; add unit tests
  - Run metrics; update docs if improved

  Acceptance
  - CC target met; tests pass.

  References
  - `apps/inventory/services/fcr_service.py`, metrics

Issue 5
- Title: Backend: Reduce complexity in scenario calculation engines
- Body:
  Summary
  - Extract algorithmic helpers in projection/tgc/mortality/fcr engines.

  Outcomes
  - CC < 15 for heavy functions; stronger unit tests.

  Steps
  - Identify hot functions; extract
  - Add tests; run metrics

  Acceptance
  - CC target met; tests pass.

  References
  - Metrics JSON; `apps/scenario/services/calculations/*`

Issue 6
- Title: Backend: Add metrics guardrails in CI (radon + cognitive, warn-only)
- Body:
  Summary
  - Publish CC/MI/Cognitive reports in CI; document remediation workflow.

  Outcomes
  - Continuous visibility; incremental improvement.

  Steps
  - Add scripts; wire to CI; document thresholds

  Acceptance
  - CI artifacts present; pipeline stable.

  References
  - `aquamind/docs/metrics/*`, `aquamind/docs/METRICS_REPORT.md`

## Completed Milestones

### 2025-09-14 - Phase 6: Metrics Guardrails in CI
- **Milestone**: Successfully implemented comprehensive CI metrics collection system
- **Implementation Details**:
  - Added radon 6.0.1 and flake8-cognitive-complexity to requirements.txt for automated metrics analysis
  - Created `scripts/run_radon_metrics.py` for collecting CC, MI, Halstead, and raw metrics with JSON artifacts
  - Created `scripts/run_cognitive_metrics.py` for cognitive complexity analysis with text artifacts
  - Integrated metrics collection into GitHub Actions workflow (`.github/workflows/django-tests.yml`)
  - Developed comprehensive documentation including thresholds and remediation workflows
  - Tested pipeline locally ensuring all artifacts generate correctly
- **Key Technologies**: radon, flake8-cognitive-complexity, GitHub Actions, Python scripting
- **Outcome**: Continuous visibility into code quality trends with automated artifact generation for trend analysis
