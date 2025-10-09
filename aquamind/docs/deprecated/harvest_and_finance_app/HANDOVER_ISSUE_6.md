# Issue 6 ➜ Issue 7 Handover

## Summary
- NAV export skeleton delivered: `NavExportBatch`/`NavExportLine` models with history, idempotent service layer, CSV streaming endpoints, and finance router wiring.
- Finance permissions enforced across the new POST/GET endpoints; duplicate requests guarded by `force=true` toggle.
- CSV output verified against spec headers and amounts; account numbers sourced from `NAV_ACCOUNT_MAP` placeholders.

## Code Highlights
- Models & migrations: `apps/finance/models.py`, migration `0003_navexportbatch_navexportline_historicalnavexportline_and_more.py`.
- Service API: `apps/finance/services/export.py` exposed via `create_export_batch`/`generate_csv` helpers.
- Viewset + serializers: `NavExportBatchViewSet` with CSV download action under `/api/v1/finance/nav-exports/`.
- Tests: `apps/finance/tests/test_nav_export_service.py` and `tests/api/test_finance_nav_exports.py` cover batching, force overwrite, download, and RBAC.

## Verification
- `DB_HOST=localhost python manage.py test apps.finance.tests tests.api.test_finance_nav_exports tests.api.test_finance_read_apis`
- `DB_HOST=localhost python manage.py spectacular --file api/openapi.yaml --validate --fail-on-warn`

## Known Follow-Ups (Issue 7 Seeds)
- Finance have to supply definitive NAV account/catalog codes to replace placeholder entries in `NAV_ACCOUNT_MAP`.
- Monitor CSV size in downstream environments; consider S3/offline storage story when moving beyond skeleton.
- Begin planning Issue 7 scope (likely transport/upload layer): confirm delivery mechanism (SFTP/API) and retry semantics.

## Suggested Next Steps for Issue 7 Droid
1. Review business spec updates for NAV transport (docs/progress/harvest_and_finance_app/07_nav_transport.md once available).
2. Evaluate export persistence: decide whether to store generated CSV for audit or regenerate on demand.
3. Prototype integration adapter (SFTP or API) with configuration-driven endpoints; reuse `NavExportBatch` state machine (`draft`/`exported` → `sent`).
4. Extend tests to cover transport failure handling and retry/backoff policy.
