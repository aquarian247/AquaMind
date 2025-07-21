# PR Merge Readiness Checklist  
*AquaMind API Contract Unification – July 2025*

---

### 1. Backend Fix Status
- [ ] **StageTransitionEnvironmental 500s resolved**  
      • `search_fields` updated to use `source_batch__batch_number` & `destination_batch__batch_number`.  
      • Manual smoke-test confirms 200 / 400 responses as expected.
- [ ] **Pagination validation active** – negative / zero `?page=` returns **400** via `ValidatedPageNumberPagination`.
- [ ] **OpenAPI schema regenerated** with `python manage.py spectacular --settings=aquamind.settings_ci > api/openapi.yaml`.  
      • File committed & no diff in CI *Schema Diff Gate*.
- [ ] **Unit-test suite** passes locally (`python manage.py test --settings=aquamind.settings_ci`).

### 2. CI/CD Expected Outcomes
- ✔️  **Django unit tests:** green  
- ✔️  **Coverage:** ≥ 40 % project-wide & ≥ 95 % for lines touched by this PR  
- ✔️  **Schemathesis contract tests:** 100 % pass (³ 3695 checks)  
- ✔️  **Operation-count gate:** ≈ 392 operations (≤ ± 50 diff)  
- ✔️  **Schema diff gate:** no uncommitted changes after re-generation  
- 📦  Artefacts uploaded: `schemathesis-output.txt`, `api/openapi.yaml`

### 3. Frontend Integration Testing Steps
1. Pull branch, then run  
   `yarn generate:api`  (maps to `openapi-generator-cli … api/openapi.yaml`).
2. `yarn dev` – frontend proxies to `http://localhost:8000`.  
   • Confirm login, dashboard data & **Stage Transition** views load.
3. Edge-cases to verify in browser console / network tab:  
   - `GET /api/v1/environmental/stage-transitions/?search=test` → 200, empty list ok.  
   - `GET /api/v1/environmental/stage-transitions/?page=-1` → 400 handled by UI toast.  
4. Run automated tests: `yarn test` → no type or runtime errors.  
5. Approve FE PR triggered by `api-spec` artifact (if applicable).

### 4. Known Issues / Considerations
- **Warnings during schema generation** (62 type-hint fall-backs) are benign and tracked in #284; do not block merge.
- **Legacy infrastructure routers** remain disabled; operation count will rise once re-enabled – documented in roadmap.
- SQLite used in CI; Postgres/Timescale differences are covered by integer-range clamping hook.

### 5. Post-Merge Action Items
- [ ] Tag release `v0.9.0-contract-unified` in backend repo.
- [ ] Merge corresponding **frontend** PR once its CI is green.
- [ ] Trigger staging deployment (`deploy-staging` job).  
      • Smoke-test key flows on staging.
- [ ] Update internal API changelog & notify QA to run regression suite.
- [ ] Close GitHub issues: #311 (API 500), #298 (pagination validation), #260 (schema drift).

*If every box above is ticked, the PR is ready to merge with high confidence.*  
