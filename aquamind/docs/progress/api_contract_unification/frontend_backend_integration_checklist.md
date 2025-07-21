# Frontend-Backend Integration Checklist  
*Date: 2025-07-21*

---

## 🔄 Current Status  

* **StageTransitionEnvironmental 500s fixed** – search fields now reference `source_batch` / `destination_batch`; endpoint returns 200 / 400 as expected.  
* **Pagination validation verified** – negative page numbers (`?page=-1`) correctly return **400 Bad Request** via `ValidatedPageNumberPagination`.  
* **Fix pushed to PR branch** – CI pipeline should now run green with 100 % Schemathesis pass-rate.  

---

## 1. Operation Count Investigation  

| Snapshot | Date | Notes |
|----------|------|-------|
| **1 716 operations** | Early July | Pre-refactor schema contained duplicate router registrations, legacy infrastructure paths, and `/docs/`, `/redoc/` routes that are *not* part of the REST API surface. |
| **1 174 operations** | 2025-07-18 | Legacy infrastructure router temporarily **pruned** ➜ count dropped. Some duplicates were removed when routers were consolidated. |
| **392 operations**  | 2025-07-21 | Current, *correct* total after full cleanup & security unification. 170 distinct paths, of which **73** are custom-action endpoints (e.g. `/recent/`, `/stats/`, `/by_batch/`). The reduction reflects: 1) duplicate routes eliminated, 2) non-API (schema-doc) endpoints excluded, 3) only authenticated, versioned API surface retained. |

**Take-away:** 392 operations is the authoritative contract moving forward; any significant drift must be explained in PR review.

---

## 2. Backend Developer Checklist  

| # | Action | Rationale |
|---|--------|-----------|
| 1 | **Update / add ViewSet** with explicit<br>`authentication_classes = [TokenAuthentication, JWTAuthentication]`<br>`permission_classes     = [IsAuthenticated]` | Keeps schema & runtime security consistent. |
| 2 | **Run unit tests + Schemathesis locally**:  `./scripts/run_contract_tests.sh`  | Prevents CI regressions. |
| 3 | **Regenerate schema**: `python manage.py spectacular --settings=aquamind.settings_ci > api/openapi.yaml` | Ensures spec reflects new/changed endpoints. |
| 4 | **Check operation count** via `analyze_api_operations.py`; expect ~392 ± ∆ | Guards against accidental router duplication. |
| 5 | **Commit** `api/openapi.yaml` **and** any hook updates | Schema is source-of-truth for FE agents. |
| 6 | **Push branch** ➜ verify CI: all tests + 100 % Schemathesis pass-rate | Contract safety-net. |
| 7 | **Post PR comment**: “API CHANGE: …” + changelog snippet | Triggers FE regeneration workflow. |

---

## 3. Frontend Developer Checklist  

| # | Action | Command / Link |
|---|--------|----------------|
| 1 | **Pull latest `api/openapi.yaml`** from `main`. | `git pull origin main` |
| 2 | **Regenerate TypeScript client** using `openapi-generator-cli` (or NSwag):<br>`yarn api:generate` | Script is configured to read `api/openapi.yaml` from repo root. |
| 3 | **Run FE test-suite** (`yarn test`) + Storybook smoke-tests | Confirms no type errors or missing endpoints. |
| 4 | **Verify breaking changes**: search git diff for deleted functions / renamed models | Adjust service hooks accordingly. |
| 5 | **Manual check** in staging: hit new/changed endpoints via generated client | Confidence pass. |
| 6 | **Merge** FE PR after CI green. |

---

## 4. Continuous Integration Requirements  

1. **Unit Tests** – `pytest` suite must be green.  
2. **Contract Tests** – Schemathesis run must report **3695 / 3695 checks passed** (100 %).  
3. **Operation-Count Gate** – `analyze_api_operations.py` exits with status 0 (difference ≤ 50 ops from expected).  
4. **Schema Diff Gate** – Workflow fails if regenerated spec differs from committed `api/openapi.yaml`.  
   *Regenerate schema with* `python manage.py spectacular --settings=aquamind.settings_ci > api/openapi.yaml` *to ensure identical output locally & in CI.*  
5. **Artefacts** – Upload `schemathesis-output.txt` + `junit.xml` for PR visibility.  
6. **Coverage** – Lines touched by PR must maintain ≥ 95 % coverage in affected apps.  

---

### ☑️  When all boxes above are ticked, both teams can merge with high confidence that **backend changes propagate cleanly to the frontend and CI remains green.**
