# AquaMind ‒ Factory.ai Development Strategy  
### Evaluating Monorepo vs Separate Repositories for Front- & Back-End Code

---

## 1. Executive Summary

After weighing technical, security, and sequencing factors, **the recommended approach is to keep the React frontend (`AquaMind-Frontend`) and Django backend (`AquaMind`) in _separate repositories_** and leverage Factory.ai’s native multi-repo capabilities.  
A focused integration layer (typed API contracts + shared CI checks) provides the cohesion you would gain from a monorepo without introducing migration risk before the UAT readiness milestone or compromising the DMZ/VLAN production model.

---

## 2. Analysis of the Two Approaches

| Topic | Monorepo (merge) | Separate Repos (retain) |
|-------|------------------|-------------------------|
| **Security alignment** | Requires careful path-based access controls to preserve DMZ/VLAN separation during deploy; risk of accidental coupling. | Mirrors production network segregation; no change to current firewall or deployment pipelines. |
| **Development velocity** | Atomic PRs across stacks, easier refactors, single issue tracker. | Slightly more coordination on cross-cutting changes; Factory.ai surfaces context across repos to offset. |
| **Tooling complexity** | Need composite tool-chain (Python + Node) in every CI job; larger containers and caches; slower builds. | Each repo keeps focused tool-chain; smaller CI images, faster incremental builds. |
| **Event-chain risk** | Large structural refactor introduces many dependent steps, changes to pipelines and commit histories, increasing coordination overhead. | No structural refactor; energy goes directly to feature completion, testing, and hardening for UAT. |
| **Code sharing (models/types)** | Simple via local imports; single version guarantee. | Requires explicit contract artifacts (e.g., OpenAPI spec or generated TypeScript types) but increases boundary clarity. |
| **Factory.ai support** | Supported, but large repo context ingestion may be slower. | Natively supported; multiple repos can be mounted into the same Factory workspace; tasks can reference both. |

**Conclusion**: For AquaMind’s security posture and UAT deadline, benefits of a monorepo are outweighed by migration risk and ops overhead.

---

## 3. Factory.ai-Specific Considerations

1. **Multi-Repo Workspaces** – Factory can ingest multiple Git repos; sessions, Droids, and chat can reference files across both without manual copy-paste.  
2. **Unified Context Retrieval** – The platform auto-surfaces relevant frontend code when editing backend API and vice-versa.  
3. **Automated Contracts** – Review Droid can watch OpenAPI diffs and trigger regeneration of TypeScript client typings in the frontend repo.  
4. **Parallel Pipelines** – Code Droid can open coordinated PRs in both repos when feature work spans the stack.  
5. **Access Control** – Each repo can inherit least-privilege permissions matching DMZ vs VLAN requirements.

---

## 4. Implementation Strategy (Separate Repos)

### 4.1 Integration Layer
1. **Define Single Source of Truth for API**  
   - Commit generated OpenAPI spec (`openapi.yaml`) to backend.  
   - Add GitHub Action to publish spec as artifact.  
2. **Generate Frontend Types**  
   - New package `@aquamind/contracts` published to GitHub Packages.  
   - Frontend pipeline (`npm run generate:api`) consumes latest artifact → creates strongly-typed TanStack Query hooks.

### 4.2 Factory.ai Configuration
- Create Factory workspace **AquaMind** with linked repos:  
  - `github.com/aquarian247/AquaMind`  
  - `github.com/aquarian247/AquaMind-Frontend`  
- Add context folders: `docs/` from both repos for richer retrieval.  
- Define default tasks: *“Implement feature”, “Sync API changes”, “Update docs”* that span repos.

### 4.3 Repository Hygiene
- Finish deleting legacy Vue code under `backend/frontend/` folder; mark path ignored in `.gitignore`.  
- Ensure each repo root has **Factory manifest** (`factory.json`) describing build/test commands.

### 4.4 Optional Future Monorepo Path
Document a staged plan (post-UAT) using Git subtrees or `git filter-repo` to merge histories if business needs evolve.

---

## 5. Development Workflow Guidelines

1. **Branch Naming**  
   - `feature/<ticket>` or `fix/<ticket>` in respective repos.  
2. **Local Full-Stack Start**  
   ```bash
   # Terminal 1 (backend)
   docker compose up backend db

   # Terminal 2 (frontend)
   cd AquaMind-Frontend && npm run dev
   ```
3. **Cross-Repo PR Checklist**  
   - Backend: update `openapi.yaml` & changelog.  
   - Run `frontend:sync-api` script; commit regenerated code in frontend PR.  
4. **Code Reviews** – Use Factory Review Droid for both PRs; ensure contract tests pass.  
5. **Documentation** – Keep shared docs in respective `docs/` dirs; cross-link via relative GitHub URLs.

---

## 6. Testing & Debugging Strategies

| Layer | Tooling | Notes |
|-------|---------|-------|
| Frontend unit | Vitest + React Testing Library | Mock TanStack Query; Storybook visual tests. |
| Backend unit | Django `pytest` suite | Existing high coverage. |
| Contract tests | `schemathesis` / `pytest-playwright` | Validate backend responses match OpenAPI; run nightly. |
| Integration (local) | Docker Compose `full-stack-test` target | Runs backend + frontend headless; Cypress e2e. |
| Network separation tests | Staging environment mirrors DMZ/VLAN; run smoke tests via VPN. |

Debugging production issues: enable frontend `NetworkDiagnostics`, backend structured logging, and use Factory’s log ingestion for root-cause suggestions.

---

## 7. CI/CD Considerations

### Backend (`AquaMind`)
- GitHub Actions matrix: `python 3.11`, DB `PostgreSQL`, `SQLite` for CI.  
- Jobs: `lint` → `test` → `build-docker` → push to container registry.

### Frontend (`AquaMind-Frontend`)
- Jobs: `lint` → `unit-tests` → `generate-api-types` (fails if drift) → `build` → `upload-artifact`.  
- On `main` tag, build static bundle, publish to S3/CDN.

### Cross-Repo Gate
- Reusable workflow **`check-contract-compat`** triggered from both pipelines; prevents breaking API drift.

### Security Scanning
- Backend: Bandit, Django-secure-check.  
- Frontend: npm audit + Snyk OSS scanning.

---

## 8. Event-Driven Migration Sequence

Agentic development benefits from milestone dependencies rather than wall-clock scheduling. The following **event chain** defines the order in which activities must complete; multiple steps can execute in parallel once their prerequisites are satisfied.

1. **Strategy Ratified**  
   *This document approved → Factory workspace with dual repos created.*
2. **Legacy Cleanup**  
   *Legacy Vue code removed → CI green without frontend folder in backend repo.*
3. **API Contract Bootstrap**  
   *OpenAPI generation merged → Spec artefact published from backend CI.*
4. **Typed Client Scaffolding**  
   *`@aquamind/contracts` package generated from spec → Frontend imports compile.*
5. **Cross-Repo Automation Online**  
   *Review-Droid & Code-Droid rules enabled → First automated spec-sync PR raised.*
6. **Contract Test Suite Passing**  
   *Schemathesis + type-check stages pass in CI for both repos.*
7. **Smoke Environment Ready**  
   *Staging stack deployed in DMZ/VLAN replica → Smoke tests (Cypress) pass.*
8. **Security & Load Validation**  
   *Security scan + load tests sign-off → UAT gate opens.*
9. **UAT Kick-off**  
   *Stakeholders begin exploratory testing with Factory observability enabled.*
10. **Post-UAT Retrospective**  
    *Lessons captured → Decide on potential monorepo merge for v2.*

> **Note on sequencing**: If any step fails, Code-Droids can iterate locally and re-emit the failed step without resetting the entire chain.

---

### Appendix — Key Links
* Development Workflow doc: `/docs/DEVELOPMENT_WORKFLOW.md` (frontend repo)  
* Deployment Architecture doc: `/docs/DEPLOYMENT_ARCHITECTURE.md` (frontend repo)  
* Factory workspace setup guide: internal wiki page (to create)  

---

_Compiled July 2025 for the AquaMind engineering team._
