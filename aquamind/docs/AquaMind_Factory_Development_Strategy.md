# AquaMind ‒ Factory.ai Development Strategy  
### Evaluating Monorepo vs Separate Repositories for Front- & Back-End Code

---

## 1. Executive Summary

After weighing security, velocity, and sequencing factors, **the recommended approach is to keep the React frontend (`AquaMind-Frontend`) and Django backend (`AquaMind`) in _separate repositories_** while leveraging Factory.ai’s native multi-repo workspace.  
A focused integration layer (typed API contracts + shared CI checks) gives us monorepo-level cohesion without the migration risk or DMZ/VLAN complications that a true merge would introduce before UAT.

---

## 2. Analysis of the Two Approaches

| Topic | Monorepo (merge) | Separate Repos (retain) |
|-------|------------------|-------------------------|
| **Security alignment** | Requires path-based access controls to preserve DMZ/VLAN separation; risk of accidental coupling. | Mirrors production network segregation; no firewall changes. |
| **Development velocity** | Atomic PRs across stacks, easier refactors, single issue tracker. | Slightly more coordination on cross-repo changes; Factory.ai surfaces context to offset. |
| **Tooling complexity** | Composite tool-chain (Python + Node) in **every** CI job; larger images; slower builds. | Each repo keeps focused tool-chain; smaller CI images; faster builds. |
| **Event-chain risk** | Large structural refactor introduces many dependent steps and pipeline changes. | No structural refactor; energy goes directly to feature completion and hardening. |
| **Code sharing (models/types)** | Simple via local imports; single version guarantee. | Requires explicit contract artefacts (OpenAPI spec + generated TS types) but yields cleaner boundaries. |
| **Factory.ai support** | Supported, but huge repo context ingestion can be slower. | Natively supported; Workspace mounts multiple repos with fine-grained permissions. |

**Conclusion:** For AquaMind’s security posture and UAT timeline, the separate-repo model wins on risk and operational simplicity.

---

## 3. Factory.ai-Specific Considerations

1. **Multi-Repo Workspaces** – Factory can ingest multiple Git repos so chat & Droids see full context without copy-paste.  
2. **Unified Context Retrieval** – Editing backend API surfaces related frontend code automatically.  
3. **Automated Contracts** – Review Droid watches OpenAPI diffs and triggers regeneration of the TypeScript client in the frontend repo.  
4. **Parallel Pipelines** – Code Droid can open co-ordinated PRs when feature work spans the stack.  
5. **Access Control** – Each repo keeps least-privilege permissions aligned to DMZ vs VLAN deployment zones.

---

## 4. Implementation Strategy (Separate Repos)

### 4.1 Integration Layer

1. **Single Source of Truth for the API**  
   • Generate OpenAPI 3.1 spec (`api/openapi.yaml`) with `drf-spectacular` on every backend push.  
   • Commit the spec and publish it as a CI artefact.  
2. **Type Generation & Distribution**  
   • Frontend pipeline runs `npm run generate:api` (powered by `openapi-typescript-codegen`).  
   • Types compile to `src/api/generated`, plus pre-wired TanStack Query hooks.  
   • Optionally, publish `@aquamind/contracts` to GitHub Packages for reuse.  
3. **Contract Testing**  
   • Backend CI runs **Schemathesis** (property-based tests) ensuring implementation ⇔ spec parity.  
   • Frontend CI type-checks against generated client; fails if drift detected.

### 4.2 Factory.ai Configuration

- Create Factory workspace **AquaMind** with linked repos  
  `github.com/aquarian247/AquaMind` & `github.com/aquarian247/AquaMind-Frontend`.  
- Mark `api/openapi.yaml` as a *contract file* so Droids can subscribe to its diffs.  
- Default cross-repo tasks: **Sync API Changes**, **Implement Feature**, **Update Docs**.  
- Enable Review Droid to block merges unless contract tests & type generation succeed.

### 4.3 Contract-First Development Workflow

| # | What Happens | Trigger |
|---|--------------|---------|
| **1** | Developer edits serializers / views. | Human developer |
| **2** | Spec regenerated: `python manage.py spectacular --file api/openapi.yaml` and committed in same PR. | Pre-commit hook / CI |
| **3** | Backend CI runs unit tests **+ Schemathesis** (10 examples). Fails if impl ≠ spec. | GitHub Actions |
| **4** | **Code Droid** detects spec diff → opens *frontend* PR with regenerated TS client (`npm run generate:api`). | Code Droid |
| **5** | **Review Droid** gate ensures both PRs are green (tests + contract) before merge. | Review Droid |
| **6** | Merge → artefacts publish → staging auto-deploys. | GitHub Actions |

#### Best Practices for API Changes

1. **Prefer additive** – introduce new fields/endpoints instead of mutating existing ones.  
2. **Breaking change?** – bump **minor** version in `openapi.yaml` and document in changelog.  
3. Keep **error models & pagination docs** accurate when response shapes change.  
4. Run `schemathesis run --hypothesis-max-examples=1` locally before pushing.  
5. Add link to live Swagger/ReDoc (`/api/schema/swagger-ui/`) in PR description.

#### How Factory Droids Help

- **Code Droid** – watches `openapi.yaml`, regenerates TS client, raises synced PRs.  
- **Review Droid** – runs contract & security tests on both repos, enforces green gate.  
- **Test Droid** – CI wrapper that executes Schemathesis plus coverage thresholds.  
- **Docs Droid** – (road-map) injects changelog excerpts into docs when spec merges.

### 4.4 Repository Hygiene

- Delete legacy Vue code under `backend/frontend/`; ignore path in `.gitignore`.  
- Each repo root contains a **Factory manifest** (`factory.json`) describing build & test commands.  
- Commit hooks: lint, type-check, and `spectacular --validate-schema`.

### 4.5 Optional Future Monorepo Path

If business priorities change post-UAT, we can merge histories using `git filter-repo` or subtrees, backed by ADRs.

---

## 5. Development Workflow Guidelines

1. **Branch naming** – `feature/<ticket>` or `fix/<ticket>` in respective repos.  
2. **Local full-stack start**

```bash
# Terminal 1 – backend
docker compose up backend db

# Terminal 2 – frontend
cd AquaMind-Frontend && npm run dev
```

3. **Cross-repo PR checklist**  
   • Backend: update `openapi.yaml` & changelog.  
   • Frontend: regenerate client (`npm run generate:api`) and commit.  
4. **Code reviews** – via Review Droid; merge blocked until contract tests pass.  
5. **Documentation** – keep docs in each repo’s `docs/`; cross-link via GitHub URLs.

---

## 6. Testing & Debugging Strategies

| Layer | Tooling | Notes |
|-------|---------|-------|
| Frontend unit | Vitest + React Testing Library | Mock TanStack Query; Storybook visual tests. |
| Backend unit | Django + pytest | Focus on business logic. |
| Contract tests | Schemathesis | Property-based; nightly exhaustive run. |
| End-to-End | Playwright (optional) | Smoke flows in staging. |

Debug prod issues with structured logging, Sentry traces, and Factory log ingestion.

---

## 7. CI/CD Considerations

### Backend (`AquaMind`)
- GitHub Actions matrix: `python 3.11`; DB: PostgreSQL & SQLite (CI).  
- Jobs: `lint` → `test` → `build-docker` → `push to registry`.

### Frontend (`AquaMind-Frontend`)
- Jobs: `lint` → `unit-tests` → `generate-api-types` (fails on drift) → `build` → `upload-artifact`.  
- On `main` tag: build static bundle & publish to S3/CDN.

### Cross-Repo Gate
- Reusable workflow **`check-contract-compat`** ensures both repos are green before deployment.

### Security Scanning
- Backend: Bandit, Django-secure-check.  
- Frontend: `npm audit` + Snyk OSS scanning.

---

## 8. Event-Driven Migration Sequence

Agentic development hinges on event dependencies rather than calendar dates.

| Seq | Event → Resulting State |
|-----|-------------------------|
| 1 | **Strategy Ratified** → Workspace with dual repos created. |
| 2 | **Legacy Cleanup** → Vue code removed; CI green. |
| 3 | **API Contract Bootstrap** → Spec artefact published by backend CI. |
| 4 | **Typed Client Scaffolded** → Frontend compiles with generated client. |
| 5 | **Automation Online** → First auto spec-sync PR raised by Code Droid. |
| 6 | **Contract Suite Passing** → Schemathesis + TS type-check green. |
| 7 | **Smoke Env Ready** → Staging deployed; Playwright smoke tests pass. |
| 8 | **Security & Load Validation** → Sign-off; UAT gate opens. |
| 9 | **UAT Kick-off** → Stakeholders test with Factory observability. |
| 10 | **Post-UAT Retrospective** → Decide on potential monorepo merge for v2. |

> If a step fails, Code Droids iterate locally and re-emit the failed step without resetting the chain.

---

### Appendix — Key Links

* Development Workflow doc: `/docs/DEVELOPMENT_WORKFLOW.md` (frontend repo)  
* Deployment Architecture doc: `/docs/DEPLOYMENT_ARCHITECTURE.md` (frontend repo)  
* Factory workspace setup guide: _internal wiki_  

_Compiled July 2025 for the AquaMind engineering team._
