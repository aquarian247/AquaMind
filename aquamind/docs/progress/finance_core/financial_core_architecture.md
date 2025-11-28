# Financial Core Architecture

**Version**: 2.0  
**Date**: November 26, 2025  
**Author**: Grok (based on Manus AI)  
**Purpose**: Define the complete architecture for AquaMind's Financial Core feature, providing Chart of Accounts, Cost Center management, Budgeting, and EoM processes (allocation, valuation, locking) for comprehensive financial planning, reporting, and closing in aquaculture operations, including Smolt/Freshwater and Sea/Farming subsidiaries.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architectural Context](#2-architectural-context)
3. [Data Model](#3-data-model)
4. [API Design](#4-api-design)
5. [Business Logic](#5-business-logic)
6. [Integration Architecture](#6-integration-architecture)
7. [Database Schema](#7-database-schema)
8. [Migration Strategy](#8-migration-strategy)
9. [Testing Strategy](#9-testing-strategy)
10. [Performance Considerations](#10-performance-considerations)

---

## 1. Executive Summary

### 1.1 Purpose

The **Financial Core** feature addresses critical gaps identified in the FishTalk feature analysis and Smolt EoM requirements: the absence of a **Chart of Accounts (CoA)**, **Cost Center** management, **Budgeting** functionality, and EoM processes for allocation, valuation, and period locking. This feature enables Finance Managers, Analysts, and Operators to:

- Define and manage the company's Chart of Accounts with standard account types (Asset, Liability, Revenue, Expense, Equity) and cost groups for allocation (e.g., Feed, Salaries with rules like 50% headcount + 50% biomass)
- Create and organize hierarchical Cost Centers for operational cost allocation (e.g., station > area > ring/container/project/batch)
- Enter and track monthly budgets by Account and Cost Center, supporting multi-year planning
- Perform EoM workflows: Import NAV costs via CSV/API, allocate pooled costs, compute cost-basis valuations (WAC roll-forward), generate NAV postings (e.g., Dr 8310 / Cr 2211), and enforce period locking with audited reopens
- Generate Budget vs. Actuals reports, movement reports (Opening/Change/Closing for cost + biology), and specialized valuations (e.g., ring-level for insurance)
- Support scenario integration for what-if analysis (e.g., biomass changes impacting allocations)
- Ensure compliance with audit trails, versioning, and subsidiary-specific rules (e.g., biology-only transfers to Sea)

This architecture extends the core planning focus to operational EoM, bridging operational data (e.g., Batch biomass) with financial closing while maintaining separation from the existing `finance` app.

### 1.2 Architectural Separation from Existing `finance` App

**Critical Design Principle**: The new `finance_core` app is **architecturally separate** from the existing `finance` app to avoid functional overlap and maintain clear separation of concerns.

| App | Purpose | Key Models |
|-----|---------|------------|
| **`finance`** (Existing) | Operational financial reporting, harvest facts aggregation, intercompany transaction management, NAV ERP export | `DimCompany`, `DimSite`, `FactHarvest`, `IntercompanyPolicy`, `IntercompanyTransaction`, `NAVExportBatch` |
| **`finance_core`** (New) | Financial planning, budgeting, CoA/Cost Center management, EoM allocation/valuation/locking, P&L projections | `AccountGroup`, `Account`, `CostCenter`, `Budget`, `BudgetEntry`, `PeriodLock`, `ValuationRun`, `CostProject` (extending CostCenter for batches) |

**Integration Points** (Not Overlaps):
1. **Budget vs. Actuals/EoM**: `finance_core` budgets/valuations compared against `finance` actuals (harvest revenue, intercompany costs); pull biology from `batch` for allocation
2. **Cost Allocation**: `finance_core` Cost Centers used to allocate `finance` intercompany transaction costs
3. **Dimensional Consistency**: Both apps reference `finance.DimCompany` for company/subsidiary-level aggregation (e.g., Freshwater/Smolt, Farming/Sea)
4. **NAV Exports**: Generate journals (e.g., 8310/2211) from EoM runs for `finance` export batching
5. **Transfers**: Optional pricing in batch transfer workflows (default biology-only per requirements; toggle per subsidiary)

### 1.3 Scope

**In Scope**:
- Hierarchical CoA with cost groups and allocation rules (e.g., Direct vs. Allocated; 50/50 headcount/biomass)
- Cost Center management with biology links (e.g., to Batch for biomass) and hierarchies (station > area > ring/project)
- Monthly budget entry and tracking (by Account × Cost Center × Year × Month), including ad-hoc/one-time costs
- EoM workflows: CSV/API imports from NAV, cost spreading engine, valuation roll-forwards (WAC), mortality P&L triggers, NAV postings, period locking with versioning
- Budget summary reports (by Account Type, Cost Center, Time Period) and specialized outputs (variances, movements, ring valuations)
- Budget vs. Actuals variance reporting (integration with `finance` app actuals and Batch biology)
- Multi-year budget management and templates for year-over-year planning (Phase 2)
- Scenario linking for what-if EoM (e.g., allocation under biomass scenarios)

**Out of Scope** (Handled by existing `finance` app or batch):
- Harvest financial facts aggregation or transaction recording (e.g., feed purchases, smolt transfers—pull as actuals)
- Intercompany transaction management (detect via policies; post via exports)
- NAV ERP export functionality (skeleton in `finance`; use for EoM journals)
- BI dimensional data management (views in `finance`; consume in reports)
- Real-time mortality registration (auto in batch; manual trigger for P&L)

### 1.4 Key Design Decisions

1. **New Django App**: Create `finance_core` as a separate app to maintain clear boundaries with `finance` and `batch`
2. **Hierarchical Structures**: Support two-level hierarchy for CoA (groups/accounts) and multi-level for CostCenters (e.g., station > area > ring); extend with CostProject for batch-specific (Smolt "projects")
3. **EoM Extensions**: Add dedicated models (PeriodLock, ValuationRun) and services for allocation/valuation; optional transfer pricing to resolve mismatches (default biology-only)
4. **Allocation Rules**: JSON fields in AccountGroup for flexibility (e.g., {mode: 'allocated', weights: {'headcount': 0.5, 'biomass': 0.5}}); fallbacks for missing data
5. **NAV Integration**: CSV primary for imports/exports (idempotent); API future via OData/webhooks
6. **Mortality Handling**: Auto-biology from batch; manual P&L trigger to separate ops from finance
7. **Compliance**: HistoricalRecords() on all models; versioning in PeriodLock for reopens

---

## 2. Architectural Context

The Financial Core integrates with AquaMind's PRD (financial planning gap) and data_model.md (e.g., batch_batch for projects/biomass, finance_factharvest for actuals). It supports Bakkafrost's structure: subsidiaries (Freshwater/Smolt, Farming/Sea via DimCompany), geographies (Faroe/Scotland), and roles (analysts lock periods). EoM aligns with Smolt requirements (cost groups, 50/50 allocation, biology-only transfers) while extensible to Sea. Builds on TRANSFER_WORKFLOW_ARCHITECTURE.md for transfers (optional pricing) and IMPLEMENTATION_PLAN.md for NAV exports.

---

## 3. Data Model

### 3.1 Core Models

#### 3.1.1 AccountGroup Model

**Purpose**: Hierarchical organization for CoA, with cost group rules for EoM allocation.

**Fields**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | BigAutoField | PK | Primary key |
| `code` | CharField(20) | UNIQUE, NOT NULL | Short code (e.g., "OPEX") |
| `name` | CharField(100) | NOT NULL | Descriptive name (e.g., "Operating Expenses") |
| `account_type` | Choice(ASSET, LIABILITY, EQUITY, REVENUE, EXPENSE) | NOT NULL | Standard type |
| `parent` | FK(AccountGroup) | NULL | Parent for nesting |
| `display_order` | PositiveIntegerField | Default 0 | Sorting order |
| `allocation_rule` | JSONField | BLANK | EoM rules (e.g., {"mode": "allocated", "weights": {"headcount": 0.5, "biomass": 0.5}}) |
| `created_at` | DateTimeField | auto_now_add | Creation timestamp |
| `updated_at` | DateTimeField | auto_now | Last update |

**Constraints**:
- UNIQUE(code)
- CHECK(parent.account_type = account_type if parent)

**Audit Trail**: HistoricalRecords() enabled

**Methods**:
- `get_full_path()`: e.g., "OPEX > FEED"

#### 3.1.2 Account Model

**Purpose**: Individual CoA line items, linked to groups and cost groups.

**Fields**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | BigAutoField | PK | Primary key |
| `code` | CharField(20) | UNIQUE, NOT NULL | Account code (e.g., "5100") |
| `name` | CharField(100) | NOT NULL | Name (e.g., "Smolt Feed") |
| `account_type` | Choice(ASSET, LIABILITY, EQUITY, REVENUE, EXPENSE) | NOT NULL | Type |
| `group` | FK(AccountGroup) | NOT NULL | Parent group |
| `description` | TextField | BLANK | Details |
| `cost_group` | Choice(Feed, Eggs, Salaries, Hires, Energy, Maintenance, Treatments, Insurance, Other, Depreciation) | BLANK | For EoM pooling |
| `is_active` | BooleanField | Default true | Active status |
| `created_at` | DateTimeField | auto_now_add | Creation |
| `updated_at` | DateTimeField | auto_now | Update |

**Constraints**:
- UNIQUE(code)
- CHECK(group.account_type = account_type)

**Audit Trail**: HistoricalRecords()

**Methods**:
- `get_cost_group_rule()`: Pull from group

#### 3.1.3 CostCenter Model

**Purpose**: Units for allocation (hierarchical; links to biology for bases like biomass).

**Fields**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | BigAutoField | PK | Primary key |
| `code` | CharField(20) | UNIQUE per company, NOT NULL | e.g., "STATION-01" |
| `name` | CharField(100) | NOT NULL | e.g., "Main Freshwater Station" |
| `company` | FK(DimCompany) | NOT NULL | Subsidiary (e.g., Freshwater) |
| `parent` | FK(CostCenter) | NULL | Hierarchy (e.g., area under station) |
| `biology_link` | FK(batch_batch) | NULL | Batch/project for headcount/biomass |
| `description` | TextField | BLANK | Details |
| `is_active` | BooleanField | Default true | Status |
| `created_at` | DateTimeField | auto_now_add | Creation |
| `updated_at` | DateTimeField | auto_now | Update |

**Constraints**:
- UNIQUE(code, company)

**Audit Trail**: HistoricalRecords()

**Methods**:
- `get_child_centers()`: Recursive hierarchy
- `get_biomass()`: Pull from linked Batch

#### 3.1.4 Budget Model

**Purpose**: Container for monthly plans/EoM runs.

**Fields**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | BigAutoField | PK | Primary key |
| `name` | CharField(100) | NOT NULL | e.g., "2025 Smolt EoM" |
| `year` | PositiveIntegerField | NOT NULL | Fiscal year |
| `company` | FK(DimCompany) | NOT NULL | Subsidiary |
| `scenario` | FK(scenario_scenario) | NULL | What-if link |
| `description` | TextField | BLANK | Notes |
| `is_active` | BooleanField | Default false | Active for period |
| `entry_count` | PositiveIntegerField | Computed | Number of entries |
| `total_budgeted` | Decimal(14,2) | Computed | Sum of entries |
| `created_at` | DateTimeField | auto_now_add | Creation |
| `updated_at` | DateTimeField | auto_now | Update |
| `created_by` | FK(auth.User) | NOT NULL | Creator |

**Constraints**:
- UNIQUE(company, year, is_active=true)

**Audit Trail**: HistoricalRecords()

**Methods**:
- `get_entries_for_month(month)`: Filter by month

#### 3.1.5 BudgetEntry Model

**Purpose**: Monthly amounts by Account/CostCenter; supports allocation chains.

**Fields**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | BigAutoField | PK | Primary key |
| `budget` | FK(Budget) | PROTECT, NOT NULL | Parent budget |
| `account` | FK(Account) | PROTECT, NOT NULL | Account |
| `cost_center` | FK(CostCenter) | PROTECT, NOT NULL | Center |
| `year` | PositiveIntegerField | NOT NULL | Year |
| `month` | PositiveSmallIntegerField | 1-12, NOT NULL | Month |
| `budgeted_amount` | Decimal(14,2) | NOT NULL, >=0 | Amount (in company currency) |
| `currency` | CharField(3) | NOT NULL, ISO 4217 | e.g., "DKK" |
| `allocated_from` | FK(BudgetEntry) | NULL | Parent for spreading |
| `notes` | TextField | BLANK | Details (e.g., "One-time repair") |
| `created_by` | FK(auth.User) | SET_NULL, NULL | Creator |
| `created_at` | DateTimeField | auto_now_add | Creation |
| `updated_at` | DateTimeField | auto_now | Update |

**Constraints**:
- UNIQUE(budget, account, cost_center, year, month)
- CHECK(month >=1 AND month <=12)
- CHECK(year >=2020 AND year <=2100)
- CHECK(account.company = budget.company)
- CHECK(cost_center.company = budget.company)
- CHECK(currency = budget.company.currency OR overridden)

**Audit Trail**: HistoricalRecords()

**Methods**:
- `clean()`: Validate consistency
- `get_period()`: "2025-01"

**Indexes**:
- (company, year, month)
- (account, year)
- (cost_center, year)

#### 3.1.6 PeriodLock Model

**Purpose**: EoM locking (hard block on edits; audited reopens).

**Fields**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | BigAutoField | PK | Primary key |
| `company` | FK(DimCompany) | NOT NULL | Subsidiary |
| `operating_unit` | CharField(50) | NOT NULL | Station/area code |
| `year` | PositiveIntegerField | NOT NULL | Year |
| `month` | PositiveSmallIntegerField | 1-12, NOT NULL | Month |
| `status` | Choice('open', 'locked') | NOT NULL | State |
| `locked_by` | FK(auth.User) | NULL | Locker |
| `locked_at` | DateTimeField | auto_now_add if locked | Timestamp |
| `reopen_reason` | TextField | BLANK | For reopens |
| `version` | PositiveIntegerField | Default 1 | Rerun version |
| `created_at` | DateTimeField | auto_now_add | Creation |
| `updated_at` | DateTimeField | auto_now | Update |

**Constraints**:
- UNIQUE(company, operating_unit, year, month)

**Audit Trail**: HistoricalRecords()

**Methods**:
- `lock()`: Set status='locked'; signal to block edits
- `reopen(reason)`: Increment version; audit log

#### 3.1.7 ValuationRun Model

**Purpose**: EoM roll-forward computations and NAV postings.

**Fields**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | BigAutoField | PK | Primary key |
| `budget` | FK(Budget) | NOT NULL | Linked budget |
| `period` | DateField | NOT NULL | EoM date (year-month) |
| `opening_value` | Decimal(14,2) | NOT NULL | Prior closing |
| `additions` | Decimal(14,2) | NOT NULL | Eggs + allocations |
| `reductions` | Decimal(14,2) | NOT NULL | Transfers + mortality |
| `closing_value` | Decimal(14,2) | Computed | Roll-forward total |
| `wac_per_kg` | Decimal(10,4) | Computed | Weighted average cost |
| `biomass_kg` | Decimal(12,2) | NOT NULL | From Batch |
| `headcount` | PositiveIntegerField | NOT NULL | From Batch |
| `mortality_expensed` | Decimal(14,2) | Default 0 | Manual P&L amount |
| `nav_posting` | JSONField | BLANK | e.g., {"dr": "8310", "cr": "2211", "dimensions": {...}} |
| `run_by` | FK(auth.User) | NOT NULL | Runner |
| `created_at` | DateTimeField | auto_now_add | Creation |
| `updated_at` | DateTimeField | auto_now | Update |

**Audit Trail**: HistoricalRecords()

**Methods**:
- `compute_roll_forward()`: Apply formula; integrate Batch data
- `generate_nav_export()`: Create CSV/JSON for posting

**Indexes**:
- (budget, period)

---

## 4. API Design

All endpoints follow DRF conventions (kebab-case, pagination, filtering). Base: `/api/v1/finance-core/`.

### 4.1 Account Group Endpoints

#### List Account Groups
**GET /account-groups/**
- Query: `account_type`, `parent`, `search`, `ordering`, `page`, `page_size`
- Response: Paginated list with `allocation_rule`

#### Create/Update/Delete
As original; add `allocation_rule` in body.

### 4.2 Account Endpoints

#### List Accounts
**GET /accounts/**
- Query: `account_type`, `group`, `cost_group`, `is_active`, `search`, `ordering`
- Response: Includes `cost_group`

#### Custom: By Cost Group
**GET /accounts/by-cost-group/**
- Query: `cost_group` (required, e.g., "Feed")

### 4.3 Cost Center Endpoints

#### List Cost Centers
**GET /cost-centers/**
- Query: `company`, `parent`, `biology_link`, `is_active`, `search`, `ordering`

#### Custom: By Batch
**GET /cost-centers/by-batch/**
- Query: `batch_id` (required); auto-creates for new projects

### 4.4 Budget Endpoints

#### List Budgets
**GET /budgets/**
- Query: `year`, `company`, `scenario`, `is_active`, `search`, `ordering`

#### Create Budget
**POST /budgets/**
- Body: As original; add `operating_unit` for EoM

#### Retrieve Budget (with Entries)
**GET /budgets/{id}/**
- Includes entries with `allocated_from`

#### Custom: Allocate Costs
**POST /budgets/{id}/allocate/**
- Body: `{cost_group: "Salaries", preview: true}`
- Response: Preview table; approve to post

#### Custom: Run Valuation
**POST /budgets/{id}/valuation-run/**
- Body: `{period: "2025-01", mortality_expense: 5000}`
- Response: ValuationRun object + NAV export

#### Custom: Lock Period
**POST /periods/lock/**
- Body: `{company_id: 1, operating_unit: "STATION-01", year: 2025, month: 1}`
- Response: Locked status

### 4.5 Budget Entry Endpoints

#### List Entries
**GET /budget-entries/**
- Query: `budget`, `currency`, `account`, `cost_center`, `month`, `allocated_from`

#### Bulk Create/Import NAV
**POST /budget-entries/bulk-import/**
- Body: Multipart CSV; validates CostGroups
- Response: Created entries + errors

### 4.6 Reporting Endpoints

#### Budget Summary
**GET /reports/budget-summary/**
- Query: `budget_id`; includes EoM allocations

#### P&L Projection
**GET /reports/pl-projection/**
- Query: `budget_id`; factors in valuations

#### Movement Report
**GET /reports/movement/**
- Query: `budget_id`, `period`, `cost_center`; cost + biology (headcount/kg/weight)

#### Ring Valuation
**GET /reports/ring-valuation/**
- Query: `cost_center_id` (ring); for insurance (closing value at WAC)

---

## 5. Business Logic

### 5.1 Allocation Engine
In `services/allocation_service.py`:
```python
from decimal import Decimal

def allocate_costs(budget_id, cost_group):
    budget = Budget.objects.get(id=budget_id)
    parent_entries = BudgetEntry.objects.filter(
        budget=budget, account__cost_group=cost_group, allocated_from__isnull=True
    )
    total_amount = sum(e.budgeted_amount for e in parent_entries)
    
    if cost_group == 'Eggs':  # Direct
        for entry in parent_entries:
            # Assign directly to linked projects
            pass
    else:  # Allocated
        child_centers = CostCenter.objects.filter(parent=budget.operating_unit, biology_link__isnull=False)
        total_weight = Decimal('0')
        weights = {}
        for center in child_centers:
            headcount = center.biology_link.headcount or 0
            biomass = center.biology_link.biomass_kg or 0
            weight = (Decimal(headcount) * Decimal('0.5') + Decimal(biomass) * Decimal('0.5'))
            weights[center.id] = weight
            total_weight += weight
        
        for parent in parent_entries:
            for center_id, weight in weights.items():
                if total_weight > 0:
                    allocated = parent.budgeted_amount * (weight / total_weight)
                    child_entry = BudgetEntry(
                        budget=budget, account=parent.account, cost_center_id=center_id,
                        year=parent.year, month=parent.month, budgeted_amount=allocated,
                        allocated_from=parent, currency=parent.currency
                    )
                    child_entry.save()
                else:
                    # Fallback: equal split
                    allocated = parent.budgeted_amount / len(child_centers)
                    # Create equal entries
```

### 5.2 Valuation Roll-Forward
In `services/valuation_service.py`:
```python
def compute_valuation_run(budget_id, period, mortality_expense=Decimal('0')):
    budget = Budget.objects.get(id=budget_id)
    prev_period = period.replace(day=1) - timedelta(days=1)
    opening = ValuationRun.objects.filter(budget=budget, period=prev_period).first()
    opening_value = opening.closing_value if opening else Decimal('0')
    
    additions = sum(
        e.budgeted_amount for e in BudgetEntry.objects.filter(
            budget=budget, month=period.month, year=period.year,
            account__cost_group__in=['Eggs', 'Allocated Groups']
        )
    )
    
    reductions = sum(
        e.budgeted_amount for e in BudgetEntry.objects.filter(
            budget=budget, month=period.month, year=period.year,
            account__cost_group__in=['Transfers', 'Mortality']
        )
    ) + mortality_expense
    
    closing_value = opening_value + additions - reductions
    
    # Biology from Batch
    total_centers = CostCenter.objects.filter(parent=budget.operating_unit)
    biomass_kg = sum(c.biology_link.biomass_kg for c in total_centers if c.biology_link)
    headcount = sum(c.biology_link.headcount for c in total_centers if c.biology_link)
    
    wac_per_kg = closing_value / biomass_kg if biomass_kg > 0 else Decimal('0')
    
    run = ValuationRun(
        budget=budget, period=period,
        opening_value=opening_value, additions=additions, reductions=reductions,
        closing_value=closing_value, wac_per_kg=wac_per_kg,
        biomass_kg=biomass_kg, headcount=headcount, mortality_expensed=mortality_expense,
        run_by=request.user  # From view context
    )
    run.save()
    
    # Optional NAV posting
    generate_nav_export(run)
    
    return run
```

### 5.3 Period Locking
In `models.py` (override):
```python
class BudgetEntry(models.Model):
    # ... fields ...
    
    def save(self, *args, **kwargs):
        if self.budget.is_locked:  # Check via PeriodLock
            lock = PeriodLock.objects.get(company=self.budget.company, operating_unit=self.cost_center.operating_unit, year=self.year, month=self.month)
            if lock.status == 'locked' and not self._state.adding:  # Edit attempt
                raise ValidationError("Period locked; contact admin for reopen.")
        super().save(*args, **kwargs)
```

### 5.4 Mortality Trigger
In `services/mortality_service.py`:
```python
def trigger_mortality_expense(cost_center_id, amount):
    # Pull from batch_mortalityevent
    events = MortalityEvent.objects.filter(assignment__cost_center_id=cost_center_id, date__month=month)
    audited_amount = sum(e.amount for e in events if e.audited)  # Manual audit flag
    if amount != audited_amount:
        raise ValidationError("Amount must match audited mortalities.")
    
    # Create reduction Entry
    entry = BudgetEntry(budget=active_budget, account=mortality_account, cost_center_id=cost_center_id,
                        year=year, month=month, budgeted_amount=amount, notes="Manual P&L trigger")
    entry.save()
    
    # Export to NAV (2211)
```

---

## 6. Integration Architecture

- **With `finance` App**: Pull actuals/FactHarvest for variances; push EoM postings to NAVExportBatch
- **With `batch` App**: Biology links (biomass/headcount from batch_batchcontainerassignment); signals on new Batch → auto CostProject
- **With NAV**: CSV import (CostGroup/OperatingUnit/Amount parser); export journals (JSON/CSV for 8310/2211 with dimensions: OperatingUnit, PSG="Smolt")
- **Transfers (from TRANSFER_WORKFLOW_ARCHITECTURE.md)**: On completion, optional financial posting (toggle: biology-only default; if priced, create IntercompanyTransaction)
- **Scenarios**: Link Budget to scenario_scenario; recompute allocations/valuations on changes
- **Audit**: HistoricalRecords() on all; signals for lock/reopen logs

---

## 7. Database Schema

- **Tables**: finance_core_accountgroup, finance_core_account, finance_core_costcenter, finance_core_budget, finance_core_budgetentry, finance_core_periodlock, finance_core_valuationrun
- **Hypertables**: Consider for ValuationRun (partition by period)
- **Indexes**: As in models; add on biology_link, allocated_from
- **Constraints**: FKs PROTECT; uniqueness for locks/entries

---

## 8. Migration Strategy

1. **Phase 1 (Week 1-2)**: Add core models (AccountGroup with allocation_rule, CostCenter with biology_link); migrate existing CoA if any
2. **Phase 2 (Week 3-4)**: Add PeriodLock, ValuationRun; backfill from Budgets (e.g., set opening_values)
3. **Phase 3 (Week 5)**: Data mapping (CostGroups to enums); idempotent import script for NAV historicals
4. **Rollback**: Reversible migrations; test on staging with sample Smolt data

---

## 9. Testing Strategy

### 9.1 Unit Tests (pytest)
- Allocation: Test 50/50 with/without biology (fallbacks)
- Valuation: Math edge cases (zero biomass, mortality)
- Locking: Save blocks on locked periods

### 9.2 Integration Tests
- EoM Workflow: Import CSV → allocate → value → lock → export (mock NAV)
- Transfers: Biology-only vs. priced (signal to Intercompany)

### 9.3 E2E Tests (Playwright)
- Full Smolt EoM: New project → import → finalize → report
- Coverage: >85%; include RBAC (analyst locks, admin reopens)

### 9.4 Performance Tests
- Large EoM: 100 rings, <2 min allocation

---

## 10. Performance Considerations

### 10.1 Query Optimization
- Bulk ops for allocations (bulk_create/update)
- Indexes on frequent filters (company/year/month, biology_link)
- Denormalize: Store computed biomass in CostCenter (update via signals)

### 10.2 Bulk Operations
Bad: Loop saves
```python
# Avoid
for budget in budgets:
    budget.budgeted_amount *= 1.05
    budget.save()
```
Good: Bulk
```python
budgets = BudgetEntry.objects.filter(company_id=1, year=2025, month=1)
for budget in budgets:
    budget.budgeted_amount *= 1.05
BudgetEntry.objects.bulk_update(budgets, ['budgeted_amount'])
```

### 10.3 Caching Strategy (Phase 2)
- Cache EoM summaries (Redis; key: f'eom_summary:{company}:{year}:{month}')
- Invalidate on lock/unlock or Batch updates

### 10.4 Database Connection Pooling
- `CONN_MAX_AGE: 600` in settings.py
- PgBouncer for high-concurrency EoM runs

---

## Conclusion

This architecture provides a robust blueprint for Financial Core, fully incorporating Smolt EoM requirements while scalable for Sea. It ensures compliance (locking, audits) and efficiency (automation). Next: Update implementation plan for phases.