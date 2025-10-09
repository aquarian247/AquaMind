# Issue 5 ➜ Issue 6 Handover

## Current Status (Issue 5)
- Finance read APIs are live under `/api/v1/finance/` with two read-only viewsets: `facts/harvests` and `intercompany/transactions`.
- Serializers now emit nested summaries for companies, sites, product grades, and policies via dedicated serializers; openapi schema validates without warnings.
- Custom `FinancePagination` (100 default / 500 max) is applied to both endpoints; ordering supported on `event_date`, `posting_date`, `fact_id`, and `tx_id`.
- Permission layer uses `IsFinanceUser` (FINANCE or ADMIN roles, plus superusers) chained with `IsAuthenticated`.
- Tests (`tests/api/test_finance_read_apis.py` + `apps.finance.tests`) pass, covering RBAC, filters, ordering, pagination, and write-method rejection.
- `api/openapi.yaml` regenerated successfully with `python manage.py spectacular --file api/openapi.yaml --validate --fail-on-warn`.

## Repo & Branch Notes
- Active branch: `features/harvest-and-finance` (still diverged from `main`; keep rebasing regularly).
- New finance API package structure: `apps/finance/api/{serializers,filters,permissions,viewsets,pagination}.py` plus `apps/finance/api/routers.py` and `__init__` exports.
- `aquamind/api/router.py` now includes the finance router (`/api/v1/finance/`).
- Serializer refactor introduced nested summary serializers re-used across facts and transactions.
- No database migrations in Issue 5; models remain as delivered in Issue 4.

## Environment & Testing
- Local DB host override: prepend commands with `DB_HOST=localhost` outside Docker.
- Key commands already executed and green:
  ```bash
  DB_HOST=localhost python manage.py test apps.finance.tests tests.api.test_finance_read_apis
  DB_HOST=localhost python manage.py spectacular --file api/openapi.yaml --validate --fail-on-warn
  ```
- Expect TimescaleDB warnings about hypertables when running tests locally; safe to ignore.

## Issue 6 Scope Recap
- Deliver NAV export skeleton (GitHub Issue 59): batch pending `IntercompanyTransaction` rows into journal files.
- Core deliverables: `NavExportBatch` / `NavExportLine` models + migrations, export service to assemble lines & mark transactions `exported`, CSV generator, and read/write endpoints (`POST /api/v1/finance/nav-exports/`, `GET /api/v1/finance/nav-exports/{id}/download`).
- RBAC remains FINANCE/ADMIN only; enforce idempotency guard (duplicate filter sets should 400 unless `force=true`).
- OpenAPI + API regression suite must cover new endpoints; update design spec NAV section and master plan checkbox when done.

## Recommended Next Steps
1. Rebase `features/harvest-and-finance` onto latest `main`; rerun targeted finance tests after rebase.
2. Read context pack docs plus `06_nav_export_skeleton.md` to align on CSV schema and state transitions.
3. Model layer: add `NavExportBatch`/`NavExportLine` with historical tracking, uniqueness on `(batch, document_no)`, and helper manager for pending transactions.
4. Implement export service (`create_export_batch`, `generate_csv`) and unit tests; ensure transactions transition to `exported` within a queryset update/transaction block.
5. Build viewset/serializer layer (likely `GenericViewSet` + mixins) with POST for batch creation and GET for streaming CSV; register router `finance-nav-exports` under finance API.
6. Regenerate OpenAPI, run finance + export tests, and capture commands for the eventual PR description.
7. Update documentation: design spec NAV section, Implementation Plan checkmark for Issue 6, and append this handover link in Issue 6 PR template.

## Risks & Watch-outs
- **Idempotency**: ensure duplicate export requests reject unless force flag supplied; consider unique constraint on `(company, date_from, date_to)` or service-level lock.
- **State management**: mark transactions as `exported` only after batch + lines persist; wrap in atomic transaction.
- **CSV fidelity**: match column order and headers exactly per spec to avoid downstream NAV ingestion issues; unit-test CSV output.
- **File size**: use `StreamingHttpResponse` for downloads to prevent memory spikes on large batches.
- **Permissions**: reuse `IsFinanceUser`; confirm non-finance users still receive 403 for new endpoints.

Keep this branch focused on Issue 6 scope; defer NAV transport integrations or FX handling to later issues.
