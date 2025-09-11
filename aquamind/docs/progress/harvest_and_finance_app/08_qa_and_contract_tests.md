# Issue 8 — QA & Contract Tests: System Integration & Docs Sync  

_Master plan reference_: `docs/progress/harvest_and_finance_app/IMPLEMENTATION_PLAN.md`  

---

## 1 Summary  
Final quality gate for the Harvest + Finance side-quest.  
Run **end-to-end tests**, regenerate **OpenAPI**, execute **Schemathesis** contract tests, and ensure documentation is fully aligned. Nothing merges until this issue passes.

---

## 2 Read First (Context Pack)  

| Doc / Code | Why you must read |
|------------|------------------|
| `docs/quality_assurance/api_standards.md` | baseline for router/URL/contract compliance |
| `docs/design/finance_harvest_design_spec.md` | canonical domain & API shapes |
| `docs/architecture.md` | system context & components |
| `docs/fit_gap_analysis.md` | ensure new work closes prior gaps |

Open every one of these at the start of the session to prevent context rot.

---

## 3 Scope  

### 3.1 Tests  
- **Projection**  
  - Verify idempotency: second run of `finance_project` yields zero new rows.  
  - Positive IC detection: different `source_company_key` vs `dest_company_key` + active policy ⇒ `IntercompanyTransaction` created.  
  - Negative IC: identical company keys ⇒ _no_ transaction.  
- **Export batching** – `NavExportBatch` marks transactions `exported`; CSV contents validated.  
- **API layer**  
  - Filter logic & RBAC on all new endpoints (facts, IC transactions, NAV exports).  
  - 403/405 edge-cases.  
- **OpenAPI & Contract**  
  - Regenerate schema (`spectacular`) and commit.  
  - Run Schemathesis with hooks; max examples ≥ 10; zero failures.  

### 3.2 Documentation  
- Update design spec with any final field or route tweaks.  
- Cross-link ADR 000X and BI guide.  
- Mark **Issue checkboxes** in master plan.

### 3.3 CI Integration  
- Extend test matrix to include `apps/finance`, `apps/harvest` tests.  
- Add job step: `schemathesis run --hypothesis-max-examples=10 api/openapi.yaml`.  
- Ensure `finance_project` CLI runs against test DB in CI to catch migrations.

---

## 4 Deliverables  
- New or extended **pytest** test modules (unit + integration).  
- Updated **OpenAPI** file committed.  
- Documentation edits (design spec + master plan checkbox).  
- Passing CI pipeline with contract tests.

---

## 5 Acceptance Criteria  
- [ ] All new endpoints, projections, and export flows covered by tests (≥ 90 % lines in new apps).  
- [ ] Schemathesis contract run passes with zero errors.  
- [ ] `python manage.py spectacular --file api/openapi.yaml` produces spec with no path conflicts.  
- [ ] Design spec & ADR cross-referenced; BI guide linked where relevant.  
- [ ] CI status is green on PR; no warnings from linters or typing.  

---

## 6 Implementation Guidance  

1. **Deterministic Fixtures**  
   - Factory Boy fixtures for predictable IDs / dates → easier idempotency asserts.  
2. **Reusable Assertions**  
   ```python
   def assert_projection_idempotent():
       first = run_projection()
       second = run_projection()
       assert second.facts_created == 0
   ```  
3. **Negative Test Cases**  
   - Harvest event with same company key must _not_ create IC transaction.  
   - Unauthorized role must fail on export endpoints (`403`).  
4. **Fast Tests**  
   - Use in-memory SQLite for unit tests; Postgres for integration via test container.  
   - Mark slow tests with `@pytest.mark.slow` and exclude from default run.  
5. **Schemathesis Setup**  
   - Import auth hooks from `aquamind.utils.schemathesis_hooks`.  
   - Limit examples but cover all tag groups (`--hypothesis-max-examples=10`).  

---

## 7 Out of Scope  
- Load/performance testing (plan a separate JMeter/Gatling task).  
- Security scanning (handled in platform-wide pipeline).

---

## 8 PR Checklist  

- [ ] New/updated tests committed & passing.  
- [ ] OpenAPI regenerated; committed diff reviewed.  
- [ ] Schemathesis job green.  
- [ ] Docs updated (design spec, ADR links, master plan checkbox).  
- [ ] PR description: test coverage summary, how to reproduce locally, risk/rollback.

_Tick this issue in the master implementation plan when **all acceptance criteria** are met._  
