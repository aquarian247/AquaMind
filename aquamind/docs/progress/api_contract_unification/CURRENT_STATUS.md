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
|                          | Schemathesis contract     | 🔴 Fail | 401 auth error (no token). | |
| **AquaMind-Frontend**    | TypeScript compile        | 🟢 Local ✔ &nbsp; 🟡 CI (pending) | ~70+ errors resolved; latest push building. | `d9de259` |
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

---

## 3  Remaining Blocking Issues

| # | Area | Description | Owner |
|---|------|-------------|-------|
| B-1 | Backend CI | `get_ci_token` prints nothing in GitHub runner → Schemathesis auth header empty → 401s. | Backend |
| B-2 | Backend CI | Need echoed token length / debug to verify capture; may require `echo "::set-output"` style. | Backend |
| F-1 | Frontend CI | Confirm that latest TypeScript fixes push build to **green**; monitor for any residual `results`/null checks. | Frontend |
| X-1 | Docs | Testing docs emphasise SQLite in CI but Windows Unicode pitfalls not mentioned; update guides. | Docs |

---

## 4  Immediate Next Actions

### Backend
1. **Hard-verify token output**  
   ```bash
   TOKEN=$(python manage.py get_ci_token --settings=aquamind.settings_ci)
   echo "TOKEN-LEN=${#TOKEN}"
   ```  
   Fail step early if length == 0.

2. If stdout still blank:
   - Use `print(token.key, flush=True)` in command.
   - Fallback: `python - <<'PY' ...` inline to bypass management command.

3. Re-run Schemathesis locally with SQLite to reproduce CI.

### Frontend
1. Push any remaining type fixes; ensure `npm run tsc` passes in CI.  
2. Run `npm run generate:api -- --clean` post-backend spec update.

### Documentation
1. Add section **“Unicode-safe logging for Windows runners”** to  
   `docs/quality_assurance/testing_strategy.md`.  
2. Consider new sub-folder `docs/progress/api_contract_unification/` (created)  
   – host status log & troubleshooting diary.

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
