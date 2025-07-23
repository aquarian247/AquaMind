# AquaMind Frontend ↔ OpenAPI Integration Plan  
_Last updated: 2025-07-22_

---

## 1&nbsp;· Current State Analysis
| Area | Status | Notes |
|------|--------|-------|
| **Backend** | `feature/api-contract-unification` branch, working tree clean | OpenAPI spec (`api/openapi.yaml`) already reflects new decimal-precision & unified response shapes |
| **Frontend** | `feature/api-contract-unification` branch, one untracked file (`METRICS_REPORT.md`) | `package.json` script `generate:api` points to `../AquaMind/api/openapi.yaml`; generated client lives in `client/src/api/generated/` |
| **Tooling** | `openapi-typescript-codegen` 0.29, `npm run generate:api` | Generates fetch-based client using union types |
| **CI** | GitHub Actions (`frontend-ci.yml`, `regenerate-api-client.yml`) | Will fail if types drift or linting errors appear |

---

## 2&nbsp;· Step-by-Step Checklist

### 2.1 Preparation
1. `cd C:\Users\bf10087\Projects\AquaMind`  
   ```bash
   git switch feature/api-contract-unification
   git pull
   ```
2. `cd ..\AquaMind-Frontend`  
   ```bash
   git switch feature/api-contract-unification
   git pull
   ```

### 2.2 Copy & Commit Latest Spec (if not auto-synced)
```bash
# from AquaMind-Frontend root
copy ..\AquaMind\api\openapi.yaml api\openapi.yaml
git add api/openapi.yaml
git commit -m "chore: sync latest openapi spec from backend"
```

### 2.3 Regenerate TypeScript Client
```bash
npm ci          # ensure deps installed
npm run generate:api
git add client/src/api/generated
git commit -m "chore: regenerate TS API client for unified contract"
```

### 2.4 Fix Compilation Breakages
1. Run type-check: `npm run type-check`  
2. Typical fixes:  
   • Adjust decimal fields: use `toFixed(2)` for currency/mass, `toFixed(4)` for precision values.  
   • Update destructuring paths where response envelope changed to `{ data, meta }`.  
   • Rename endpoints/services if `operationId` changed (search & replace).

### 2.5 Unit & Linting Pass
```bash
npm test            # Jest / vitest etc.
npm run check       # runs type-check
npm run lint        # if configured
```

### 2.6 Manual QA With Live Backend
1. **Start backend**  
   ```bash
   cd ..\AquaMind
   venv\Scripts\python.exe manage.py runserver
   ```
2. **Start frontend**  
   ```bash
   cd ..\AquaMind-Frontend
   npm run dev
   ```
3. Validate:
   - Login / JWT flow
   - Batch list, create, transfers
   - Environmental charts display with 4-dp precision
   - Feed & inventory pages show 2-dp decimals

### 2.7 Commit & Push
```bash
git add .
git commit -m "feat: align frontend with unified API contract"
git push --set-upstream origin feature/api-contract-unification
```

### 2.8 CI Verification
1. Confirm **backend** CI green (unit, Schemathesis).  
2. Confirm **frontend** CI green (`frontend-ci.yml`).  
3. Merge both PRs after Review Droid approval.

---

## 3&nbsp;· Potential Issues & Troubleshooting

| Symptom | Likely Cause | Resolution |
|---------|--------------|------------|
| `TS2339: property 'data' does not exist` | Response wrapped/unwrapped | Inspect new model in `generated/models/*`; update code `(res as PaginatedBatchList).results` etc. |
| Decimal displays `6` not `6.00` | Format not applied | Use helper `formatDecimal(value, 2)` (create util) |
| 401 errors despite login | Auth header path changed in `OpenAPI.ts` | Ensure `client/src/api/index.ts` sets `OpenAPI.TOKEN` after login |
| CORS preflight fails | Backend setting missing | Add `http://localhost:5173` to `CORS_ALLOWED_ORIGINS` in `settings.py` |
| CI `npm run generate:api` diff | Spec changed during PR | Re-run generation, commit again |

---

## 4&nbsp;· Testing & Validation Steps

1. **Type Safety** – `npm run type-check` must report 0 errors.  
2. **Unit Tests** – `npm test` green; coverage unchanged.  
3. **E2E Smoke (optional)** – Playwright script `npm run e2e` (if present).  
4. **Manual UX Check** – Verify:
   - Mass & currency: 2 decimal places
   - Scientific/precision readings: 4 decimal places
   - Pagination still works  
5. **CI** – Both repos’ workflows must pass on GitHub.  
6. **Regression** – Quick click-through of critical pages (dashboard, batch, inventory).

---

## 5&nbsp;· Success Criteria

- [ ] `client/src/api/generated/` regenerated from latest `api/openapi.yaml`.  
- [ ] `npm run type-check`, `npm test`, and lint succeed locally.  
- [ ] GitHub Actions **frontend-ci** passes.  
- [ ] Full-stack app runs locally without console/network errors.  
- [ ] Decimal values render with correct precision: `##.##` (mass/currency), `##.####` (sensor & growth).  
- [ ] Login, batch ops, feed management, environmental monitoring fully functional.  

_Once all boxes are checked, the AquaMind frontend is officially aligned with the unified backend API contract._
