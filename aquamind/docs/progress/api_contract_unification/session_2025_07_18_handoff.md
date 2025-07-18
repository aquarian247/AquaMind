# Session 2025-07-18 — API Contract Unification Handoff

**Maintainer leaving:** Grok (Factory.ai)  
**Next maintainer:** _YOU_ (please read **everything** below before coding)  
**Branch:** `feature/api-contract-unification` (backend + frontend)  

---

## 1 ▪ Executive Summary

We are **99 % complete**.  
Contract-testing with Schemathesis now reports **536 / 537 checks PASS**; the only failure is a *false-positive* on `/api/v1/auth/dev-auth/` (endpoint should be anonymous).  
Global auth is enforced, `SessionAuthentication` removed, status-code conformance is green, legacy `/infrastructure/*` paths pruned, SQLite clamp hook active.  
**Outstanding items:** whitelist dev-auth in the OpenAPI schema, fix ~69 unit tests that now break due to stricter auth, and merge.

---

## 2 ▪ Start-Here Reading List  (≈ 15 min total)

1. `docs/progress/api_contract_unification/AquaMind API Unification Project Plan - New.md`  
   – Big picture, phases, new **§2a Authentication Breakthrough** table.

2. `docs/progress/api_contract_unification/CI_TROUBLESHOOTING_LOG.md`  
   – Chronological root-cause analysis; last update 2025-07-18.

3. Source code hooks:  
   - `aquamind/utils/openapi_utils.py` (post-processing hooks)  
   - `aquamind/settings.py` & `settings_ci.py` (REST_FRAMEWORK & SPECTACULAR settings)  

4. Helper scripts (added this session, optional to inspect):  
   - `scripts/add_auth_to_viewsets.py`  
   - `scripts/fix_auth_syntax.py`

Read in that order; you’ll have full context.

---

## 3 ▪ Exact Remaining Tasks

| # | Task | When done |
|---|------|-----------|
| 1 | **Whitelist anonymous auth endpoints in schema** so Schemathesis stops flagging `/api/v1/auth/dev-auth/`. | `ignored_auth` = 0 |
| 2 | **Update 69 failing unit tests** to authenticate (`force_authenticate` or header). | `pytest` green in CI |
| 3 | Remove temp debug middleware (`AUTH_DEBUG`) & helper scripts from production settings. | clean code |
| 4 | Full Schemathesis run (no `--max-examples` cap) on CI. | 0 failures |
| 5 | Front-end regenerate client & type-check. | `npm run build` green |
| 6 | Final PR review & merge to `main`. | project done |

---

## 4 ▪ Technical Context

### 4.1 Global Auth Enforcement
```python
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
}
```
No `SessionAuthentication` anywhere. ViewSets inherit this; a few special cases (`AllowAny`) must declare it explicitly **and** be exempted in the schema.

### 4.2 Schema Hooks
* **ensure_global_security** – always adds `security: - tokenAuth: []`.
* **cleanup_duplicate_security** – dedups and **should keep `{}` only for endpoints in `EXEMPT_ANON_PATHS` set** (currently `token/` and `dev-auth/`).
* **clamp_integer_schema_bounds** – SQLite sanity (keep).

### 4.3 False-positive Details  
`/api/v1/auth/dev-auth/` correctly has:
```python
@extend_schema(auth=[])   # marks anonymous
@permission_classes([AllowAny])
```
But after hooks run, operation still inherits `tokenAuth` at top level. Schemathesis therefore expects 401 but receives 200.

---

## 5 ▪ Step-by-Step Instructions

### 5.1 Whitelist dev-auth in Schema

1. **Edit** `aquamind/utils/openapi_utils.py` → in `cleanup_duplicate_security` make sure `EXEMPT_ANON_PATHS` includes **exactly**:
   ```python
   EXEMPT_ANON_PATHS = {
       "/api/v1/auth/token/",
       "/api/v1/auth/dev-auth/",
   }
   ```
2. **Before deduplicating** per-operation security, if path in that set:  
   ```python
   operation["security"] = [{}]   # anonymous
   continue
   ```
3. Regenerate schema:
   ```bash
   python manage.py spectacular --file api/openapi.yaml --settings=aquamind.settings_ci
   ```
4. Run:
   ```bash
   schemathesis run http://127.0.0.1:8000/api/schema/ --checks=ignored_auth --hypothesis-max-examples=5
   ```
   Expect **0 failures**.

### 5.2 Fix Unit Tests

1. Run `pytest` (CI uses `settings_ci.py` → SQLite).  
2. For failing tests (≈ 69):  
   * If using DRF APITestCase – call `self.client.force_authenticate(user=self.user)`.  
   * If using `APIClient` directly – add header:  
     ```python
     client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
     ```  
     Use the CI token from `get_ci_token` mgmt command.
3. Commit after green.

### 5.3 Cleanup & Final Validation

1. Remove `AUTH_DEBUG` middleware import from `settings_ci.py`.  
2. Delete or archive helper scripts if not needed.  
3. Push branch, watch GitHub Actions:  
   * **schemathesis** job must report 0/0 failures  
   * **pytest** job must be green  
4. In front-end repo, run:
   ```bash
   npm run generate:api
   npm run type-check
   npm run build
   ```
   Fix any TS errors (should be none).

### 5.4 Merge

1. Update PR #12 description with final status.  
2. Request review → squash & merge → delete feature branch.

---

## 6 ▪ Expected Outcomes

| Metric | Target |
|--------|--------|
| Schemathesis failures | **0** |
| Unit tests | **0 failures** |
| Front-end build | Pass |
| Docs | Updated with root-cause & final results |
| PR #12 | Merged to `main` |

When these are met, **API Contract Unification is DONE 🎉**.

---

### Good luck 🚀  
All investigation groundwork is finished—focus on the 1 false-positive + unit-test patch-up and you’ll achieve 100 % success quickly.  
If anything is unclear, re-read the troubleshooting log; every root cause and fix attempt is documented there.  
Happy hacking!
