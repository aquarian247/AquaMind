# API Contract Unification & Automation Plan  
*Location  *: `aquamind/docs/progress/api_contract_unification_plan.md`  
*Owner     *: Knowledge-Droid  
*Implement *: Code-Droid(s)  
*Target    *: **both** AquaMind backend (`github.com/aquarian247/AquaMind`) and frontend (`github.com/aquarian247/AquaMind-Frontend`) repositories  
*Initiates after*: **Strategy Ratified** event  
*Completes when*: **Post-UAT Cleanup** event (legacy docs removed)

---

## 🔎 Status Snapshot  *(2025-07-15)*
| Section | Status | Key Notes |
|---------|--------|-----------|
| **3.1  – Backend: Generate OpenAPI** | ✅ Complete | Spec file committed (`api/openapi.yaml`) |
| **3.2  – Frontend: Generate TS client** | ✅ Complete | `src/api/generated/` created & scripts added |
| **3.3  – Cross-repo automation** | ✅ Complete | Workflows in place, label `spec-sync` configured |
| **3.4  – Contract validation** | ⚠️ **Partial** | Schemathesis CI fails (401 − token capture); local run pending |
| **3.5  – Deprecate legacy docs** | ✅ Complete | Old Postman & markdown moved to `docs/legacy/` |
| **4    – Testing Matrix** | ⚠️ **Partial** | Backend unit tests green locally & in CI; contract + TypeScript compile still flaky |
| **5    – Factory.ai workspace** | ⏳ **Pending** | JSON config drafted; workspace script still to be created |


## 1 Objectives & Success Criteria
| # | Objective | Success Criteria |
|---|-----------|-----------------|
| 1 | Establish a **single source of truth** for the REST API using *OpenAPI 3.1* generated from Django | `openapi.yaml` committed & versioned in backend repo root (`/api/openapi.yaml`) |
## 7 Known Issues & Resolutions

| ID | Area | Symptom | Resolution / Mitigation | Status |
|----|------|---------|-------------------------|--------|
| KI-1 | Backend CI | Unicode characters (✓ ⚠ ℹ) in migrations crash Windows/SQLite CI | Replaced with ASCII `[OK] / [WARNING] / [INFO]` and added `PYTHONIOENCODING=utf-8` note | **Resolved** |
| KI-2 | Backend CI | `get_ci_token` prints nothing → Schemathesis 401 | Added `flush=True`, removed `sys.exit(0)`, workflow now echoes token length | **Open** |
| KI-3 | Testing Docs | Confusion between local PostgreSQL vs CI SQLite | Expanded §10 in *testing_strategy.md* with DB matrix & env-vars | **Resolved** |
| KI-4 | Frontend | Repeated TypeScript `results`/null errors | Introduced generics (`Paginated<T>`), added missing interfaces | **Mostly Resolved** (monitor) |

---

## 8 Revision History
| 3 | Fully **automate cross-repo sync** using Factory.ai & GitHub Actions | On merge of backend PR that changes spec → frontend PR with regenerated code opens automatically |
| 4 | Introduce **contract validation** in CI | Schemathesis job passes; contract-drift check blocks merge if types out-of-date |
| 5 | Replace legacy docs (Postman & hand-written tables) with **auto-published Swagger/ReDoc** | `/api/schema/docs/` served in dev & staging; old docs marked *deprecated* |

| 2025-07-15 | Code-Droid | Updated snapshot, documented Unicode fix, added Known Issues section |
---

## 2 Prerequisites & Dependencies
1. Python 3.11 environment with AquaMind backend installed  
2. Node 18+ environment with AquaMind-Frontend installed  
3. GitHub Actions runners with Docker support  
4. Factory workspace *“AquaMind”* created and linked to both repos (to be configured in §5)  
5. Repository secrets:
   - `PYPI_TOKEN` (for drf-spectacular if publishing)
   - `GH_PAT` (frontend workflow commits from CI)  

---

## 3 Step-by-Step Tasks (ordered by dependency)

### 3.1 Backend – Generate OpenAPI spec
| Step | Command / Code | Notes |
|------|----------------|-------|
| B1 | Add packages | `poetry add drf-spectacular drf-spectacular-sidecar` *(or)* `pip install ...` |
| B2 | `settings.py` | ```python\nREST_FRAMEWORK[\"DEFAULT_SCHEMA_CLASS\"] = \"drf_spectacular.openapi.AutoSchema\"\nSPECTACULAR_SETTINGS = {\"TITLE\": \"AquaMind API\", \"VERSION\": \"v1\"}\n``` |
| B3 | Add URL | `path("api/schema/", SpectacularAPIView.as_view(), name="schema"),` + Swagger/Redoc views |
| B4 | Generate spec artefact *(depends on B1-B3)* | `python manage.py spectacular --file api/openapi.yaml` – commit if diff |
| B5 | Commit **`api/openapi.yaml`** | Add to version control and (optionally) `docs/` redirect |

### 3.2 Frontend – Generate TypeScript client
| Step | Command / Code |
|------|----------------|
| F1 | `npm install -D openapi-typescript-codegen` |
| F2 | Add script to `package.json` | `"generate:api": "openapi --input ../AquaMind/api/openapi.yaml --output src/api/generated --client fetch"` |
| F3 | Auto-generate client on spec update *(depends on F1-F2, X2)* | Re-use workspace rule or lightweight CI job |
| F4 | Import hooks in code | `import { BatchService } from "@/api/generated";` |

### 3.3 Cross-Repo Automation
| Step | Action |
|------|--------|
| X1 | Backend CI uploads `openapi.yaml` as artefact `api-spec` |
| X2 | Reusable workflow `sync-openapi-to-frontend` triggers via `workflow_run` on success of backend CI |
| X3 | Workflow clones front-end repo, runs `npm run generate:api`, commits & opens PR titled `chore: regenerate API client for <sha>` |
| X4 | Add label `spec-sync` to aid Review Droid routing |

### 3.4 Contract Validation
| Layer | Tool | Implementation |
|-------|------|----------------|
| Backend | **Schemathesis** | Add job `schemathesis run --base-url=http://localhost:8000 --checks all api/openapi.yaml` |
| Frontend | **Type check** | `npm run tsc --noEmit` verifies generated types compile |

### 3.5 Deprecate Legacy Docs
1. Move `aquamind_postman_collection.json` and `api_documentation.md` to `docs/legacy/`  
2. Insert header “Deprecated – superseded by Swagger UI”  

---

## 4 Testing & Validation Matrix
| Test | Trigger | Pass Condition |
|------|---------|----------------|
| **OpenAPI generation** | Backend PR | Spec file updated – CI green |
| **Schemathesis** | Backend PR | 0 failed checks |
| **Type generation** | Frontend PR | `npm run build` passes |
| **Contract drift** | Both repos | `git diff --exit-code` on `src/api/generated` shows no changes |
| **E2E smoke (optional)** | Nightly | Cypress hits `/login`, `/api/v1/auth/csrf/` |

---

## 5 Factory.ai Workspace Configuration
```jsonc
{
  "workspace": "AquaMind",
  "repositories": [
    { "url": "github.com/aquarian247/AquaMind",           "mount": "/backend"  },
    { "url": "github.com/aquarian247/AquaMind-Frontend",  "mount": "/frontend" }
  ],
  "watch": {
    "/backend/api/openapi.yaml": {
      "on_change": "run-script",
      "script": "/frontend/scripts/regenerate_api.sh"
    }
  },
  "droids": {
    "code": { "enabled": true },
    "review": { "rules": ["spec-sync"] }
  }
}
```

---

## 6 Relevant Links
* Backend spec file (to be created): `/api/openapi.yaml`  
* Swagger UI (dev): `http://localhost:8000/api/schema/docs/`  
* Frontend type gen output: `src/api/generated/`  
* Legacy docs (to deprecate):  
  * `/docs/aquamind_postman_collection.json`  
  * `/docs/api_documentation.md`  
* Frontend guide: `AquaMind-Frontend/docs/DJANGO_INTEGRATION_GUIDE.md`  

---

## 7 Revision History
| Date | Author | Note |
|------|--------|------|
| 2025-07-02 | Knowledge-Droid | Initial plan drafted for Code-Droid execution |

---

### :rocket:  **Code-Droid Kick-off Checklist**
- [ ] Fork & checkout feature branch `feature/api-contract-unification`
- [ ] Complete **§3** tasks B1→B5, F1→F4, X1→X4
- [ ] Open coordination thread in Factory chat with status updates
- [ ] Ensure all tests in **§4** pass
- [ ] Submit PRs with label `spec-sync` for Review-Droid
