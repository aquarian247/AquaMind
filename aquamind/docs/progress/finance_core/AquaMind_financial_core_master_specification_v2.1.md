# AquaMind Financial Core — Complete Specification & Implementation Guide v2.1

**Version**: 2.1  
**Date**: March 11, 2026  
**Status**: Production-Ready (Smolt EoM + Planning/Budgeting)  
**Scope**: Full replacement of the FishTalk Finance costing/valuation/closing subset used at Bakkafrost (planning + monthly budgeting + Smolt EoM workflows). Sea/Farming EoM is a future extension.

**Primary Authoritative Source**: This document. All other older MD files are now obsolete.

---

## Table of Contents

1. [Executive Summary & PRD Overview](#1-executive-summary--prd-overview)
2. [Detailed Functional Requirements & Workflows](#2-detailed-functional-requirements--workflows)
3. [Architecture & Data Model (Aligned to Existing Schema)](#3-architecture--data-model)
4. [API Specification](#4-api-specification)
5. [UI Specification & User Guide](#5-ui-specification--user-guide)
6. [12-Week Implementation Plan](#6-12-week-implementation-plan)
7. [Acceptance Criteria, Risks & Open Items](#7-acceptance-criteria-risks--open-items)

---

## 1. Executive Summary & PRD Overview

**Goal**: Give finance users the exact monthly cost-assignment workflow they have in FishTalk — but modern, fast, auditable, and integrated with real-time biology.

**What we keep from FishTalk Finance** (and only this subset):
- NAV CSV import (CostGroup + OperatingUnit + Amount)
- 50/50 opening headcount + biomass allocation (exact formula)
- Per-project WAC roll-forward valuation
- Closing stock value by site (Operating Unit) → delta NAV posting (8310/2211 or 8313/2211)
- Manual mortality impairment % (one-off)
- Hard period lock (finance + biology)

**What we add** (because we can):
- Real-time biology sync from `batch_batch` / `batch_batchcontainerassignment`
- Allocation preview + approve step
- One-click EoM wizard
- Versioned ValuationRun + idempotent exports
- Celery async (<2 min for 100+ rings)
- Hard locks that block edits in both finance and batch apps

**Architectural Separation** (unchanged from v2.0):
- `finance_core` app = planning + budgeting + EoM
- Existing `finance` app = operational reporting + NAV exports + harvest facts

**Biology Source of Truth**:
- Headcount & biomass_kg from `batch_batchcontainerassignment` (opening-of-month values)
- New cost projects auto-created on new batches via signals

---

## 2. Detailed Functional Requirements & Workflows

### 2.1 Pre-Close Checks
- Detect new `batch_batch` created in period without linked cost project
- One-click wizard to create CostCenter (project) with naming convention `<Site>-<InputNumber>:<MonthShort>`
- Many-to-one batch → cost project support

### 2.2 NAV Cost Import (Idempotent Replace-Period)
- CSV columns: `CostGroup`, `OperatingUnit`, `Amount`
- Locked period → 423 Locked
- Unknown CostGroup/OperatingUnit → hard error with row list

### 2.3 Allocation Engine (Exact 50/50)
```python
share_i = 0.5 * (count_i / Σcount) + 0.5 * (biomass_i / Σbiomass)
```
- Fallbacks (zero biology) and preview table required.

## 2.4 Valuation & Mortality

- Per-project WAC roll-forward valuation stored in `ValuationRun`
- Formula: `Closing = Opening + Eggs (direct) + Allocations − Transfers-out − Mortality/Adjustments`
- Weighted Average Cost (WAC) per kg calculated automatically
- Manual one-off mortality impairment % per cost project (typically ≥20%)
- Applied as reduction to closing value before NAV posting
- No automatic P&L impact from normal/routine mortality (only manual impairment triggers expense)
- Biology values (headcount and biomass_kg) pulled from `batch_batchcontainerassignment` at opening of month

## 2.5 NAV Delta Export (Mode B)

- Closing stock value aggregated by site (Operating Unit / cost center group)
- Delta = current period closing value − previous period closing value
- Two-line balancing journal per site + PSG dimension:
  - **Smolt**: Inventory account `8313` Dr / `2211` Cr
  - **Sea**: Inventory account `8310` Dr / `2211` Cr
  - PSG values: `SMOLT`, `FISKUR`, `LÍVFISKUR`
- Output CSV matches NAV General Journal format exactly
- Idempotent and versioned via `ValuationRun.nav_posting` JSON field

## 2.6 Period Locking

- Hard lock via `PeriodLock` model (company + operating_unit + year + month)
- Once locked, system blocks imports, allocations, valuation runs, budget edits, and biology changes
- Admin-only reopen with mandatory reason and version increment

**Full EoM Wizard Flow** (flagship UI):
1. Import NAV CSV  
2. Review & create missing cost projects (auto + one-click wizard)  
3. Allocation preview (with share % and totals)  
4. Approve allocation  
5. Valuation run (optional mortality impairment)  
6. NAV export preview + download  
7. Lock period  

## 2.7 Raised Ambition & Configurability Features

- One-click EoM Wizard (full stepper with real-time validation)
- Auto cost-project creation wizard (naming templates + batch linking)
- Real-time biology validation with configurable fallback (“equal split” override instead of hard error)
- Versioned re-run capability — “Re-calculate from month X” on any unlocked period
- Anomaly alerts — automatic flags when allocation share deviates >5% from previous month or rule expectation
- Ring-level insurance report — closing WAC + biomass per ring (exportable)

**Allocation Rule Engine (Highly Configurable)**  
Allocation is no longer hardcoded.

- Rules live in a new `AllocationRule` model (linked to `AccountGroup` or `CostCenter`) with JSON definition:
  ```json
  {
    "mode": "weighted",
    "weights": { "headcount": 0.5, "biomass": 0.5 },
    "fallback": "equal_split",
    "effective_from": "2025-01-01"
  }

Supports:

* Global rules per cost group
* Per-CostCenter overrides (e.g. one station uses 70/30)
* Per-Period overrides (exceptional month)
* **Historical immutability**: When a `ValuationRun` is created, the exact rule snapshot is stored in the run record. Future rule changes never affect locked or historical periods.

---

## 3. Architecture & Data Model (Aligned to Existing Schema)

**New `finance_core` app** (kept completely separate from existing `finance` app).

### 3.1 New Core Models
- **AccountGroup** & **Account** — hierarchical CoA with `cost_group` field
- **CostCenter** — hierarchical (station → project), with `biology_link` FK
- **Budget** & **BudgetEntry** — monthly entries with `allocated_from` self-FK
- **PeriodLock** — enforces hard locks
- **ValuationRun** — TimescaleDB hypertable
- **AllocationRule** — new configurable rule model (see 2.7)

All models use `HistoricalRecords()`.

### 3.2 Integration with Existing Data Model
- Biology from `batch_batchcontainerassignment`
- Company data from `finance_dimcompany`
- NAV export linked to existing `finance_navexportbatch`

### 3.3 Key Design Decisions
- Idempotent imports, Celery jobs, save() overrides for locks

### 3.4 Configuration & Administration (Compliance-First)
**Admin area**: `/finance/admin/configuration`

- Allocation Rules Editor (live preview calculator)
- Rule versioning & effective dates
- Safe mode (blocks changes affecting locked periods)
- Full audit trail on every rule change

---

## 4. API Specification

**Base URL**: `/api/v1/finance-core/`

**Key EoM Endpoints**:
- `POST /budgets/{id}/allocate/`
- `POST /budgets/{id}/valuation-run/`
- `POST /periods/lock/`
- `POST /budget-entries/bulk-import/`
- `GET /reports/movement/`
- `GET /reports/ring-valuation/`
- `GET /reports/nav-export-preview/`

All standard CRUD, filtering, and copy endpoints remain.

---

## 5. UI Specification & User Guide

**Main Route**: `/finance/planning`

**Tabs**:
1. Chart of Accounts
2. Cost Centers
3. Budgeting (spreadsheet grid with auto-save)
4. **EoM Wizard** (flagship tab)

**EoM Wizard**:
- Stepper interface
- Real-time validation
- Preview tables
- One-click actions for allocation, valuation, export, lock

**User Guide Summary**:
- Budgeting grid works as before
- New EoM section provides step-by-step guidance
- Configuration admin page for safe rule changes

---

## 6. 12-Week Implementation Plan

**Phase 1 (Weeks 1-3)**: Foundation (models, CoA, Cost Centers, basic Budgeting)  
**Phase 2 (Weeks 4-6)**: Budgeting + Allocation Engine (configurable rules)  
**Phase 3 (Weeks 7-9)**: EoM Core (ValuationRun, PeriodLock, NAV import/export, Celery)  
**Phase 4 (Weeks 10-12)**: EoM Wizard UI, admin config page, full testing, performance tuning, deployment

---

## 7. Acceptance Criteria, Risks & Open Items

### Acceptance Criteria
- Allocation matches exact formula with configurable rules and historical snapshots
- NAV export CSV is NAV-ready and balances to zero
- Period lock blocks all relevant writes
- EoM for 100+ rings completes in < 2 minutes
- Rule changes cannot affect locked periods
- Full audit trail on every change

### Risks & Mitigations
- Biology/finance desync → strong signals + preview step
- Performance → bulk operations + Celery
- User adoption → wizard + training videos + “FishTalk mode” toggle

### Open Items
- Full Sea/Farming EoM workflow
- Broodstock-specific handling

**This document is the single source of truth.**  
Ready for immediate implementation.

**End of Document**