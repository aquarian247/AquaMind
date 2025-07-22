# AquaMind – API Contract Unification & Automation Strategy
*Version 1.0 – July 2025*

---

## 1 · Current State Analysis
| Aspect | Backend (Django repo) | Frontend (React repo) | Challenge |
|--------|----------------------|-----------------------|-----------|
| Contract artefact | `docs/aquamind_postman_collection.json` + `docs/api_documentation.md` | `docs/DJANGO_INTEGRATION_GUIDE.md` – hard-coded endpoint tables | Two divergent documents; must be updated in lock-step |
| Type information | Python ↦ DRF serializers | Manually written `types/django.ts` | Drift risk; no single schema owner |
| Validation | Unit tests only | Runtime 404 / shape mismatch | Contract regressions surface late |
| Sync process | Human-driven after feature PR | Copy-paste & doc editing | Error-prone, slows delivery |

---

## 2 · Proposed Unified Contract System

| Pillar | Details |
|--------|---------|
| **Single Source of Truth** | Generate **OpenAPI 3.1** spec directly from Django (`drf-spectacular` or `drf-yasg`). Commit `openapi.yaml` to backend repo; artefact tagged per release. |
| **Automated Type Generation** | GitHub Action in frontend repo runs `openapi-typescript-codegen` (or `orval`) on the latest spec ➜ produces strongly-typed API client + Zod schemas/TanStack Query hooks. |
| **Contract Testing & Validation** | 1. **Backend** – Schemathesis test suite ensures implemented endpoints conform to spec. 2. **Frontend** – Jest/ Vitest unit tests validate mocked responses against generated types. 3. **CI Gate** – Fails if spec changed but TS artefacts not regenerated. |
| **Documentation Automation** | Swagger UI & ReDoc auto-published from `openapi.yaml`; replaces manual Postman + Markdown tables. |
| **Factory.ai Workspace Integration** | Workspace links both repos; Droids watch `openapi.yaml`. When backend PR changes the spec, a parallel frontend PR with regenerated types is created automatically; Review Droid checks contract tests before merge. |

---

## 3 · Implementation Plan

### Phase 1 – Generate OpenAPI from Django
1. Add `drf-spectacular` to `requirements.txt`.  
2. Annotate viewsets/serializers where necessary.  
3. CI job `generate-openapi` outputs `openapi.yaml`; commit artefact.  
4. Publish Swagger UI at `/api/schema/docs/` for quick review.

### Phase 2 – Automated TypeScript Generation
1. Frontend repo: add dev-dep `openapi-typescript-codegen`.  
2. Script `npm run generate:api` → outputs to `src/api/generated`.  
3. GitHub Action triggers on spec artefact update; pushes regenerated code in dedicated PR.

### Phase 3 – Contract Validation & Testing
1. **Backend**: Add `schemathesis` CLI job `contract-test` in CI.  
2. **Frontend**: Add Vitest test that imports a sample response JSON and compiles against generated types.  
3. Shared reusable workflow `check-contract-drift` blocks merges if validation fails.

### Phase 4 – Factory.ai Automation
1. In workspace settings, mark `openapi.yaml` as *contract file*.  
2. Configure Code Droid rule: _“When `openapi.yaml` changes → run script `frontend:pipeline:generate-types`, open PR, mention reviewer.”_  
3. Enable Review Droid to run both back- and front-end contract tests before approving.

---

## 4 · Benefits & ROI

| Benefit | Impact |
|---------|--------|
| **Eliminates Manual Sync Errors** | Single artefact removes copy-paste; CI gate prevents divergence. |
| **Type-Safe Full-Stack** | Compile-time safety in React; fewer runtime 400/500s. |
| **Self-Updating Documentation** | Swagger/ReDoc always reflects latest API, aiding UAT testers and new devs. |
| **Faster Feature Delivery** | Factory.ai automates cross-repo PRs; developers focus on logic, not boilerplate. |
| **Improved Onboarding & Context Retrieval** | Factory’s search surfaces spec + generated code instantly. |
| **Audit & Compliance** | Versioned specs supply clear change history for regulatory reviews. |

---

## 5 · Migration Timeline (Minimal-Disruption)

## 5 · Event-Driven Migration Sequence

Agentic development is **dependency-driven, not calendar-driven**.  Instead of weekly sprints, each step below unblocks the next; multiple steps can run in parallel once their prerequisites are satisfied.

| Sequence # | Triggering Event → Resulting State |
|------------|------------------------------------|
| **1** | **Strategy Confirmed** → Strategy file approved and merged; dedicated `api-schema` branch created. |
| **2** | **OpenAPI Bootstrap** → `drf-spectacular` installed, serializers annotated, first `openapi.yaml` committed and published via CI. |
| **3** | **Typed Client Scaffolded** → Frontend `generate:api` script produces initial client; app compiles with generated hooks. |
| **4** | **Contract Validation Online** → Schemathesis + Vitest type-checks pass in CI; `check-contract-drift` workflow active. |
| **5** | **Factory Automation Enabled** → Workspace rule detects spec changes and opens automated spec-sync PRs; Review Droid gates on contract tests. |
| **6** | **Legacy Docs Deprecated** → Postman collection and handwritten tables moved to `docs/legacy/`; banner notes new OpenAPI source. |
| **7** | **Smoke Tests Green** → Full-stack contract suite passes against staging environment. |
| **8** | **UAT Gate Opens** → Stakeholders begin exploratory testing with live Swagger/ReDoc and autogenerated client in place. |
| **9** | **Post-UAT Cleanup** → Remaining legacy artefacts removed; contributor handbook updated to reference automated workflow. |

> **Why event-driven?**  
> Code- and Review-Droids execute tasks as soon as dependencies are met, often in parallel and at machine speed.  Sequencing by events avoids artificial delays and aligns progress with actual system readiness.
