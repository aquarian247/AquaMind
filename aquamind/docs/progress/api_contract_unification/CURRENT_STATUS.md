# API-Contract Unification – Current Status  
*File *: `aquamind/docs/progress/api_contract_unification/CURRENT_STATUS.md`  
*Date *: **2025-07-16**  
*Maintainer*: Code-Droid / Team Backend 🐟

---

## 1  CI Dashboard (latest run)

| Repo | Pipeline Stage | Status | Notes | Last Commit |
|------|----------------|--------|-------|-------------|
| **AquaMind (backend)** | Unit / Integration tests | 🟢 Local ✔ &nbsp; 🟢 GitHub CI ✔ | All 482 tests pass on both PostgreSQL (local) & SQLite (CI). | `1aec9c8` |
|                          | OpenAPI generation        | 🟢 Pass | `api/openapi.yaml` produced and uploaded. | |
|                          | Schemathesis contract     | 🔴 Fail | CI red – *ignored_auth* & status-code failures remain. | |
| **AquaMind-Frontend**    | TypeScript compile        | 🟢 Local ✔ &nbsp; 🟢 CI ✔ | Build green after mock-API refactor (`storage.ts` removal). | `fdf7198` |
|                          | Generated client drift    | 🟢 Clean | No diff after latest `npm run generate:api`. | |

Legend: 🟢 Pass 🟡 Pending 🔴 Fail ✔ Local success ✖ CI failure

---

## 2  Key Accomplishments

1. **Unified OpenAPI 3.1 spec** generated directly from Django (`drf-spectacular`) and committed at `/api/openapi.yaml`.
2. **Type-safe TS client** generated in frontend via `openapi-typescript-codegen`; wired into build.
3. **Cross-repo workflows** established – backend uploads spec, frontend workflow ready to consume.
4. **Massive TypeScript cleanup** – >70 compile errors eliminated across broodstock, scenario, batch pages.
5. **Backend test suite green locally** after:  
   • Unicode removal in migrations (Windows/CI safe).  
   • Conditional TimescaleDB helpers.  
   • CI user + token management command.
6. **Global security enforced** – Added `SECURITY: [{"tokenAuth": []}]` to drf-spectacular settings + schema post-processing hook to de-duplicate entries.  
7. **Robust pagination** – Introduced `ValidatedPageNumberPagination` (min page = 1, graceful out-of-range handling) and wired as DRF default.  
8. **SQLite-safe schema** – Integer bounds clamped & duplicate `security` arrays cleaned in CI OpenAPI generation.  
9. **Legacy storage replaced** – Monolithic `server/storage.ts` & `routes.ts` retired in favour of lightweight **`server/mock-api.ts`** with env-toggle (`VITE_USE_MOCK_API` / `VITE_USE_DJANGO_API`).  
10. **Field-resolution bugs eliminated** – Fixed incorrect `search_fields` in  
    • `MortalityEventViewSet` (`notes` → `description`)  
    • `JournalEntryViewSet` (`title`,`content` → `description`)
11. **Frontend API integration simplified** – Decision approved to drop `client/src/lib/django-api.ts` wrapper and call generated **`ApiService`** directly.
12. **Protected-endpoint anonymity removed** – Enhanced `cleanup_duplicate_security` hook to strip `{}` (anonymous access) from every operation except the two auth endpoints, regenerated & committed (`1aec9c8`).

---

## 3  Remaining Blocking Issues

| # | Area | Description | Owner |
|---|------|-------------|-------|
| B-1 | Backend CI | **Schemathesis failing** – *ignored_auth* & status-code‐conformance errors persist despite security cleanup. Needs deeper header-injection audit & schema tweaks for auth endpoints. | Backend |
| X-1 | Docs | Testing docs emphasise SQLite in CI but Windows Unicode pitfalls not mentioned; update guides. | Docs |

---

## 4  Immediate Next Actions

### Backend
1. Investigate why Schemathesis still reports *ignored_auth*; capture headers received by DRF in failing requests.  
2. Add `400` response to auth endpoints or mark as negative-test-ignored.  
3. Regenerate schema after router rename cleanup (`/infrastructure/*` → `/batch/*`).  
4. Remove temporary `--hypothesis-max-examples=10` once CI is green.

### Frontend
Complete API integration simplification:  
• Remove `client/src/lib/django-api.ts`.  
• Update `client/src/lib/api.ts` to use generated `ApiService` directly.  
• Ensure environment configuration in `client/src/lib/config.ts`.

### Documentation
1. Add section **“Unicode-safe logging for Windows runners”** to  
   `docs/quality_assurance/testing_strategy.md`.  
2. Document auth-enforcement troubleshooting checklist in  
   `docs/quality_assurance/api_security.md`.

---

## 5  Ownership

| Scope | Primary | Backup |
|-------|---------|--------|
| Backend CI token & Schemathesis | @backend-lead | @devops-support |
| TypeScript cleanup | @frontend-lead | @typescript-rookie |
| Documentation | @tech-writer | @any-dev |

---

## 6  Useful Links

- Backend workflow runs: https://github.com/aquarian247/AquaMind/actions
- Frontend workflow runs: https://github.com/aquarian247/AquaMind-Frontend/actions
- OpenAPI spec preview (Swagger/ReDoc): `http://localhost:8000/api/schema/docs/`
- Test strategy docs:  
  - `docs/quality_assurance/testing_strategy.md`  
  - `docs/quality_assurance/timescaledb_testing_strategy.md`

---

_Update this file at each major CI attempt or daily stand-up._  
