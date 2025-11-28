# Financial Core Implementation Plan

**AquaMind Financial Planning & Budgeting Module**

**Version**: 2.0  
**Date**: November 26, 2025  
**Status**: Production-Ready with EoM Extensions

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Implementation Overview](#implementation-overview)
3. [Phase 1: Foundation (Weeks 1-3)](#phase-1-foundation)
4. [Phase 2: Core Features & Allocation (Weeks 4-6)](#phase-2-core-features--allocation)
5. [Phase 3: EoM Integration & Reporting (Weeks 7-9)](#phase-3-eom-integration--reporting)
6. [Phase 4: Testing & Deployment (Weeks 10-12)](#phase-4-testing--deployment)
7. [Acceptance Criteria](#acceptance-criteria)
8. [Risk Mitigation](#risk-mitigation)

---

## Executive Summary

This implementation plan provides a complete, production-ready roadmap for building the **Financial Core** module in AquaMind, now extended for EoM processes (allocation, valuation, locking) based on Smolt requirements. The module addresses gaps in Chart of Accounts (CoA), Cost Center tracking, Budgeting, and month-end closing.

### Key Objectives

1. **Enable Financial Planning & EoM**: Tools for budgets, cost spreading (e.g., 50/50 rules), valuations (WAC roll-forwards), NAV postings, and period locking
2. **Maintain Architectural Integrity**: Separation from `finance` app; integrate with `batch` for biology (biomass/headcount)
3. **Support Scenario-Based Budgeting**: Link to `scenario` app for what-if EoM
4. **Deliver Production-Quality Code**: No temporaries; focus on idempotency, audits, and performance (<2 min EoM runs)

### Implementation Timeline

- **Total Duration**: 12 weeks (unchanged; redistributed for EoM)
- **Backend Development**: 8 weeks
- **Integration & Testing**: 4 weeks
- **Deployment**: Week 12

### Resource Requirements

- **Backend Developer**: 1 FTE for 12 weeks
- **Database Administrator**: 0.25 FTE for schema/migrations (add hypertable for ValuationRun)
- **QA Engineer**: 0.5 FTE (Weeks 8-12; extra for EoM workflows)
- **Finance SME**: 0.1 FTE for validation (e.g., 50/50 tests)

---

## Implementation Overview

### Architectural Principles

1. **Separation of Concerns**:
   - `finance` app = Operational reporting (harvest facts, intercompany, NAV exports)
   - `finance_core` app = Planning/budgeting/EoM (CoA, CostCenters, allocations, locking)

2. **Integration Over Duplication**:
   - Use `DimCompany` from `finance`; pull biology from `batch` for allocation bases
   - EoM exports to `finance` NAVExportBatch

3. **Django Best Practices**:
   - Code org: `apps/finance_core/` with `models/`, `serializers/`, `viewsets/`, `services/`
   - DRF for APIs; Celery for EoM jobs (allocation/valuation)
   - TimescaleDB for ValuationRun (time-series)

4. **API-First Design**:
   - RESTful; OpenAPI via drf-spectacular
   - Frontend-only access

### Technology Stack

- **Backend**: Django 4.2+ / DRF
- **Database**: PostgreSQL 14+ / TimescaleDB
- **Async**: Celery + Redis (for EoM computations)
- **Testing**: pytest / pytest-django
- **Migrations**: Django with RunSQL for hypertables

---

## Phase 1: Foundation (Weeks 1-3)

### Objective

Scaffold app and core data model (CoA, CostCenters, Budgets).

### Tasks

#### Week 1: App Scaffolding and Data Model Design

**Task 1.1: Create `finance_core` App**
- Run `python manage.py startapp finance_core`
- Add to INSTALLED_APPS; configure URLs (`finance_core/urls.py`)

**Task 1.2: Implement Core Models**
- AccountGroup (with allocation_rule JSON)
- Account (with cost_group Choice)
- CostCenter (with biology_link FK to batch_batch)
- Budget (with operating_unit CharField)
- BudgetEntry (with allocated_from self-FK, currency)

**Task 1.3: Migrations & Validation**
- Generate migrations; add indexes/constraints
- Implement clean() for consistency (e.g., company matches)

#### Week 2: Basic Serializers and ViewSets

**Task 2.1: Serializers**
- ModelSerializers for all; nested for hierarchies (e.g., group in Account)
- Custom fields (e.g., full_path computed)

**Task 2.2: ViewSets**
- CRUD for all resources; add filters (e.g., cost_group)
- Custom actions: by-type, active, by-cost-group, by-batch

**Task 2.3: Permissions**
- RBAC: IsAuthenticated; custom for locking (e.g., IsFinanceManager)

#### Week 3: Basic Testing & OpenAPI

**Task 3.1: Unit Tests**
- Model validations; serializer outputs
- Coverage >80%

**Task 3.2: Integration Tests**
- CRUD flows; hierarchy queries

**Task 3.3: OpenAPI**
- Run drf-spectacular; validate schema

---

## Phase 2: Core Features & Allocation (Weeks 4-6)

### Objective

Add budgeting CRUD, EoM allocation engine, and basic services.

### Tasks

#### Week 4: Budgeting Core

**Task 4.1: Budget/BudgetEntry ViewSets**
- List/create/retrieve/update/delete; bulk-create
- Filters: year, month, allocated_from

**Task 4.2: Custom Actions**
- Copy budget; summary by type
- Bulk import NAV CSV (idempotent parser for CostGroup/OperatingUnit/Amount)

**Task 4.3: Services Layer**
- budget_service.py: get_entries_for_month()

#### Week 5: Allocation Engine

**Task 5.1: Allocation Service**
- allocate_costs(): Implement 50/50 logic; preview/approve
- Fallbacks (e.g., equal if no biology); create child entries

**Task 5.2: Endpoint**
- POST /budgets/{id}/allocate/ (body: cost_group, preview bool)

**Task 5.3: Tests**
- Unit: Allocation math (with/without biology)
- Integration: Full spread for 10 rings

#### Week 6: Mortality & Basic Reports

**Task 6.1: Mortality Trigger**
- trigger_mortality_expense(): Manual P&L from batch_mortalityevent

**Task 6.2: Initial Reports**
- P&L projection; budget summary (with allocated totals)

**Task 6.3: OpenAPI Update**
- Regenerate schema; test endpoints

---

## Phase 3: EoM Integration & Reporting (Weeks 7-9)

### Objective

Implement valuation, locking, NAV exports, and full reports.

### Tasks

#### Week 7: Valuation & Locking

**Task 7.1: Models**
- Add PeriodLock, ValuationRun migrations
- Backfill opening values from historical Budgets

**Task 7.2: Services**
- compute_valuation_run(): Roll-forward formula; WAC calc
- Lock service: Override saves; reopen with version

**Task 7.3: Endpoints**
- POST /budgets/{id}/valuation-run/ (with mortality_expense)
- POST /periods/lock/

#### Week 8: NAV Integration & Transfers

**Task 8.1: Exports**
- generate_nav_export(): CSV/JSON for 8310/2211 (dimensions)
- Idempotent; link to finance NAVExportBatch

**Task 8.2: Transfers**
- Optional pricing toggle (default false); signal on batch transfer completion

**Task 8.3: Imports**
- Enhance bulk-import for NAV CSV validation/errors

#### Week 9: Advanced Reports

**Task 9.1: Movement & Valuation Reports**
- GET /reports/movement/ (Opening/Change/Closing + biology)
- GET /reports/ring-valuation/ (insurance-ready)

**Task 9.2: Scenario Link**
- Update Budget serializer for scenario; recompute on changes

**Task 9.3: Celery for EoM Jobs**
- Queue allocation/valuation; Redis broker

---

## Phase 4: Testing & Deployment (Weeks 10-12)

### Objective

Full QA, docs, and rollout.

### Tasks

#### Week 10: Comprehensive Testing

**Task 10.1: Unit/Integration**
- EoM workflows (import → allocate → value → lock)
- Edge: Missing biology, locked edits

**Task 10.2: E2E (Playwright)**
- Smolt EoM flow; Sea transfer (biology-only)

**Task 10.3: Performance**
- Load test: 100 rings EoM <2 min

#### Week 11: Documentation & Polish

**Task 11.1: User Guide/API Docs**
- Update with EoM sections; OpenAPI regen

**Task 11.2: Frontend Coordination**
- Expose new endpoints; basic EoM UI (wizard for allocate/lock)

#### Week 12: Deployment & Training

**Task 12.1: Staging Rollout**
- Migrate prod; seed test data (Smolt batches)

**Task 12.2: Training**
- Videos for EoM; feedback loop

**Task 12.3: Monitoring**
- Add logs for locks/allocations; alerts on failures

---

## Acceptance Criteria

### Backend

1. **Models**: All implemented (`AccountGroup` with rules, `CostCenter` with biology_link, `PeriodLock`, `ValuationRun`)
   - FKs/validations correct; HistoricalRecords()

2. **API**: All CRUD + customs (allocate, valuation-run, lock, import-nav, movement)
   - Filtering/searching/ordering; OpenAPI green

3. **EoM Integration**: Allocation (50/50 with fallbacks); valuation (WAC roll-forward); locking (blocks saves)
   - NAV export (8310/2211 CSV); biology pull from batch

4. **Testing**: >85% coverage; E2E for workflows; no regressions on core budgeting

### Frontend (Coordinated)

- EoM wizard (import → preview → approve → lock)
- Reports UI (movement tables, ring cards)

---

## Risk Mitigation

### Risk 1: Data Migration from FishTalk/NAV
**Mitigation**: Idempotent scripts; CSV fallback; stage test with historical Smolt CSVs

### Risk 2: Performance with Large EoM (100+ Rings)
**Mitigation**: Celery async; indexes on biology_link; bulk ops; hypertable for ValuationRun

### Risk 3: Biology/Finance Mismatches (e.g., Transfers, Mortality)
**Mitigation**: Optional pricing toggle; manual mortality trigger; signals for sync; user stories validated

### Risk 4: User Adoption (EoM Complexity)
**Mitigation**: Wizard UI; previews/approvals; training videos; "FishTalk mode" for legacy

### Risk 5: NAV Schema Drift
**Mitigation**: Validate CSVs at import; API future-proofing; SME review of postings

---

## Conclusion

This plan delivers Financial Core with EoM, agent-ready for Cursor.ai. Clear phases ensure no bloat.