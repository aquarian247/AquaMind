## AquaMind Backend - Code Health Remediation Plan (Post-Maintenance)

Date: 2025-09-14 (UTC)
Scope: Django apps under `apps/` (exclude `operational` for business KPI experiments unless stated).
Goal: Reduce complexity hotspots, raise Maintainability Index, and stabilize business logic with tests.

### Guiding Principles
- Keep tasks session-sized and self-contained to avoid context rot.
- Prefer extraction and composition over wholesale rewrites.
- Add or update tests as you refactor; behaviour must remain stable.
- Gate regressions with lightweight CI checks (changed files only).

### Targets Identified (from METRICS_REPORT_AFTER)
- Highest CC functions: validation/aggregation in `batch`, `inventory`, `infrastructure` command.
- Worst MI files: `scenario/api/serializers.py`, `inventory/services/fcr_service.py`, `operational/services/fcr_trends_service.py`.
- Cognitive complexity concentration: `batch` serializers and viewsets.

---

### Task 1 — Extract validators in `batch/api/serializers/growth.py`
- Outcome: Split `validate` into small pure helpers; CC ≤ 12.
- Steps: Create `validators/growth_validation.py`; move per-field checks; import into serializer.
- Acceptance: Unit tests pass; snapshot of error messages unchanged.

### Task 2 — Refactor `inventory/services/fcr_service.py` (phase 1)
- Outcome: Separate data access, aggregation, and formatting into modules.
- Steps: Create `services/fcr/` package with `io.py`, `aggregate.py`, `formatting.py`; move non-IO helpers.
- Acceptance: File LOC reduced; MI ≥ 45; service API unchanged.

### Task 3 — Refactor `inventory/services/fcr_service.py` (phase 2: tests)
- Outcome: Add unit tests for aggregation helpers (no DB hits).
- Steps: Parametric tests for edge cases; validate numeric stability.
- Acceptance: >15 test cases added; coverage for helpers ≥ 80%.

### Task 4 — Split `infrastructure/management/commands/validate_openapi.py` checks
- Outcome: Extract `validate_response_codes` and related checks into `validators.py`.
- Steps: Introduce mapping tables; prefer early returns.
- Acceptance: Top CC ≤ 12; command behaviour unchanged; add 6 tests for common failure modes.

### Task 5 — Lower cognitive complexity in `batch/api/serializers/transfer.py`
- Outcome: Isolate transformation logic in `serializers/utils_transfer.py`.
- Acceptance: Most CCR findings resolved; maintain field-level validations.

### Task 6 — Normalize `batch/views.py` hotspots (`merge_batches`)
- Outcome: Extract orchestration into service layer; keep view lean.
- Acceptance: View CC ≤ 10; add service tests for merge scenarios.

### Task 7 — Improve MI for `scenario/api/serializers.py`
- Outcome: Move large schema/validation structures into modules; document types.
- Acceptance: MI ≥ 35; serializers split logically; import paths stable.

### Task 8 — Stabilize `operational/services/fcr_trends_service.py`
- Outcome: Extract `_get_*series` helpers into dedicated module; add deterministic tests.
- Acceptance: Top CC ≤ 12; unit tests cover typical and empty datasets.

### Task 9 — Introduce CI gates on changed files (radon/flake8 CCR)
- Outcome: Warn on CC ≥ 15, MI < 50, and CCR occurrences in changed files.
- Steps: Add lightweight script in `scripts/` and GitHub Action; PR comment summary.
- Acceptance: Pipeline runs on PRs; non-blocking warnings displayed.

### Task 10 — Type hints and docstrings for extracted helpers
- Outcome: Improve readability and static tooling.
- Acceptance: No mypy errors in helpers; concise docstrings added.

### Task 11 — Micro-optimizations: `.select_related`/`.prefetch_related`
- Outcome: Ensure refactors do not regress query counts.
- Acceptance: Add 3 tests asserting query caps for common endpoints.

### Task 12 — Documentation updates
- Outcome: Update `docs/development/aggregation_playbook.md` with new service boundaries.
- Acceptance: Diagrams/sections reflect `fcr_service` restructuring.

---

Execution Notes
- Run tasks independently; avoid cross-branch refactors.
- Record completions in the progress log with ISO dates per the Implementation Progress Tracking Rule.
