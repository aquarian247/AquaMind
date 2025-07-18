# 🏁 Kick-off Prompt for Next Session – API Contract Unification

Welcome! You are continuing the **AquaMind API-contract unification** effort across the backend (`aquarian247/AquaMind`) and frontend (`aquarian247/AquaMind-Frontend`) repos.

---

## 1  Project Context & Objective
Unify both repos around a single OpenAPI 3.1 spec generated from Django, enforce that implementation & TypeScript client stay in sync, and ensure CI passes with Schemathesis contract tests.

---

## 2  What We Achieved in the Last Session (2025-07-15)
• Front-end: removed legacy `server/storage.ts` & `routes.ts`; added lightweight `server/mock-api.ts`; TypeScript build ✅  
• Back-end: fixed 500 errors by correcting `search_fields`  
  – `MortalityEventViewSet`: `notes → description`  
  – `JournalEntryViewSet`: `title, content → description`  
• Added protection in `apps/users/management/commands/get_ci_token.py` against empty token keys.  
• Updated docs: `CURRENT_STATUS.md` & created detailed hand-off `session_2025_07_15_handoff.md`.

All changes are pushed to **branch** `feature/api-contract-unification` in both repos.

---

## 3  Current Status & Immediate Priorities
Stage | Result (CI) | Priority
----- | ----------- | --------
Unit tests | ✅ | –
OpenAPI generation | ✅ | –
Schemathesis | ❌ | **Top** – failing due to auth enforcement mismatch & pagination edge-cases
Frontend build | ✅ | –

**Immediate tasks**
1. Verify CI token capture: token length should be 40 (management command now flushes).  
2. Audit authentication: endpoints declare auth but some allow anonymous GETs – fix `permission_classes` **or** adjust schema.  
3. Pagination: decide spec vs implementation for `page=0` & huge page numbers (404 vs 400/minimum=1).  
4. Re-run Schemathesis locally with SQLite (`ci.sqlite3`) to reproduce remaining failures, then push fixes.

---

## 4  Technical Details of Remaining Issues
ID | Symptom | Suspected Cause | Key Files
-- | --------| ---------------| ----------
A-1 | “Authentication declared but not enforced” warnings | ViewSets missing/overriding `IsAuthenticated` | Various `apps/*/api/viewsets*.py`
A-2 | 401s in Schemathesis (header present) | Token not captured or accepted | `.github/workflows/django-tests.yml`, `get_ci_token.py`
A-3 | Pagination 404 for `page=0`, `page>max` | DRF PageNumberPagination default min=1; spec lacks min constraint | `settings.py` (REST_FRAMEWORK), schema generation hooks

Helpful commands:
```bash
# local contract test (from backend root)
python manage.py migrate --settings=aquamind.settings_ci
python manage.py runserver 0.0.0.0:8000 --settings=aquamind.settings_ci &
schemathesis run --base-url=http://127.0.0.1:8000 --checks all api/openapi.yaml
```

---

## 5  Key File & Branch Locations
Repo | Branch | Files of Interest
---- | ------ | ----------------
Backend | `feature/api-contract-unification` | `api/openapi.yaml`; `.github/workflows/django-tests.yml`; `apps/users/management/commands/get_ci_token.py`; `apps/batch/api/viewsets.py`; `apps/health/api/viewsets/journal_entry.py`
Frontend | `feature/api-contract-unification` | `server/mock-api.ts`; `server/index.ts`; `.env.example`
Docs | same branch (backend) | `aquamind/docs/progress/api_contract_unification/CURRENT_STATUS.md`; `session_2025_07_15_handoff.md`

---

## 6  Action Checklist for You
- [ ] Pull latest `feature/api-contract-unification` in both repos.
- [ ] Run backend CI workflow locally or push test commit to observe token length output.
- [ ] Fix authentication enforcement inconsistencies; update schema if anonymous access is intended.
- [ ] Address pagination rules (schema min=1 or code 400).
- [ ] Re-run Schemathesis until **0 failures**.
- [ ] Update docs ➜ `CURRENT_STATUS.md` and add new handoff note.

Good luck! Let’s turn the Schemathesis light green. 🚦
