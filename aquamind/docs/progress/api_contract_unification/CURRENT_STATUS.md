# API-Contract Unification – Current Status  
*File *: `aquamind/docs/progress/api_contract_unification/CURRENT_STATUS.md`  
*Date *: **2025-07-15**  
*Maintainer*: Code-Droid / Team Backend 🐟

---

## 1  CI Dashboard (latest run)

| Repo | Pipeline Stage | Status | Notes | Last Commit |
|------|----------------|--------|-------|-------------|
| **AquaMind (backend)** | Unit / Integration tests | 🟢 Local ✔ &nbsp; 🔴 GitHub CI ✖ | All 482 tests pass locally on PostgreSQL. GitHub CI fails during Schemathesis step – token capture still empty. | `2ac520a` |
|                          | OpenAPI generation        | 🟢 Pass | `api/openapi.yaml` produced and uploaded. | |
|                          | Schemathesis contract     | 🔴 Fail | 401 / auth-enforcement mismatch; field-error crashes resolved. | |
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
6. **Legacy storage replaced** – Monolithic `server/storage.ts` & `routes.ts` retired in favour of lightweight **`server/mock-api.ts`** with env-toggle (`VITE_USE_MOCK_API` / `VITE_USE_DJANGO_API`).
7. **Field-resolution bugs eliminated** – Fixed incorrect `search_fields` in  
   • `MortalityEventViewSet` (`notes` → `description`)  
   • `JournalEntryViewSet` (`title`,`content` → `description`)

---

## 3  Remaining Blocking Issues

| # | Area | Description | Owner |
|---|------|-------------|-------|
| A-1 | Backend CI | **Authentication enforcement mismatch** – schema requires auth but many endpoints allow anonymous requests; Schemathesis flags “auth declared but not enforced”. | Backend |
| A-2 | Backend CI | Fine-tune pagination behaviour vs spec (`page=0`, huge page numbers) – decide if spec or code needs changes. | Backend |
| X-1 | Docs | Testing docs emphasise SQLite in CI but Windows Unicode pitfalls not mentioned; update guides. | Docs |

---

## 4  Immediate Next Actions

### Backend
1. Confirm CI token now **non-empty** (length 40).  
2. Investigate auth-enforcement: ensure every viewset inherits correct `permission_classes` or middleware; update schema if anonymous access is intended.  
3. Re-run Schemathesis locally (SQLite) to reproduce remaining auth / pagination failures.  
4. Once auth issues fixed, bump Hypothesis examples back to default (remove `--hypothesis-max-examples=10`).

### Frontend
No immediate work – monitor backend spec changes. Regenerate client only after schema stabilises.

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

- Backend workflow run: https://github.com/aquarian247/AquaMind/actions
- Frontend workflow run: https://github.com/aquarian247/AquaMind-Frontend/actions
- OpenAPI spec preview (Swagger/ReDoc): `http://localhost:8000/api/schema/docs/`
- Test strategy docs:  
  - `docs/quality_assurance/testing_strategy.md`  
  - `docs/quality_assurance/timescaledb_testing_strategy.md`

---

_Update this file at each major CI attempt or daily stand-up._  
