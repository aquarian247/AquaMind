# Debugging Handoff — Harvest & Finance Backend Changes

## 1. Context
- Backend repo: `/Users/aquarian247/Projects/AquaMind`
- Branch: `features/harvest-and-finance`
- Recent backend session focused on deprecating Schemathesis, rewriting docs, and updating migrations/tests for Issue 7 & 8.

## 2. Outstanding Backend Findings
1. **Contract Test Import Error**
   - `tests.contract.test_api_contract` still imports `ScenarioViewSet` from `apps.scenario.api.viewsets`, which no longer exports that symbol.
   - Action: Update/replace the contract test import or adjust the viewset module.
2. **Playwright Dependency Missing**
   - `tests/test_django_admin_playwright.py` fails with `ModuleNotFoundError: playwright` when running backend test suite.
   - Action: Install Playwright dependencies or skip this suite when Playwright isn’t available.
3. **BI View Tests vs SQLite**
   - After guarding migration `finance.0004_bi_delivery_views`, SQLite skips creating the views/indexes. `apps.finance.tests.test_bi_views` now fail under `settings_ci` because the views don’t exist.
   - Action: add SQLite skip guards to those tests or provide SQLite-compatible view definitions for CI runs.

## 3. Validation Performed
- `python manage.py test` (Postgres) runs to completion with the two errors above (contract & Playwright).
- `python manage.py test --settings=aquamind.settings_ci` now finishes with the same errors plus the BI view failures (see item 3).

## 4. Suggested Next Session Steps
1. Decide on the approach for contract tests (either fix imports or retire Schemathesis-era suite).
2. Install or gate Playwright-based admin test.
3. Resolve finance BI view tests for SQLite (skip or emulate views).
4. Re-run both test commands; ensure API regression suite still green.
5. Once clean, update progress docs & implementation plan for Issue 8.

## 5. References
- Backend testing guide: `aquamind/docs/quality_assurance/testing_guide.md`
- Finance BI views migration: `apps/finance/migrations/0004_bi_delivery_views.py`
- API regression tests: `tests/api/`
- BI view tests: `apps/finance/tests/test_bi_views.py`

