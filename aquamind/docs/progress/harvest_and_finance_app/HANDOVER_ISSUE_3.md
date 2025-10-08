# Issue 2 ➜ Issue 3 Handover

## Current Status (Issue 2)
- Harvest domain implementation is complete: app scaffold, models with history, admin, migrations, read-only serializers/viewsets, kebab-case routers, and OpenAPI regenerated.
- API contract covers `/api/v1/operational/harvest-events/` and `/api/v1/operational/harvest-lots/`; tests exist under `apps/harvest/tests/api/test_harvest_api.py`.
- Health sampling aggregation tests now pass after aligning sampling dates with assignments (`apps/health/tests/test_health_sampling_aggregation.py`).
- Targeted suite `python manage.py test apps.health.tests.test_health_sampling_aggregation` passes against SQLite; full suite still requires Postgres host `timescale-db` to be reachable.

## Repo & Branch Notes
- Working branch: `features/harvest-and-finance`.
- New migrations already in tree: `apps/harvest/migrations/0001_initial.py`; no additional migrations generated this session.
- Untracked project additions live under `apps/harvest/`; ensure they are staged before opening the Issue 2 PR.

## Environment & Testing
- Local Postgres connection string expects host `timescale-db`; set `DB_HOST=localhost` (or run via docker-compose) before executing the full test suite.
- When running tests on SQLite, remove `DATABASES['default']['OPTIONS']` or override via env to avoid `TypeError: 'options'`.
- Regenerate OpenAPI after further API work: `python manage.py spectacular --file api/openapi.yaml --validate --fail-on-warn`.

## Issue 3 Scope Recap
- Create new `apps.finance` domain with `DimCompany` and `DimSite` models plus admin registrations.
- Implement idempotent management command `finance_sync_dimensions` to upsert companies (geography × subsidiary) and sites (FreshwaterStation/Area → DimCompany).
- Tests must cover initial sync, re-run idempotency, and mapping integrity.
- Reference: `03_finance_app_dimensions_and_mapping.md`, ADR §5 implementation sketch, and `users.models.Subsidiary` enum.

## Recommended Next Steps
1. Read the context pack docs plus `IMPLEMENTATION_PLAN.md` Issue 3 section to confirm acceptance criteria.
2. Scaffold `apps/finance` (models, admin, migrations) mirroring existing app conventions (history not required).
3. Build `finance_sync_dimensions` using `update_or_create` inside an atomic block; derive `display_name` as `{subsidiary}-{geography.name}`.
4. Write unit tests under `apps/finance/tests/` covering first-run insert, second-run no-duplication, and site→company linkage.
5. Run `python manage.py makemigrations finance`, apply migrations, sync dimensions locally, regenerate OpenAPI (if any new endpoints later), and execute the full test suite against Postgres.

## Risks & Watch-outs
- Do not introduce operational FKs back to Finance dims; keep joins read-only.
- Ensure `Subsidiary` derivation aligns with infrastructure models (stations → Freshwater, areas → Farming).
- Management command should tolerate geographies/subsidiaries that lack associated infra objects (still create DimCompany rows to keep reporting complete).
- Keep naming consistent with API standards for future Issues (kebab-case basenames, documented schemas).
