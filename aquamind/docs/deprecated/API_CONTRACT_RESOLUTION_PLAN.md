# API Contract Resolution Plan  
_AquaMind Frontend ↔ Backend • August 2025_

---

## 1 Executive Summary
The migration to the generated **ApiService** client surfaced > 100 TypeScript errors and multiple runtime gaps. Root issues:

* Two parallel DTO hierarchies (`client/src/lib/types/django.ts` vs generated `models/`).
* CamelCase expectations in UI while backend delivers snake_case.
* Components call out-of-date service methods or legacy endpoints.
* UI depends on computed fields that the backend never implemented.

The objective of this plan is to eliminate contract drift, re-enable strict type-checking in CI, and guarantee that every API change is reflected in both codebases automatically.

---

## 2 Phased Implementation Approach

| Phase | Goal | Key Tasks | Owners | Effort |
|-------|------|----------|--------|--------|
| **P0 – Quick Wins** | Reduce error count by 60 % in 24 h | • Remove `client/src/lib/types/django.ts` and fix imports<br>• Rename wrong `ApiService` methods in Scenario & Batch pages<br>• Add temporary `// @ts-ignore` ONLY where needed to unblock build | FE | 0.5 d |
| **P1 – Adapter Layer** | Introduce clean mapping boundary | • Create `client/src/adapters/` with mappers for `FeedingEvent`, `Area`, `Station`, `Batch`<br>• Convert affected components to use adapters (no direct snake_case) | FE | 1 d |
| **P2 – Component Refactor** | Achieve zero TypeScript errors | • Update remaining pages (Inventory, Infrastructure lists, Scenario) to adapters + generated models<br>• Delete `django-api.ts`, legacy hooks | FE | 2 d |
| **P3 – Backend Gap Closure** | Supply heavy computed data | • Implement Area & Station summary serializers (`total_biomass`, `average_weight`, etc.)<br>• Add Scenario projections nested routes<br>• Update OpenAPI; CI regenerates client | BE | 1 d |
| **P4 – CI Hardening** | Prevent future drift | • Flip `npm run type-check` & `validate:endpoints` to **blocking**<br>• Add ESLint rule forbidding literal `/api` strings<br>• Add pre-commit hook to reject duplicate DTO files | DevOps | 0.5 d |

_Total scheduled effort_: **5 developer-days** spread across teams.

---

## 3 Quick Wins (start immediately)

1. **Delete duplicate types file** (`lib/types/django.ts`) – commit will shrink error list by ~40.
2. **Search-replace wrong service names** (`apiV1ScenarioScenariosProjectionsList` → correct).
3. **Cast obvious snake_case fields** in hot paths (BatchFeedHistoryView) to unblock UI.
4. **Document temporary ignores** in code comments so they can be removed in P2.

These steps unblock daily work and give the team breathing room to execute structured refactor.

---

## 4 Architectural Decisions

| Decision | Rationale | ADR |
|----------|-----------|-----|
| **Adapters as the permanent translation layer** | Keeps backend free to stay snake_case; frontend enjoys camelCase; isolates computed fields. | ADR-005 |
| **Generated models are the single source of truth** | Eliminates drift and manual maintenance. | ADR-006 |
| **Backend supplies heavy aggregates** (KPI summaries) | Prevents browser CPU/ memory spikes and duplicate query logic. | ADR-007 |
| **Strict CI gates** (type-check + endpoint validator) | Guarantees future changes follow contract-first workflow. | ADR-008 |

All ADRs will be authored in `docs/adr/` and referenced in pull-requests.

---

## 5 Timeline & Effort Estimates

| Week / Day | Activity | Deliverable |
|------------|----------|-------------|
| **Day 1 (P0)** | Quick wins, PR #XX | Build passes locally (<40 errors) |
| **Day 2-3 (P1)** | Adapter scaffolding & migration for high-traffic pages | PR #YY, CI green except adapter backlog |
| **Day 4-5 (P2)** | Remaining component refactor, delete dead code | PR #ZZ, `npm run type-check` passes |
| **Day 5 (P3)** | Backend summary endpoints, OpenAPI update | PR backend #AA, regenerated client |
| **Day 5 (P4)** | CI gate flip + pre-commit | All pipelines blocking on type / endpoint errors |

Buffer of 1 day reserved for code review & hot-fixes.

---

## 6 Success Metrics

| Metric | Target | Source |
|--------|--------|--------|
| TypeScript errors on `main` | **0** | `npm run type-check` |
| Unknown endpoints detected | **0** | `scripts/validate-endpoints.ts` |
| Playwright smoke suite | **100 % pass** | Frontend CI |
| Schemathesis run | **0 unexpected 404/500** | Backend CI |
| PR cycle time | ≤ 2 days | GitHub Insights |
| Docs freshness | ADRs merged & linked in README | Manual audit |

Meeting all metrics signals completion of the API alignment Phase 2 and readiness to activate **contract-strict** freeze tag (`v1.0-contract-strict`).

---

### Let’s ship it 🚀
