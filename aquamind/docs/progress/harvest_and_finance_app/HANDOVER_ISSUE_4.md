# Issue 3 ➜ Issue 4 Handover

## Current Status (Issue 3)
- Finance domain scaffolded under `apps.finance` with `DimCompany` and `DimSite` models, admin registrations, and management command wiring.
- Migration `finance/0001_initial.py` created and applied via `python manage.py migrate finance` (DB_HOST=localhost); rollback verified by Django auto-generation.
- Idempotent sync implemented in `finance_sync_dimensions`; `display_name` derived as `{subsidiary}-{geography.name}`; subsidiaries sourced from `users.models.Subsidiary`.
- Targeted test suite `python manage.py test apps.finance.tests.test_finance_sync_dimensions` passes; full project suite (1008 tests) confirmed green by previous agent.

## Repo & Branch Notes
- Working branch: `features/harvest-and-finance` (diverged from `main`).
- New app paths: `apps/finance/` (models, admin, management command, tests, migrations).
- Settings updated to include `apps.finance` in `INSTALLED_APPS`.
- No OpenAPI changes for finance yet; harvest OpenAPI diffs remain from Issue 2 work (pending regeneration once finance APIs land).

## Environment & Data
- Run migrations against local Postgres (set `DB_HOST=localhost` when not using docker-compose).
- Management command usage: `python manage.py finance_sync_dimensions` (idempotent; safe to re-run).
- Command populates `DimCompany` rows for every Geography × {Freshwater, Farming} pair, even if no infra sites exist yet.

## Acceptance Criteria Review (Issue 3)
- ✅ Tables created/applied (`DimCompany`, `DimSite`).
- ✅ Sync idempotency verified through dedicated tests.
- ✅ Every `DimSite` binds to an existing `DimCompany` (enforced + tested).
- ✅ At least one `DimCompany` per geography (command ensures coverage; tests assert presence).
- ✅ Nullable finance fields (`currency`, `nav_company_code`) accepted (no non-null constraint).
- ✅ Test coverage for first-run insert, rerun stability, and mapping integrity.

## Recommended Next Steps (Issue 4 Scope)
1. Re-read `03_finance_app_dimensions_and_mapping.md` §6 and `IMPLEMENTATION_PLAN.md` for projection details.
2. Design `FactHarvest` model + intercompany policy/transaction scaffolding under `apps.finance` (or dedicated app if spec dictates).
3. Implement projection CLI (likely `finance_project`) that materializes fact rows, detecting intercompany transfers when geography/subsidiary keys diverge.
4. Ensure projection respects idempotency (replace/update existing fact rows) and defers pricing mechanics per ADR.
5. Expand tests to cover projection runs, intercompany detection logic, and rollback scenarios.
6. Once projection ready, regenerate OpenAPI if new endpoints are added in later issues.

## Risks & Watch-outs
- Fact table volume may require batching; align with TimescaleDB warnings seen during tests (extension disabled locally).
- Maintain read-only separation: operational models must not depend on finance dims.
- Keep subsidiaries enumeration in sync; extend command/tests if new subsidiaries introduced.

## References
- Context Pack docs in `docs/progress/harvest_and_finance_app/` plus ADR §5 implementation sketch.
- Tests: `apps.finance.tests.test_finance_sync_dimensions` (use as template for projection scenarios).
