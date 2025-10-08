# Issue 4 ➜ Issue 5 Handover

## Current Status (Issue 4)
- Finance projection is complete: `FactHarvest`, `IntercompanyPolicy`, and `IntercompanyTransaction` models include history tracking, indexes, and admin registrations.
- `finance_project` command materializes harvest lots into facts, caches dimension lookups, and raises intercompany transactions when configured policies exist.
- Tests in `apps.finance.tests.test_finance_project` cover fact creation, idempotent reruns, missing-destination skips, and intercompany detection.
- Migration `apps/finance/migrations/0002_intercompanypolicy_historicalintercompanytransaction_and_more.py` is generated; apply with `python manage.py migrate` before manual QA.
- OpenAPI now documents harvest read-only endpoints; finance APIs are still pending (Issue 5 scope).

## Repo & Branch Notes
- Working branch: `features/harvest-and-finance` (rebased onto `main` at session start).
- New/updated modules: finance models/admin, `utils/mapping.py`, `management/commands/finance_project.py`, associated tests, and migration `0002`.
- Harvest API router now installs under `/api/v1/operational/`; ensure no duplicate prefixes when adding finance endpoints.
- No additional migrations beyond finance `0002`; confirm `python manage.py showmigrations finance` reflects it as applied.

## Environment & Testing
- Default Postgres host is `timescale-db`; override with `DB_HOST=localhost` when running commands outside Docker.
- Verified via `DB_HOST=localhost python manage.py test apps.finance.tests` (passes; TimescaleDB warnings expected locally).
- Supporting commands:
  ```bash
  python manage.py finance_sync_dimensions
  python manage.py finance_project --from=YYYY-MM-DD --to=YYYY-MM-DD
  ```
- After schema or router changes, regenerate OpenAPI using `python manage.py spectacular --file api/openapi.yaml --validate --fail-on-warn`.

## Issue 5 Scope Recap
- Build read-only finance APIs (GitHub Issue 58) exposing facts, policies, and transactions with AND-combined filters, pagination, and RBAC alignment.
- Serializer/viewset patterns should mirror harvest APIs; leverage projection indexes for filtering (`event_date`, `dim_company`, `product_grade`, `state`).
- Reference docs: finance-harvest design spec, Issue 1 ADR §5 implementation sketch, API standards, and existing projection tests for field expectations.

## Recommended Next Steps
1. Re-read context pack plus Implementation Plan Issue 5 section to confirm acceptance criteria.
2. Scaffold finance API module (serializers, filters, viewsets, routers) following kebab-case basenames and read-only mixins.
3. Implement `select_related`/`prefetch_related` to avoid N+1 lookups when listing facts and intercompany transactions.
4. Add API tests covering pagination, filter combinations, permissions, and empty-state behavior.
5. Regenerate OpenAPI and rerun focused suites (`apps.finance.tests` + new API tests); capture commands in PR notes.

## Risks & Watch-outs
- Keep finance endpoints strictly read-only until later issues unlock mutations.
- Ensure router inclusion does not collide with existing operational paths.
- Projection must remain idempotent—rerun `finance_project` after modifying policies or lot fixtures before capturing API responses.
- Mind policy coverage: intercompany transactions only arise when both geography and subsidiary mappings exist.
