# Harvest & Finance App — Master Implementation Plan

Purpose  
Track and coordinate the “Harvest + Finance” side quest through clear, check-off outcomes per phase. This plan complements the individual GitHub issues (issues 54 through 61) by defining shared context, gating criteria, and a consistent agent workflow to prevent context rot. This must all be done in the same feature branch: features/harvest-and-finance and make sure we are on a main and everything is pruned and remnant feature branches are deleted. Then create features/harvest-and-finaince branch for this side-quest.

---

## Core Outcomes
• Harvest domain (events, lots, grades, waste, audit; read APIs)  
• Finance dimensions (company/site), projections (fact_harvest), inter-company detection  
• Read-only Finance APIs; NAV export skeleton; BI delivery (views, guide)

---

## Shared Context Pack  (read these first in **every** session)
- aquamind/docs/design/finance_harvest_design_spec.md  
- aquamind/docs/quality_assurance/api_standards.md  
- aquamind/docs/architecture.md  
- aquamind/docs/prd.md  
- aquamind/docs/personas.md  
- aquamind/docs/database/data_model.md  

---

## Repeatable Agent Workflow
1. Read the **Context Pack** above  
2. Open the matching GitHub issue and its PR checklist  
3. Work strictly within current phase scope  
4. Regenerate OpenAPI & run full test suite  
5. Update docs (design spec, ADRs, BI guide)  
6. Link PR to issue; add verification & rollback notes  

---

## Phase Checklist  (√ when complete & link PR/issue)

| ✔ | Phase / Issue | Done-When | Links |
|---|---------------|-----------|-------|
| [ ] | **Issue 1 (no. 54 in github) — ADR: Lightweight Intercompany & Finance Dims**<br>Context: Align spec; keep ops free of Company model | ADR merged; spec updated; open decisions logged | [ADR PR]() / [Issue]() |
| [ ] | **Issue 2 (no. 55 in github) — Harvest Domain: Models, Audit, Read API**<br>Context: HarvestEvent, HarvestLot, HarvestWaste, ProductGrade; dest_geography + dest_subsidiary | Migrations+admin; endpoints list/filter; OpenAPI green | [PR]() / [Issue]() |
| [ ] | **Issue 3 (no. 56 in github) — Finance App: Dimensions & Mapping**<br>Context: DimCompany, DimSite; sync command | `finance_sync_dimensions` idempotent | [PR]() / [Issue]() |
| [ ] | **Issue 4 (no. 57 in github) — Finance Projection: fact_harvest & IC Detection**<br>Context: FactHarvest, IntercompanyPolicy/Transaction; projection CLI | Idempotent; IC only when keys differ + policy | [PR]() / [Issue]() |
| [ ] | **Issue 5 (no. 58 in github) — Finance Read APIs**<br>Context: Read-only endpoints, filters, RBAC | Filters AND-combined; pagination; schema validated | [PR]() / [Issue]() |
| [ ] | **Issue 6 (no. 59 in github) — NAV Export Skeleton**<br>Context: Batch pending IC txns ➔ CSV/JSON; download endpoint | Batch marks txns exported; idempotent guard; file validates | [PR]() / [Issue]() |
| [ ] | **Issue 7 (no. 60 in github) — BI Delivery: Views & Incremental Refresh Guide**<br>Context: DB views, indexes, Power BI guide | Views & guide in repo; performance indexes | [PR]() / [Issue]() |
| [ ] | **Issue 8 (no. 61 in github) — QA & Contract Tests**<br>Context: E2E tests, Schemathesis, docs sync | CI green; coverage on projections/exports/APIs; docs synced | [PR]() / [Issue]() |

---

## Quality Gates  (apply to every phase)
- OpenAPI builds; Schemathesis passes  
- Kebab-case basenames; no duplicate routers  
- Tests & migrations reversible  
- Docs updated (design spec, ADRs, BI guide)  
- PR includes rollback plan  

---

## Runbook  (local developer commands)
```bash
python manage.py makemigrations && python manage.py migrate
python manage.py test
python manage.py spectacular --file api/openapi.yaml
python manage.py finance_sync_dimensions
python manage.py finance_project --from=YYYY-MM-DD --to=YYYY-MM-DD
```

---

## Decision Log  (append chronologically)
- **0001** Lightweight intercompany via (geography, subsidiary); Finance dims own mapping; no users.Company in ops  
- **0002** Open decisions: pricing method TBD; grade taxonomy TBD; NAV transport TBD; FX source TBD  

---

## Risks & Mitigations
| Risk | Mitigation |
|------|------------|
| Ambiguity in legal entities | Use flexible dims; add Company model later if required |
| Spec / API drift | Contract tests + ADR gating each phase |
| BI refresh performance | Partition facts by date; narrow views; index common filters |

