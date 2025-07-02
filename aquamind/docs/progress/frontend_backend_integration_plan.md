# Frontend ↔ Backend Integration Plan  
*File:* `aquamind/docs/progress/frontend_backend_integration_plan.md`  
*Owner:* Knowledge-Droid  *Implement:* Code-Droid(s)  
*Goal:* Allow a human tester to log in via React UI (using existing Django admin credentials) and freely browse a running AquaMind stack (React + Django + PostgreSQL) locally and in staging, with automated end-to-end tests guaranteeing that workflow.

---

## 1 Objectives & Success Criteria
| # | Objective | Success Criteria |
|---|-----------|-----------------|
| 1 | Add **React login page** that authenticates against `/api/v1/auth/login/` and stores session/JWT | User can sign in with Django superuser; token stored; redirects to dashboard |
| 2 | Configure **local full-stack environment** (docker-compose) | One command `docker compose up` starts db, backend, frontend; hot-reload works |
| 3 | Establish **integration testing harness** | Cypress (or Playwright) tests run in CI; green on login, navigation to 3 core pages |
| 4 | Provide **sample data loader** for predictable UI state | `manage.py loaddata demo.json` executed automatically in compose startup |
| 5 | Document workflow in this file and `README`s | A new engineer follows steps in ≤15 min to view app |

---

## 2 Prerequisites & Dependencies
1. Repositories linked in Factory workspace (`/backend`, `/frontend` mounts).  
2. Docker & Docker Compose v2 on runners.  
3. Environment variables managed via `.env` (development) and GitHub Secrets (CI).  
4. Backend must already expose authentication endpoints (per `DJANGO_INTEGRATION_GUIDE.md`).  
5. *OpenAPI contract plan* (separate doc) in progress—login endpoint already covered.

---

## 3 Local Development Environment

### 3.1 Compose Services
| Service | Image / Build Context | Ports | Notes |
|---------|----------------------|-------|-------|
| `db` | `postgres:16-alpine` + TimescaleDB ext | 5432 | volumes/`pgdata`; env from `.env` |
| `backend` | `Dockerfile.dev` in `/backend` | 8000 | depends_on: db |
| `frontend` | Node 18 + Vite dev server | 5173 | env `VITE_DJANGO_API_URL=http://backend:8000` |

Compose file lives in root of **backend** repo to keep DB/private side internal; frontend mounts via relative path.

### 3.2 Environment Files
```
# .env (root)
POSTGRES_USER=dev
POSTGRES_PASSWORD=dev
POSTGRES_DB=aquamind
DJANGO_SECRET_KEY=local-secret
VITE_DJANGO_API_URL=http://localhost:8000
VITE_USE_DJANGO_API=true
```

---

## 4 Step-by-Step Tasks for Code-Droids

### Phase A – Backend adjustments
1. **CORS**: Ensure `http://localhost:5173` allowed when `DEBUG=True`.  
2. **Seed admin/demo data**:  
   ```bash
   python manage.py createsuperuser --noinput \
       --username admin --email admin@example.com
   python manage.py loaddata demo_fixture.json
   ```

### Phase B – React Login Page
| Step | File / Command | Details |
|------|---------------|---------|
| F1 | `src/pages/Login.tsx` | Form (username, password) using Shadcn/ui components |
| F2 | Hook | `useLoginMutation` generated from OpenAPI client or manual `fetch` |
| F3 | State | On success save JWT/CSRF using TanStack Query `setQueryData` or custom auth store |
| F4 | Routing | Add `/login` route via Wouter; protect interior routes with guard that redirects if unauthenticated |
| F5 | Style | Tailwind classes, responsive |

### Phase C – Integration Tests
1. **Add Cypress** (`npm i -D cypress @testing-library/cypress`).  
2. `cypress.config.ts` baseUrl `http://localhost:5173`.  
3. Test spec `login.cy.ts`:
   ```js
   cy.visit('/login')
   cy.get('[data-cy=username]').type('admin')
   cy.get('[data-cy=password]').type('admin')
   cy.contains('Sign in').click()
   cy.url().should('include', '/dashboard')
   cy.contains('Dashboard')            // page loads
   ```
4. Additional specs: navigate to *Batches*, *Environmental Charts*, *Inventory* pages and assert 200 responses.

### Phase D – CI Pipeline Updates
| Repo | File | Job |
|------|------|-----|
| Backend | `.github/workflows/full-stack-ci.yml` | Build docker-compose, wait for health, run Cypress headless |
| Frontend | Trigger via workflow_call | Re-uses same Cypress job |

### Phase E – Factory.ai Automation
1. **Dev Task Template**: *“Run full-stack locally”* opens terminal with `docker compose up`.  
2. **Review Droid Rule**: On PRs touching `src/pages/Login.tsx` or `auth` libs, automatically require Cypress suite.  
3. **Knowledge to Code Handoff**: reference this plan ID `FBI-001`.

---

## 5 Testing Scenarios & Validation Matrix

| Scenario ID | Description | Path | Expected Outcome |
|-------------|-------------|------|------------------|
| **FBI-L1** | Admin login happy path | `/login → /dashboard` | Status 200, token stored, admin name visible |
| **FBI-L2** | Invalid credentials | wrong pwd | Error banner shown, stays on /login |
| **FBI-N1** | Navigate to Batches list | Sidebar → Batches | Table renders rows from `/api/v1/batch/batches/` |
| **FBI-N2** | Navigate to Environmental chart | Sidebar → Environmental | Chart.js renders with timeseries from API |
| **FBI-A1** | Unauthenticated access guard | Direct hit `/dashboard` without token | Redirect to `/login` |
| **FBI-CI** | CI smoke | Cypress headless pipeline | All specs green ≤ 5 min |

---

## 6 Event-Driven Sequence  
_Agentic development progresses by satisfying dependencies rather than waiting for calendar dates.  
Each step below **unlocks** the next; multiple steps can run in parallel once their prerequisites are complete._

| Seq # | Triggering Event → Resulting State |
|-------|------------------------------------|
| **1** | **Compose stack bootstrapped** → `docker compose up` starts DB, backend, frontend locally; hot-reload confirmed. |
| **2** | **Seed script verified** → Admin user + demo data load on startup; backend endpoints return 200 with data. |
| **3** | **Login skeleton merged** → `/login` route renders form and hits stub function. |
| **4** | **Auth wiring complete** → Successful POST to `/api/v1/auth/login/` stores token; redirect to `/dashboard`. |
| **5** | **Route guards active** → Visiting a protected route without token redirects to `/login`. |
| **6** | **Cypress suite green** → Headless run passes login test plus navigation to Batches, Environmental, Inventory pages. |
| **7** | **CI pipeline updated** → GitHub Actions job `full-stack-ci.yml` builds compose stack and runs Cypress; must pass before merge. |
| **8** | **Factory automation enabled** → Review Droid rule requires Cypress suite on any PR touching `auth` or `src/pages/Login.tsx`. |
| **9** | **Staging smoke pass** → Same Cypress suite passes against staging DMZ/VLAN environment, unblocking UAT. |

---

## 7 Open Questions
1. Use **JWT** or **session cookies**? Current backend indicates JWT; confirm.  
2. Which e2e framework preferred by team—Cypress vs Playwright? Defaulting to Cypress per prior docs.  
3. Future: admin section SPA vs leverage Django admin iframe?

---

## 8 Revision History
| Date | Author | Note |
|------|--------|------|
| 2025-07-02 | Knowledge-Droid | Initial plan drafted |

---

### :rocket: Code-Droid Kick-off Checklist
- [ ] Confirm backend auth mechanism & CORS
- [ ] Create docker-compose and seed scripts
- [ ] Implement login UI & route guards
- [ ] Wire TanStack Query auth hooks
- [ ] Write Cypress specs & integrate into CI
- [ ] Update READMEs and signal completion in Factory chat
