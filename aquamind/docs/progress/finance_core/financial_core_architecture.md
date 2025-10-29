# Financial Core Architecture

**Version**: 1.0  
**Date**: October 28, 2025  
**Author**: Manus AI  
**Purpose**: Define the complete architecture for AquaMind's Financial Core feature, providing Chart of Accounts, Cost Center management, and Budgeting capabilities to support comprehensive financial planning and reporting.

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

The **Financial Core** feature addresses a critical gap identified in the FishTalk feature analysis: the absence of a **Chart of Accounts (CoA)**, **Cost Center** management, and **Budgeting** functionality in AquaMind. This feature enables Finance Managers to:

- Define and manage the company's Chart of Accounts with standard account types (Asset, Liability, Revenue, Expense, Equity)
- Create and organize Cost Centers for departmental/operational cost allocation
- Enter and track monthly budgets by Account and Cost Center
- Generate Budget vs. Actuals reports by comparing budgets against operational data
- Support multi-year financial planning and variance analysis

### 1.2 Architectural Separation from Existing `finance` App

**Critical Design Principle**: The new `finance_core` app is **architecturally separate** from the existing `finance` app to avoid functional overlap and maintain clear separation of concerns.

| App | Purpose | Key Models |
|-----|---------|------------|
| **`finance`** (Existing) | Operational financial reporting, harvest facts aggregation, intercompany transaction management, NAV ERP export | `DimCompany`, `DimSite`, `FactHarvest`, `IntercompanyPolicy`, `IntercompanyTransaction`, `NAVExportBatch` |
| **`finance_core`** (New) | Financial planning, budgeting, Chart of Accounts management, Cost Center tracking, P&L projections | `Account`, `CostCenter`, `Budget`, `BudgetTemplate` (Phase 2) |

**Integration Points** (Not Overlaps):
1. **Budget vs. Actuals**: `finance_core` budgets compared against `finance` actuals (harvest revenue, intercompany costs)
2. **Cost Allocation**: `finance_core` cost centers used to allocate `finance` intercompany transaction costs
3. **Dimensional Consistency**: Both apps reference `finance.DimCompany` for company-level aggregation

### 1.3 Scope

**In Scope**:
- Chart of Accounts (CoA) with hierarchical account structure (account groups/categories)
- Cost Center management with hierarchical organization
- Monthly budget entry and tracking (by Account × Cost Center × Year × Month)
- Budget summary reports (by Account Type, Cost Center, Time Period)
- Budget vs. Actuals variance reporting (integration with `finance` app actuals)
- Multi-year budget management
- Budget templates for year-over-year planning (Phase 2)

**Out of Scope** (Handled by existing `finance` app):
- Harvest financial facts aggregation
- Intercompany transaction management
- NAV ERP export functionality
- BI dimensional data management

### 1.4 Key Design Decisions

1. **New Django App**: Create `finance_core` as a separate app to maintain clear boundaries
2. **Hierarchical Account Structure**: Support account groups/categories for P&L and Balance Sheet organization
3. **Monthly Granularity**: Budget entries at monthly level (can aggregate to quarterly/yearly)
4. **Flexible Cost Center Hierarchy**: Support parent-child cost center relationships for departmental organization
5. **Integration via Foreign Keys**: Link to existing `finance.DimCompany` for company-level budgets
6. **Audit Trail**: Use `django-simple-history` for all models to track budget changes
7. **API-First Design**: REST API with DRF, following AquaMind API standards (kebab-case, filtering, searching)


### 1.5 Potential Gaps and Mitigations (optional)

**There are potentially minor gaps for aquaculture-specific spreading**:

1. **Granularity**: CostCenters can go down to container level, but if containers are dynamic (e.g., added/removed), add a capacity or biomass field to CostCenter for allocation bases. (Easy extension: Add in a migration.)
2. **Complex Rules**: Basic spreading (e.g., equal split) is supported via services, but advanced (e.g., weighted by usage) might need extra fields (e.g., allocation_weight on CostCenter). Mitigate by starting simple and iterating.
3. **NAV/GL Sync**: For actuals, ensure "finance_core" exports allocated budgets to NAV's cost allocation journals. Gap: No built-in reconciliation yet—add a Variance Report endpoint comparing budgeted allocations to NAV actuals.
4. **Performance**: For large farms (e.g., 100 halls × 25 areas × 50 containers = 125k CostCenters), hierarchical queries could slow; use recursive CTEs or libraries like django-treebeard for optimization.
5. **UI/Frontend**: The tabbed interface supports this (e.g., select CostCenter hierarchy in Budgeting grid), but add a "Spread Cost" modal for bulk allocation.

---

## 2. Architectural Context

### 2.1 System Architecture Overview

AquaMind follows a **Django REST Framework (DRF) + React** architecture:

- **Backend**: Django 4.2+ with PostgreSQL 15 (TimescaleDB extension)
- **API Layer**: Django REST Framework 3.14+ with standardized ViewSets and Serializers
- **Frontend**: React 18 + TypeScript with TanStack Query for server state management
- **Database**: PostgreSQL with TimescaleDB for time-series data (not used in `finance_core`)

### 2.2 Existing `finance` App Context

The existing `finance` app provides:
- **Dimensional Data**: `DimCompany` (legal entities by geography + subsidiary), `DimSite` (operational sites)
- **Harvest Facts**: `FactHarvest` (aggregated harvest events for BI reporting)
- **Intercompany Management**: `IntercompanyPolicy` (pricing rules), `IntercompanyTransaction` (cross-subsidiary transactions)
- **ERP Integration**: `NAVExportBatch`, `NAVExportLine` (export to Microsoft Dynamics NAV)

**Key Insight**: The `finance` app is a **reporting and integration layer**, not a general ledger. It does NOT provide:
- Chart of Accounts
- Cost Center management
- Budgeting functionality
- P&L or Balance Sheet structures

### 2.3 `finance_core` App Positioning

The `finance_core` app fills the **financial planning gap** by providing:
- **Chart of Accounts (CoA)**: The foundational structure for all financial reporting
- **Cost Centers**: Organizational units for cost allocation and departmental budgeting
- **Budgeting**: Monthly budget entry, tracking, and variance analysis

**Relationship to `finance` App**:
- `finance_core` defines the **budget** (planned financial performance)
- `finance` app captures the **actuals** (realized financial performance from operations)
- Integration layer (Phase 2) compares budget vs. actuals for variance reporting

### 2.4 App Structure

Following AquaMind's modular Django app organization:

```
aquamind/
├── apps/
│   ├── finance/          # Existing app (operational financial reporting)
│   │   ├── models.py     # DimCompany, FactHarvest, IntercompanyPolicy, etc.
│   │   ├── api/
│   │   │   ├── serializers/
│   │   │   ├── viewsets/
│   │   │   └── routers.py
│   │   └── services/     # Business logic (dimension mapping, NAV export)
│   │
│   └── finance_core/     # NEW app (financial planning and budgeting)
│       ├── models.py     # Account, CostCenter, Budget
│       ├── api/
│       │   ├── serializers/
│       │   │   ├── account_serializer.py
│       │   │   ├── cost_center_serializer.py
│       │   │   └── budget_serializer.py
│       │   ├── viewsets/
│       │   │   ├── account_viewset.py
│       │   │   ├── cost_center_viewset.py
│       │   │   └── budget_viewset.py
│       │   ├── filters/
│       │   │   ├── account_filter.py
│       │   │   ├── cost_center_filter.py
│       │   │   └── budget_filter.py
│       │   └── routers.py
│       ├── services/     # Business logic (budget calculations, variance analysis)
│       │   ├── budget_service.py
│       │   └── variance_service.py
│       ├── migrations/
│       ├── tests/
│       └── admin.py
```

---

## 3. Data Model

### 3.1 Entity Relationship Diagram (ERD)

```
┌─────────────────────┐
│  finance.DimCompany │ (Existing)
│  ─────────────────  │
│  company_id (PK)    │
│  geography_id (FK)  │
│  subsidiary         │
│  display_name       │
│  currency           │
└──────────┬──────────┘
           │
           │ 1:N
           │
┌──────────▼──────────┐         ┌─────────────────────┐
│  Account            │         │  CostCenter         │
│  ─────────────────  │         │  ─────────────────  │
│  id (PK)            │         │  id (PK)            │
│  company_id (FK)    │         │  company_id (FK)    │
│  code (UNIQUE)      │         │  code (UNIQUE)      │
│  name               │         │  name               │
│  account_type       │         │  parent_id (FK)     │
│  parent_id (FK)     │         │  is_active          │
│  is_active          │         │  created_at         │
│  created_at         │         │  updated_at         │
│  updated_at         │         └──────────┬──────────┘
└──────────┬──────────┘                    │
           │                               │
           │ N:1                           │ N:1
           │                               │
           │         ┌─────────────────────▼───────┐
           └────────►│  Budget                     │
                     │  ─────────────────────────  │
                     │  id (PK)                    │
                     │  account_id (FK)            │
                     │  cost_center_id (FK)        │
                     │  company_id (FK)            │
                     │  year                       │
                     │  month                      │
                     │  budgeted_amount            │
                     │  notes                      │
                     │  created_by_id (FK)         │
                     │  created_at                 │
                     │  updated_at                 │
                     │  UNIQUE(account, cost_center│
                     │         , year, month)      │
                     └─────────────────────────────┘
```

### 3.2 Model Specifications

#### 3.2.1 `Account` Model

**Purpose**: Represents a single account in the Chart of Accounts (CoA), supporting hierarchical organization for P&L and Balance Sheet reporting.

**Fields**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | BigAutoField | PK | Primary key |
| `company` | ForeignKey | FK to `finance.DimCompany`, PROTECT, NOT NULL | Company this account belongs to |
| `code` | CharField(20) | UNIQUE (per company), NOT NULL | Account code (e.g., "1000", "4010") |
| `name` | CharField(200) | NOT NULL | Account name (e.g., "Cash", "Sales Revenue") |
| `account_type` | CharField(20) | Choices, NOT NULL | ASSET, LIABILITY, REVENUE, EXPENSE, EQUITY |
| `parent` | ForeignKey | FK to `Account`, SET_NULL, NULL | Parent account for hierarchical CoA |
| `is_active` | BooleanField | Default: True | Whether account is active for budget entry |
| `created_at` | DateTimeField | auto_now_add | Timestamp of creation |
| `updated_at` | DateTimeField | auto_now | Timestamp of last update |

**Choices**:
```python
class AccountType(models.TextChoices):
    ASSET = "ASSET", "Asset"
    LIABILITY = "LIABILITY", "Liability"
    REVENUE = "REVENUE", "Revenue"
    EXPENSE = "EXPENSE", "Expense"
    EQUITY = "EQUITY", "Equity"
```

**Constraints**:
- `UNIQUE(company, code)`: Account codes must be unique within a company
- `CHECK(parent.company_id = company_id)`: Parent account must belong to the same company (enforced in `clean()`)

**Audit Trail**: `HistoricalRecords()` enabled

**Methods**:
- `clean()`: Validate parent account belongs to same company, prevent circular references
- `get_full_path()`: Return hierarchical path (e.g., "Operating Expenses > Salaries > Management")
- `get_children()`: Return all child accounts

**Example Data**:
```python
# Asset Accounts
Account(company=faroe_broodstock, code="1000", name="Cash", account_type="ASSET", parent=None)
Account(company=faroe_broodstock, code="1100", name="Accounts Receivable", account_type="ASSET", parent=None)

# Revenue Accounts
Account(company=faroe_broodstock, code="4000", name="Sales Revenue", account_type="REVENUE", parent=None)
Account(company=faroe_broodstock, code="4010", name="Egg Sales", account_type="REVENUE", parent=revenue_4000)

# Expense Accounts
Account(company=faroe_broodstock, code="5000", name="Operating Expenses", account_type="EXPENSE", parent=None)
Account(company=faroe_broodstock, code="5100", name="Salaries", account_type="EXPENSE", parent=opex_5000)
Account(company=faroe_broodstock, code="5110", name="Management Salaries", account_type="EXPENSE", parent=salaries_5100)
```

#### 3.2.2 `CostCenter` Model

**Purpose**: Represents an organizational unit for cost allocation and departmental budgeting, supporting hierarchical organization (e.g., "Faroe Islands > Broodstock > Hatchery").

**Fields**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | BigAutoField | PK | Primary key |
| `company` | ForeignKey | FK to `finance.DimCompany`, PROTECT, NOT NULL | Company this cost center belongs to |
| `code` | CharField(20) | UNIQUE (per company), NOT NULL | Cost center code (e.g., "CC-001", "HATCH") |
| `name` | CharField(200) | NOT NULL | Cost center name (e.g., "Hatchery Operations") |
| `parent` | ForeignKey | FK to `CostCenter`, SET_NULL, NULL | Parent cost center for hierarchical organization |
| `is_active` | BooleanField | Default: True | Whether cost center is active for budget entry |
| `created_at` | DateTimeField | auto_now_add | Timestamp of creation |
| `updated_at` | DateTimeField | auto_now | Timestamp of last update |

**Constraints**:
- `UNIQUE(company, code)`: Cost center codes must be unique within a company
- `CHECK(parent.company_id = company_id)`: Parent cost center must belong to the same company (enforced in `clean()`)

**Audit Trail**: `HistoricalRecords()` enabled

**Methods**:
- `clean()`: Validate parent cost center belongs to same company, prevent circular references
- `get_full_path()`: Return hierarchical path (e.g., "Faroe Islands > Broodstock > Hatchery")
- `get_children()`: Return all child cost centers

**Example Data**:
```python
# Top-level cost centers
CostCenter(company=faroe_broodstock, code="CC-100", name="Broodstock Operations", parent=None)
CostCenter(company=faroe_broodstock, code="CC-200", name="Administration", parent=None)

# Sub-cost centers
CostCenter(company=faroe_broodstock, code="CC-110", name="Hatchery", parent=broodstock_ops)
CostCenter(company=faroe_broodstock, code="CC-120", name="Broodstock Maintenance", parent=broodstock_ops)
CostCenter(company=faroe_broodstock, code="CC-210", name="Finance Department", parent=admin)
```

#### 3.2.3 `Budget` Model

**Purpose**: Represents a monthly budget entry for a specific Account × Cost Center combination, enabling detailed financial planning and variance tracking.

**Fields**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | BigAutoField | PK | Primary key |
| `account` | ForeignKey | FK to `Account`, PROTECT, NOT NULL | Account this budget entry is for |
| `cost_center` | ForeignKey | FK to `CostCenter`, PROTECT, NOT NULL | Cost center this budget entry is for |
| `company` | ForeignKey | FK to `finance.DimCompany`, PROTECT, NOT NULL | Company (denormalized for query performance) |
| `year` | PositiveIntegerField | NOT NULL | Budget year (e.g., 2025) |
| `month` | PositiveSmallIntegerField | NOT NULL, 1-12 | Budget month (1=January, 12=December) |
| `budgeted_amount` | DecimalField(14, 2) | NOT NULL | Budgeted amount in the specified currency |
| `currency` | CharField(3) | NOT NULL, max_length=3 | ISO 4217 currency code (e.g., 'DKK', 'EUR'); defaults to company.currency |
| `notes` | TextField | BLANK | Optional notes for this budget entry |
| `created_by` | ForeignKey | FK to `auth.User`, SET_NULL, NULL | User who created this budget entry |
| `created_at` | DateTimeField | auto_now_add | Timestamp of creation |
| `updated_at` | DateTimeField | auto_now | Timestamp of last update |

**Constraints**:
- `UNIQUE(account, cost_center, year, month)`: Only one budget entry per Account × Cost Center × Year × Month
- `CHECK(month >= 1 AND month <= 12)`: Month must be between 1 and 12
- `CHECK(year >= 2020 AND year <= 2100)`: Year must be reasonable
- `CHECK(account.company_id = company_id)`: Account must belong to the same company (enforced in `clean()`)
- `CHECK(cost_center.company_id = company_id)`: Cost center must belong to the same company (enforced in `clean()`)
- `CHECK(currency = company.currency OR custom logic)`: Currency must match company currency unless explicitly overridden (enforced in `clean()`)

**Audit Trail**: `HistoricalRecords()` enabled

**Methods**:
- `clean()`: Validate account and cost center belong to the same company, validate month/year ranges, and ensure currency matches company.currency (with option for override if multi-currency is allowed)
- `get_period()`: Return formatted period string (e.g., "2025-01", "January 2025")

**Indexes**:
- `INDEX(company, year, month)`: For efficient budget summary queries
- `INDEX(account, year)`: For account-level budget aggregation
- `INDEX(cost_center, year)`: For cost center-level budget aggregation

**Example Data**:
```python
# January 2025 budgets for Hatchery cost center
Budget(
    account=salaries_5100,
    cost_center=hatchery_cc110,
    company=faroe_broodstock,
    year=2025,
    month=1,
    budgeted_amount=Decimal("45000.00"),
    currency='DKK',  # Matches faroe_broodstock.currency
    notes="3 full-time employees + 1 part-time",
    created_by=finance_manager
)

Budget(
    account=feed_costs_5200,
    cost_center=hatchery_cc110,
    company=faroe_broodstock,
    year=2025,
    month=1,
    budgeted_amount=Decimal("12000.00"),
    currency='DKK',  # Matches faroe_broodstock.currency
    notes="Based on 500kg/day feed consumption",
    created_by=finance_manager
)
```

### 3.3 Data Model Rationale

#### 3.3.1 Why Separate `Account` and `CostCenter`?

**Two-Dimensional Budgeting**: Financial planning requires tracking budgets across **two orthogonal dimensions**:
1. **What** is being spent (Account: Salaries, Feed, Equipment)
2. **Where** it's being spent (Cost Center: Hatchery, Broodstock, Administration)

This enables questions like:
- "What is the total salary budget for the Hatchery?" (Sum all Salary accounts for Hatchery cost center)
- "What is the total Hatchery budget?" (Sum all accounts for Hatchery cost center)
- "What is the company-wide salary budget?" (Sum all Salary accounts across all cost centers)

#### 3.3.2 Why Monthly Granularity?

**Operational Alignment**: Aquaculture operations have monthly cycles (feeding, growth, mortality tracking), so monthly budgets align with operational reporting. Users can aggregate to quarterly/yearly as needed.

#### 3.3.3 Why Hierarchical Accounts and Cost Centers?

**Flexible Reporting**: Hierarchical structures enable:
- **Drill-down reporting**: Start with "Total Operating Expenses" and drill into "Salaries" → "Management Salaries"
- **Roll-up aggregation**: Sum all child accounts to get parent account totals
- **Organizational alignment**: Cost centers mirror organizational structure (Geography → Subsidiary → Department)

#### 3.3.4 Why Denormalize `company` in `Budget`?

**Query Performance**: The `company` field in `Budget` is denormalized (also available via `account.company` and `cost_center.company`) to enable efficient filtering without JOINs:
```sql
-- Fast query (uses index on budget.company_id)
SELECT * FROM finance_core_budget WHERE company_id = 1 AND year = 2025;

-- Slow query (requires JOINs)
SELECT * FROM finance_core_budget b
JOIN finance_core_account a ON b.account_id = a.id
WHERE a.company_id = 1 AND b.year = 2025;
```

---

## 4. API Design

### 4.1 API Standards Compliance

The `finance_core` API follows AquaMind's API standards (documented in `aquamind/docs/quality_assurance/api_standards.md`):

1. **URL Convention**: Kebab-case for resource names (e.g., `/api/v1/finance-core/accounts/`)
2. **HTTP Methods**: Standard REST verbs (GET, POST, PUT, PATCH, DELETE)
3. **Filtering**: Use `django-filter` for query parameter filtering
4. **Searching**: Use DRF's `SearchFilter` for text search
5. **Pagination**: Use `PageNumberPagination` with default page size of 50
6. **Ordering**: Use DRF's `OrderingFilter` for sorting
7. **Error Handling**: Return structured error responses with appropriate HTTP status codes
8. **Authentication**: Use DRF's `IsAuthenticated` permission class
9. **Versioning**: API versioned at `/api/v1/`

### 4.2 Endpoint Specifications

#### 4.2.1 Account Endpoints

**Base URL**: `/api/v1/finance-core/accounts/`

| Method | Endpoint | Description | Permissions |
|--------|----------|-------------|-------------|
| GET | `/api/v1/finance-core/accounts/` | List all accounts (with filtering) | IsAuthenticated |
| POST | `/api/v1/finance-core/accounts/` | Create a new account | IsAuthenticated, FinanceRole |
| GET | `/api/v1/finance-core/accounts/{id}/` | Retrieve a specific account | IsAuthenticated |
| PUT | `/api/v1/finance-core/accounts/{id}/` | Update an account (full) | IsAuthenticated, FinanceRole |
| PATCH | `/api/v1/finance-core/accounts/{id}/` | Update an account (partial) | IsAuthenticated, FinanceRole |
| DELETE | `/api/v1/finance-core/accounts/{id}/` | Delete an account | IsAuthenticated, FinanceRole |
| GET | `/api/v1/finance-core/accounts/tree/` | Get hierarchical account tree | IsAuthenticated |

**Query Parameters** (GET list):
- `company`: Filter by company ID
- `account_type`: Filter by account type (ASSET, LIABILITY, REVENUE, EXPENSE, EQUITY)
- `is_active`: Filter by active status (true/false)
- `parent`: Filter by parent account ID (null for top-level accounts)
- `search`: Search by code or name
- `ordering`: Sort by field (e.g., `code`, `-created_at`)

**Custom Actions**:
- `GET /api/v1/finance-core/accounts/tree/`: Returns hierarchical account tree structure

**Request/Response Examples**: See Section 4.3

#### 4.2.2 Cost Center Endpoints

**Base URL**: `/api/v1/finance-core/cost-centers/`

| Method | Endpoint | Description | Permissions |
|--------|----------|-------------|-------------|
| GET | `/api/v1/finance-core/cost-centers/` | List all cost centers (with filtering) | IsAuthenticated |
| POST | `/api/v1/finance-core/cost-centers/` | Create a new cost center | IsAuthenticated, FinanceRole |
| GET | `/api/v1/finance-core/cost-centers/{id}/` | Retrieve a specific cost center | IsAuthenticated |
| PUT | `/api/v1/finance-core/cost-centers/{id}/` | Update a cost center (full) | IsAuthenticated, FinanceRole |
| PATCH | `/api/v1/finance-core/cost-centers/{id}/` | Update a cost center (partial) | IsAuthenticated, FinanceRole |
| DELETE | `/api/v1/finance-core/cost-centers/{id}/` | Delete a cost center | IsAuthenticated, FinanceRole |
| GET | `/api/v1/finance-core/cost-centers/tree/` | Get hierarchical cost center tree | IsAuthenticated |

**Query Parameters** (GET list):
- `company`: Filter by company ID
- `is_active`: Filter by active status (true/false)
- `parent`: Filter by parent cost center ID (null for top-level cost centers)
- `search`: Search by code or name
- `ordering`: Sort by field (e.g., `code`, `-created_at`)

**Custom Actions**:
- `GET /api/v1/finance-core/cost-centers/tree/`: Returns hierarchical cost center tree structure

#### 4.2.3 Budget Endpoints

**Base URL**: `/api/v1/finance-core/budgets/`

| Method | Endpoint | Description | Permissions |
|--------|----------|-------------|-------------|
| GET | `/api/v1/finance-core/budgets/` | List all budget entries (with filtering) | IsAuthenticated |
| POST | `/api/v1/finance-core/budgets/` | Create a new budget entry | IsAuthenticated, FinanceRole |
| GET | `/api/v1/finance-core/budgets/{id}/` | Retrieve a specific budget entry | IsAuthenticated |
| PUT | `/api/v1/finance-core/budgets/{id}/` | Update a budget entry (full) | IsAuthenticated, FinanceRole |
| PATCH | `/api/v1/finance-core/budgets/{id}/` | Update a budget entry (partial) | IsAuthenticated, FinanceRole |
| DELETE | `/api/v1/finance-core/budgets/{id}/` | Delete a budget entry | IsAuthenticated, FinanceRole |
| POST | `/api/v1/finance-core/budgets/bulk-create/` | Create multiple budget entries | IsAuthenticated, FinanceRole |
| GET | `/api/v1/finance-core/budgets/summary/` | Get budget summary (aggregated) | IsAuthenticated |

**Query Parameters** (GET list):
- `company`: Filter by company ID
- `account`: Filter by account ID
- `cost_center`: Filter by cost center ID
- `year`: Filter by year
- `month`: Filter by month
- `year_month`: Filter by year-month (e.g., "2025-01")
- `account__account_type`: Filter by account type (ASSET, LIABILITY, REVENUE, EXPENSE, EQUITY)
- `search`: Search by account code/name or cost center code/name
- `ordering`: Sort by field (e.g., `year`, `month`, `-budgeted_amount`)

**Custom Actions**:
- `POST /api/v1/finance-core/budgets/bulk-create/`: Create multiple budget entries in a single request (for efficient data entry)
- `GET /api/v1/finance-core/budgets/summary/`: Returns aggregated budget summary with query parameters:
  - `company`: Required, company ID
  - `year`: Required, budget year
  - `month`: Optional, specific month (if omitted, returns yearly summary)
  - `account_type`: Optional, filter by account type
  - `cost_center`: Optional, filter by cost center
  - `group_by`: Optional, grouping dimension (`account`, `cost_center`, `account_type`, `month`)

**Request/Response Examples**: See Section 4.3

### 4.3 Request/Response Examples

#### 4.3.1 Account API Examples

**Create Account** (POST `/api/v1/finance-core/accounts/`)

Request:
```json
{
  "company": 1,
  "code": "5100",
  "name": "Salaries",
  "account_type": "EXPENSE",
  "parent": 5,
  "is_active": true
}
```

Response (201 Created):
```json
{
  "id": 10,
  "company": {
    "company_id": 1,
    "display_name": "Bakkafrost Broodstock (Faroe Islands)",
    "currency": "EUR"
  },
  "code": "5100",
  "name": "Salaries",
  "account_type": "EXPENSE",
  "parent": {
    "id": 5,
    "code": "5000",
    "name": "Operating Expenses"
  },
  "is_active": true,
  "full_path": "Operating Expenses > Salaries",
  "created_at": "2025-10-28T10:30:00Z",
  "updated_at": "2025-10-28T10:30:00Z"
}
```

**List Accounts with Filtering** (GET `/api/v1/finance-core/accounts/?company=1&account_type=EXPENSE&is_active=true`)

Response (200 OK):
```json
{
  "count": 15,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 5,
      "company": {
        "company_id": 1,
        "display_name": "Bakkafrost Broodstock (Faroe Islands)",
        "currency": "EUR"
      },
      "code": "5000",
      "name": "Operating Expenses",
      "account_type": "EXPENSE",
      "parent": null,
      "is_active": true,
      "full_path": "Operating Expenses",
      "created_at": "2025-10-28T10:00:00Z",
      "updated_at": "2025-10-28T10:00:00Z"
    },
    {
      "id": 10,
      "company": {
        "company_id": 1,
        "display_name": "Bakkafrost Broodstock (Faroe Islands)",
        "currency": "EUR"
      },
      "code": "5100",
      "name": "Salaries",
      "account_type": "EXPENSE",
      "parent": {
        "id": 5,
        "code": "5000",
        "name": "Operating Expenses"
      },
      "is_active": true,
      "full_path": "Operating Expenses > Salaries",
      "created_at": "2025-10-28T10:30:00Z",
      "updated_at": "2025-10-28T10:30:00Z"
    }
  ]
}
```

**Get Account Tree** (GET `/api/v1/finance-core/accounts/tree/?company=1&account_type=EXPENSE`)

Response (200 OK):
```json
{
  "account_type": "EXPENSE",
  "tree": [
    {
      "id": 5,
      "code": "5000",
      "name": "Operating Expenses",
      "account_type": "EXPENSE",
      "is_active": true,
      "children": [
        {
          "id": 10,
          "code": "5100",
          "name": "Salaries",
          "account_type": "EXPENSE",
          "is_active": true,
          "children": [
            {
              "id": 11,
              "code": "5110",
              "name": "Management Salaries",
              "account_type": "EXPENSE",
              "is_active": true,
              "children": []
            },
            {
              "id": 12,
              "code": "5120",
              "name": "Operational Staff Salaries",
              "account_type": "EXPENSE",
              "is_active": true,
              "children": []
            }
          ]
        },
        {
          "id": 13,
          "code": "5200",
          "name": "Feed Costs",
          "account_type": "EXPENSE",
          "is_active": true,
          "children": []
        }
      ]
    }
  ]
}
```

#### 4.3.2 Cost Center API Examples

**Create Cost Center** (POST `/api/v1/finance-core/cost-centers/`)

Request:
```json
{
  "company": 1,
  "code": "CC-110",
  "name": "Hatchery",
  "parent": 5,
  "is_active": true
}
```

Response (201 Created):
```json
{
  "id": 10,
  "company": {
    "company_id": 1,
    "display_name": "Bakkafrost Broodstock (Faroe Islands)",
    "currency": "EUR"
  },
  "code": "CC-110",
  "name": "Hatchery",
  "parent": {
    "id": 5,
    "code": "CC-100",
    "name": "Broodstock Operations"
  },
  "is_active": true,
  "full_path": "Broodstock Operations > Hatchery",
  "created_at": "2025-10-28T10:35:00Z",
  "updated_at": "2025-10-28T10:35:00Z"
}
```

#### 4.3.3 Budget API Examples

**Create Budget Entry** (POST `/api/v1/finance-core/budgets/`)

Request:
```json
{
  "account": 10,
  "cost_center": 10,
  "company": 1,
  "year": 2025,
  "month": 1,
  "budgeted_amount": "45000.00",
  "notes": "3 full-time employees + 1 part-time"
}
```

Response (201 Created):
```json
{
  "id": 100,
  "account": {
    "id": 10,
    "code": "5100",
    "name": "Salaries",
    "account_type": "EXPENSE"
  },
  "cost_center": {
    "id": 10,
    "code": "CC-110",
    "name": "Hatchery"
  },
  "company": {
    "company_id": 1,
    "display_name": "Bakkafrost Broodstock (Faroe Islands)",
    "currency": "EUR"
  },
  "year": 2025,
  "month": 1,
  "period": "2025-01",
  "budgeted_amount": "45000.00",
  "notes": "3 full-time employees + 1 part-time",
  "created_by": {
    "id": 5,
    "username": "finance_manager",
    "full_name": "Jane Smith"
  },
  "created_at": "2025-10-28T10:40:00Z",
  "updated_at": "2025-10-28T10:40:00Z"
}
```

**Bulk Create Budget Entries** (POST `/api/v1/finance-core/budgets/bulk-create/`)

Request:
```json
{
  "budgets": [
    {
      "account": 10,
      "cost_center": 10,
      "company": 1,
      "year": 2025,
      "month": 1,
      "budgeted_amount": "45000.00",
      "notes": "Salaries for Hatchery"
    },
    {
      "account": 13,
      "cost_center": 10,
      "company": 1,
      "year": 2025,
      "month": 1,
      "budgeted_amount": "12000.00",
      "notes": "Feed costs for Hatchery"
    },
    {
      "account": 10,
      "cost_center": 10,
      "company": 1,
      "year": 2025,
      "month": 2,
      "budgeted_amount": "45000.00",
      "notes": "Salaries for Hatchery"
    }
  ]
}
```

Response (201 Created):
```json
{
  "created_count": 3,
  "budgets": [
    {
      "id": 100,
      "account": {"id": 10, "code": "5100", "name": "Salaries"},
      "cost_center": {"id": 10, "code": "CC-110", "name": "Hatchery"},
      "year": 2025,
      "month": 1,
      "budgeted_amount": "45000.00"
    },
    {
      "id": 101,
      "account": {"id": 13, "code": "5200", "name": "Feed Costs"},
      "cost_center": {"id": 10, "code": "CC-110", "name": "Hatchery"},
      "year": 2025,
      "month": 1,
      "budgeted_amount": "12000.00"
    },
    {
      "id": 102,
      "account": {"id": 10, "code": "5100", "name": "Salaries"},
      "cost_center": {"id": 10, "code": "CC-110", "name": "Hatchery"},
      "year": 2025,
      "month": 2,
      "budgeted_amount": "45000.00"
    }
  ]
}
```

**Get Budget Summary** (GET `/api/v1/finance-core/budgets/summary/?company=1&year=2025&group_by=account_type`)

Response (200 OK):
```json
{
  "company": {
    "company_id": 1,
    "display_name": "Bakkafrost Broodstock (Faroe Islands)",
    "currency": "EUR"
  },
  "year": 2025,
  "summary": [
    {
      "account_type": "REVENUE",
      "total_budgeted": "1200000.00",
      "entry_count": 24
    },
    {
      "account_type": "EXPENSE",
      "total_budgeted": "980000.00",
      "entry_count": 156
    },
    {
      "account_type": "ASSET",
      "total_budgeted": "0.00",
      "entry_count": 0
    }
  ],
  "net_income_budgeted": "220000.00"
}
```

**Get Budget Summary by Month** (GET `/api/v1/finance-core/budgets/summary/?company=1&year=2025&group_by=month`)

Response (200 OK):
```json
{
  "company": {
    "company_id": 1,
    "display_name": "Bakkafrost Broodstock (Faroe Islands)",
    "currency": "EUR"
  },
  "year": 2025,
  "summary": [
    {
      "month": 1,
      "period": "2025-01",
      "total_budgeted": "95000.00",
      "entry_count": 15
    },
    {
      "month": 2,
      "period": "2025-02",
      "total_budgeted": "92000.00",
      "entry_count": 15
    }
  ]
}
```

### 4.4 Error Handling

All API endpoints follow AquaMind's standard error response format:

**Validation Error** (400 Bad Request):
```json
{
  "detail": "Validation failed",
  "errors": {
    "code": ["Account with this code already exists for this company."],
    "parent": ["Parent account must belong to the same company."]
  }
}
```

**Not Found** (404 Not Found):
```json
{
  "detail": "Account with id=999 not found."
}
```

**Permission Denied** (403 Forbidden):
```json
{
  "detail": "You do not have permission to perform this action. Finance role required."
}
```

**Server Error** (500 Internal Server Error):
```json
{
  "detail": "An unexpected error occurred. Please contact support.",
  "error_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

---

## 5. Business Logic

### 5.1 Account Management Logic

#### 5.1.1 Account Code Uniqueness

**Rule**: Account codes must be unique within a company, but can be reused across companies.

**Enforcement**: Database `UNIQUE` constraint on `(company, code)`.

**Example**:
- ✅ Allowed: Faroe Broodstock has account "5100" (Salaries), Scotland Farming also has account "5100" (Salaries)
- ❌ Forbidden: Faroe Broodstock has two accounts with code "5100"

#### 5.1.2 Hierarchical Account Validation

**Rule**: Parent account must belong to the same company as the child account.

**Enforcement**: `Account.clean()` method validates `parent.company_id == self.company_id`.

**Example**:
- ✅ Allowed: Account "5110" (Management Salaries, Faroe Broodstock) has parent "5100" (Salaries, Faroe Broodstock)
- ❌ Forbidden: Account "5110" (Management Salaries, Faroe Broodstock) has parent "5100" (Salaries, Scotland Farming)

#### 5.1.3 Circular Reference Prevention

**Rule**: An account cannot be its own ancestor (direct or indirect parent).

**Enforcement**: `Account.clean()` method traverses parent chain to detect cycles.

**Example**:
- ❌ Forbidden: Account A → parent: Account B → parent: Account C → parent: Account A (cycle detected)

#### 5.1.4 Account Deletion Rules

**Rule**: An account can only be deleted if:
1. It has no child accounts
2. It has no budget entries

**Enforcement**: Django's `PROTECT` foreign key constraint prevents deletion if referenced.

**User Feedback**: API returns 400 Bad Request with message: "Cannot delete account '5100' because it has 3 child accounts and 24 budget entries. Please delete or reassign them first."

### 5.2 Cost Center Management Logic

#### 5.2.1 Cost Center Code Uniqueness

**Rule**: Cost center codes must be unique within a company, but can be reused across companies.

**Enforcement**: Database `UNIQUE` constraint on `(company, code)`.

#### 5.2.2 Hierarchical Cost Center Validation

**Rule**: Parent cost center must belong to the same company as the child cost center.

**Enforcement**: `CostCenter.clean()` method validates `parent.company_id == self.company_id`.

#### 5.2.3 Circular Reference Prevention

**Rule**: A cost center cannot be its own ancestor (direct or indirect parent).

**Enforcement**: `CostCenter.clean()` method traverses parent chain to detect cycles.

#### 5.2.4 Cost Center Deletion Rules

**Rule**: A cost center can only be deleted if:
1. It has no child cost centers
2. It has no budget entries

**Enforcement**: Django's `PROTECT` foreign key constraint prevents deletion if referenced.

### 5.3 Budget Entry Logic

#### 5.3.1 Budget Entry Uniqueness

**Rule**: Only one budget entry is allowed per Account × Cost Center × Year × Month combination.

**Enforcement**: Database `UNIQUE` constraint on `(account, cost_center, year, month)`.

**User Experience**: If a user attempts to create a duplicate budget entry, the API returns 400 Bad Request with message: "A budget entry already exists for Account '5100', Cost Center 'CC-110', 2025-01. Please update the existing entry instead."

#### 5.3.2 Cross-Company Validation

**Rule**: The account, cost center, and company must all belong to the same company.

**Enforcement**: `Budget.clean()` method validates:
- `account.company_id == self.company_id`
- `cost_center.company_id == self.company_id`

**Example**:
- ✅ Allowed: Budget entry for Account "5100" (Faroe Broodstock), Cost Center "CC-110" (Faroe Broodstock), Company: Faroe Broodstock
- ❌ Forbidden: Budget entry for Account "5100" (Faroe Broodstock), Cost Center "CC-110" (Scotland Farming), Company: Faroe Broodstock

#### 5.3.3 Month and Year Validation

**Rule**: Month must be between 1 and 12, year must be between 2020 and 2100.

**Enforcement**: Database `CHECK` constraints and `Budget.clean()` method.

#### 5.3.4 Budget Amount Validation

**Rule**: Budget amounts can be positive, negative, or zero (to support different account types).

**Rationale**:
- **Revenue accounts**: Positive budgeted amounts represent expected income
- **Expense accounts**: Positive budgeted amounts represent expected costs
- **Asset/Liability accounts**: Can have positive or negative budgeted changes

**No Enforcement**: No constraint on sign of `budgeted_amount`.

### 5.4 Budget Summary Calculation Logic

#### 5.4.1 Aggregation Rules

**Budget Summary Endpoint** (`GET /api/v1/finance-core/budgets/summary/`) aggregates budget entries based on query parameters:

**Aggregation by Account Type**:
```python
# Pseudocode
summary = Budget.objects.filter(company=company_id, year=year) \
    .values('account__account_type') \
    .annotate(
        total_budgeted=Sum('budgeted_amount'),
        entry_count=Count('id')
    )
```

**Aggregation by Cost Center**:
```python
summary = Budget.objects.filter(company=company_id, year=year) \
    .values('cost_center__code', 'cost_center__name') \
    .annotate(
        total_budgeted=Sum('budgeted_amount'),
        entry_count=Count('id')
    )
```

**Aggregation by Month**:
```python
summary = Budget.objects.filter(company=company_id, year=year) \
    .values('month') \
    .annotate(
        total_budgeted=Sum('budgeted_amount'),
        entry_count=Count('id')
    ) \
    .order_by('month')
```

#### 5.4.2 Net Income Calculation

**Net Income (Budgeted)** = Total Revenue Budget - Total Expense Budget

**Calculation**:
```python
revenue_budget = Budget.objects.filter(
    company=company_id,
    year=year,
    account__account_type='REVENUE'
).aggregate(total=Sum('budgeted_amount'))['total'] or 0

expense_budget = Budget.objects.filter(
    company=company_id,
    year=year,
    account__account_type='EXPENSE'
).aggregate(total=Sum('budgeted_amount'))['total'] or 0

net_income_budgeted = revenue_budget - expense_budget
```

**Note**: Asset, Liability, and Equity accounts are not included in net income calculation (they affect the Balance Sheet, not the P&L).

### 5.5 Budget vs. Actuals Logic (Phase 2)

**Integration with `finance` App**: The `finance_core` app will integrate with the existing `finance` app to compare budgeted amounts against actual operational performance.

**Actuals Sources**:
1. **Harvest Revenue** (from `finance.FactHarvest`): Actual revenue from harvest events
2. **Intercompany Costs** (from `finance.IntercompanyTransaction`): Actual costs from intercompany transfers (e.g., smolt purchases from Freshwater to Farming)
3. **Feed Costs** (from `inventory.FeedingEvent`): Actual feed costs from feeding events

**Variance Calculation**:
```python
# Pseudocode for Budget vs. Actuals Report
def calculate_variance(company_id, year, month):
    # Get budgeted amounts
    budgets = Budget.objects.filter(
        company=company_id,
        year=year,
        month=month
    ).select_related('account', 'cost_center')
    
    # Get actuals from finance app
    actuals = get_actuals_from_finance_app(company_id, year, month)
    
    # Calculate variance for each budget entry
    variance_report = []
    for budget in budgets:
        actual_amount = actuals.get(budget.account.code, 0)
        variance = actual_amount - budget.budgeted_amount
        variance_percent = (variance / budget.budgeted_amount * 100) if budget.budgeted_amount != 0 else 0
        
        variance_report.append({
            'account': budget.account,
            'cost_center': budget.cost_center,
            'budgeted': budget.budgeted_amount,
            'actual': actual_amount,
            'variance': variance,
            'variance_percent': variance_percent
        })
    
    return variance_report
```

**Implementation Note**: This logic will be implemented in Phase 2 as a separate service (`variance_service.py`) after the core budgeting functionality is stable.

---

## 6. Integration Architecture

### 6.1 Integration with Existing `finance` App

The `finance_core` app integrates with the existing `finance` app at specific, well-defined points:

#### 6.1.1 Company Dimension Sharing

**Integration Point**: Both apps reference `finance.DimCompany` for company-level data.

**Relationship**:
```python
# finance_core/models.py
from apps.finance.models import DimCompany

class Account(models.Model):
    company = models.ForeignKey(
        DimCompany,  # Shared dimension from finance app
        on_delete=models.PROTECT,
        related_name="finance_core_accounts"
    )
    # ... other fields

class CostCenter(models.Model):
    company = models.ForeignKey(
        DimCompany,  # Shared dimension from finance app
        on_delete=models.PROTECT,
        related_name="finance_core_cost_centers"
    )
    # ... other fields

class Budget(models.Model):
    company = models.ForeignKey(
        DimCompany,  # Shared dimension from finance app
        on_delete=models.PROTECT,
        related_name="finance_core_budgets"
    )
    # ... other fields
```

**Rationale**: `DimCompany` is the authoritative source for company-level metadata (geography, subsidiary, currency, NAV company code). Reusing this model ensures consistency across financial reporting and planning.

#### 6.1.2 Budget vs. Actuals Integration (Phase 2)

**Integration Point**: Compare `finance_core.Budget` entries against actuals from `finance.FactHarvest`, `finance.IntercompanyTransaction`, and `inventory.FeedingEvent`.

**Service Layer**:
```python
# finance_core/services/variance_service.py
from apps.finance.models import FactHarvest, IntercompanyTransaction
from apps.inventory.models import FeedingEvent
from apps.finance_core.models import Budget

class VarianceService:
    @staticmethod
    def calculate_variance(company_id, year, month):
        """
        Calculate budget vs. actuals variance for a specific period.
        
        Returns:
            dict: Variance report with budgeted, actual, and variance amounts
        """
        # Get budgets for the period
        budgets = Budget.objects.filter(
            company_id=company_id,
            year=year,
            month=month
        ).select_related('account', 'cost_center')
        
        # Get actuals from finance app
        actuals = VarianceService._get_actuals(company_id, year, month)
        
        # Calculate variance
        variance_report = []
        for budget in budgets:
            account_code = budget.account.code
            actual_amount = actuals.get(account_code, Decimal('0.00'))
            variance = actual_amount - budget.budgeted_amount
            variance_percent = (
                (variance / budget.budgeted_amount * 100)
                if budget.budgeted_amount != 0
                else Decimal('0.00')
            )
            
            variance_report.append({
                'account': budget.account,
                'cost_center': budget.cost_center,
                'budgeted': budget.budgeted_amount,
                'actual': actual_amount,
                'variance': variance,
                'variance_percent': variance_percent,
                'status': VarianceService._get_variance_status(variance_percent)
            })
        
        return variance_report
    
    @staticmethod
    def _get_actuals(company_id, year, month):
        """
        Retrieve actual amounts from finance app for the period.
        
        Returns:
            dict: Account code → actual amount mapping
        """
        actuals = {}
        
        # Get harvest revenue (from finance.FactHarvest)
        harvest_facts = FactHarvest.objects.filter(
            dim_company_id=company_id,
            event_date__year=year,
            event_date__month=month
        )
        # Map to revenue accounts (e.g., "4000" - Sales Revenue)
        # This requires a mapping table or configuration
        
        # Get intercompany costs (from finance.IntercompanyTransaction)
        intercompany_txns = IntercompanyTransaction.objects.filter(
            policy__to_company_id=company_id,
            posting_date__year=year,
            posting_date__month=month,
            state='POSTED'
        )
        # Map to expense accounts (e.g., "5300" - Smolt Purchases)
        
        # Get feed costs (from inventory.FeedingEvent)
        feeding_events = FeedingEvent.objects.filter(
            container__site__company_id=company_id,
            feed_time__year=year,
            feed_time__month=month
        )
        # Map to expense accounts (e.g., "5200" - Feed Costs)
        
        return actuals
    
    @staticmethod
    def _get_variance_status(variance_percent):
        """
        Determine variance status based on percentage.
        
        Returns:
            str: 'favorable', 'unfavorable', or 'on_track'
        """
        if abs(variance_percent) <= 5:
            return 'on_track'
        elif variance_percent > 5:
            return 'favorable'  # For revenue, actual > budget is good
        else:
            return 'unfavorable'  # For expenses, actual > budget is bad
```

**API Endpoint** (Phase 2):
```
GET /api/v1/finance-core/budgets/variance/?company=1&year=2025&month=1
```

**Response**:
```json
{
  "company": {
    "company_id": 1,
    "display_name": "Bakkafrost Broodstock (Faroe Islands)",
    "currency": "EUR"
  },
  "period": "2025-01",
  "variance_report": [
    {
      "account": {
        "code": "4000",
        "name": "Sales Revenue",
        "account_type": "REVENUE"
      },
      "cost_center": {
        "code": "CC-100",
        "name": "Broodstock Operations"
      },
      "budgeted": "100000.00",
      "actual": "105000.00",
      "variance": "5000.00",
      "variance_percent": "5.00",
      "status": "favorable"
    },
    {
      "account": {
        "code": "5100",
        "name": "Salaries",
        "account_type": "EXPENSE"
      },
      "cost_center": {
        "code": "CC-110",
        "name": "Hatchery"
      },
      "budgeted": "45000.00",
      "actual": "47000.00",
      "variance": "2000.00",
      "variance_percent": "4.44",
      "status": "on_track"
    }
  ],
  "summary": {
    "total_budgeted": "145000.00",
    "total_actual": "152000.00",
    "total_variance": "7000.00",
    "variance_percent": "4.83"
  }
}
```

#### 6.1.3 Cost Center Allocation for Intercompany Transactions (Phase 2)

**Integration Point**: Use `finance_core.CostCenter` to allocate costs from `finance.IntercompanyTransaction`.

**Use Case**: When a Farming subsidiary purchases smolt from a Freshwater subsidiary, the intercompany transaction cost should be allocated to a specific cost center (e.g., "Sea Farm 1" or "Smolt Procurement").

**Implementation**:
1. Add optional `cost_center_id` field to `finance.IntercompanyTransaction` (via migration)
2. When creating an intercompany transaction, allow users to specify a cost center
3. When generating Budget vs. Actuals reports, group intercompany costs by cost center

**Database Migration** (Phase 2):
```python
# apps/finance/migrations/0006_add_cost_center_to_intercompany_transaction.py
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ('finance', '0005_transfer_finance_integration_phase1'),
        ('finance_core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='intercompanytransaction',
            name='cost_center',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='intercompany_transactions',
                to='finance_core.costcenter'
            ),
        ),
    ]
```

### 6.2 Integration with Other Apps

#### 6.2.1 Integration with `batch` App (Indirect)

**Integration Point**: Budget vs. Actuals reporting may include batch-level costs (e.g., feed costs, mortality costs).

**Relationship**: No direct foreign key relationship. Integration happens via the `inventory` app (feeding events) and `health` app (treatment costs).

#### 6.2.2 Integration with `inventory` App (Phase 2)

**Integration Point**: Feed costs from `inventory.FeedingEvent` are used as actuals in Budget vs. Actuals reports.

**Service Layer**:
```python
# finance_core/services/variance_service.py (continued)
@staticmethod
def _get_feed_costs_actuals(company_id, year, month):
    """
    Get actual feed costs from inventory.FeedingEvent.
    
    Returns:
        Decimal: Total feed costs for the period
    """
    from apps.inventory.models import FeedingEvent
    
    feed_costs = FeedingEvent.objects.filter(
        container__site__company_id=company_id,
        feed_time__year=year,
        feed_time__month=month
    ).aggregate(
        total_cost=Sum(F('feed_amount_kg') * F('feed__cost_per_kg'))
    )['total_cost'] or Decimal('0.00')
    
    return feed_costs
```

#### 6.2.3 Integration with `users` App

**Integration Point**: User permissions for creating/editing budgets.

**Permission Model**:
- **Finance Role**: Users with `role='Finance'` in `users.UserProfile` can create/edit accounts, cost centers, and budgets
- **Manager Role**: Users with `role='Manager'` can view budgets but not edit
- **Operator Role**: Users with `role='Operator'` cannot access financial planning features

**Permission Class**:
```python
# finance_core/api/permissions/finance_role.py
from rest_framework.permissions import BasePermission

class FinanceRolePermission(BasePermission):
    """
    Permission class that allows only users with Finance role to modify financial data.
    """
    
    def has_permission(self, request, view):
        # Allow read-only access for authenticated users
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return request.user.is_authenticated
        
        # Require Finance role for write operations
        if not request.user.is_authenticated:
            return False
        
        try:
            user_profile = request.user.userprofile
            return user_profile.role in ('Finance', 'Manager', 'Admin')
        except AttributeError:
            return False
```

### 6.3 Integration Summary

| Integration Point | Source App | Target App | Integration Type | Phase |
|-------------------|------------|------------|------------------|-------|
| Company Dimension | `finance` | `finance_core` | Foreign Key | Phase 1 |
| Budget vs. Actuals (Harvest Revenue) | `finance` | `finance_core` | Service Layer | Phase 2 |
| Budget vs. Actuals (Intercompany Costs) | `finance` | `finance_core` | Service Layer | Phase 2 |
| Budget vs. Actuals (Feed Costs) | `inventory` | `finance_core` | Service Layer | Phase 2 |
| Cost Center Allocation | `finance_core` | `finance` | Foreign Key (optional) | Phase 2 |
| User Permissions | `users` | `finance_core` | Permission Class | Phase 1 |

---

## 7. Database Schema

### 7.1 Table Definitions (SQL)

#### 7.1.1 `finance_core_account` Table

```sql
CREATE TABLE finance_core_account (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES finance_dimcompany(company_id) ON DELETE PROTECT,
    code VARCHAR(20) NOT NULL,
    name VARCHAR(200) NOT NULL,
    account_type VARCHAR(20) NOT NULL CHECK (account_type IN ('ASSET', 'LIABILITY', 'REVENUE', 'EXPENSE', 'EQUITY')),
    parent_id BIGINT REFERENCES finance_core_account(id) ON DELETE SET NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT finance_core_account_company_code_uniq UNIQUE (company_id, code)
);

CREATE INDEX finance_core_account_company_id_idx ON finance_core_account(company_id);
CREATE INDEX finance_core_account_account_type_idx ON finance_core_account(account_type);
CREATE INDEX finance_core_account_parent_id_idx ON finance_core_account(parent_id);
```

#### 7.1.2 `finance_core_costcenter` Table

```sql
CREATE TABLE finance_core_costcenter (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES finance_dimcompany(company_id) ON DELETE PROTECT,
    code VARCHAR(20) NOT NULL,
    name VARCHAR(200) NOT NULL,
    parent_id BIGINT REFERENCES finance_core_costcenter(id) ON DELETE SET NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT finance_core_costcenter_company_code_uniq UNIQUE (company_id, code)
);

CREATE INDEX finance_core_costcenter_company_id_idx ON finance_core_costcenter(company_id);
CREATE INDEX finance_core_costcenter_parent_id_idx ON finance_core_costcenter(parent_id);
```

#### 7.1.3 `finance_core_budget` Table

```sql
CREATE TABLE finance_core_budget (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES finance_core_account(id) ON DELETE PROTECT,
    cost_center_id BIGINT NOT NULL REFERENCES finance_core_costcenter(id) ON DELETE PROTECT,
    company_id BIGINT NOT NULL REFERENCES finance_dimcompany(company_id) ON DELETE PROTECT,
    year INTEGER NOT NULL CHECK (year >= 2020 AND year <= 2100),
    month SMALLINT NOT NULL CHECK (month >= 1 AND month <= 12),
    budgeted_amount NUMERIC(14, 2) NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    created_by_id INTEGER REFERENCES auth_user(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT finance_core_budget_account_cc_year_month_uniq UNIQUE (account_id, cost_center_id, year, month)
);

CREATE INDEX finance_core_budget_company_year_month_idx ON finance_core_budget(company_id, year, month);
CREATE INDEX finance_core_budget_account_year_idx ON finance_core_budget(account_id, year);
CREATE INDEX finance_core_budget_cost_center_year_idx ON finance_core_budget(cost_center_id, year);
CREATE INDEX finance_core_budget_created_by_id_idx ON finance_core_budget(created_by_id);
```

#### 7.1.4 Historical Tables (Audit Trail)

**`finance_core_historicalaccount` Table**:
```sql
CREATE TABLE finance_core_historicalaccount (
    history_id SERIAL PRIMARY KEY,
    id BIGINT NOT NULL,
    company_id BIGINT NOT NULL,
    code VARCHAR(20) NOT NULL,
    name VARCHAR(200) NOT NULL,
    account_type VARCHAR(20) NOT NULL,
    parent_id BIGINT,
    is_active BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    history_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    history_change_reason VARCHAR(100),
    history_type VARCHAR(1) NOT NULL CHECK (history_type IN ('+', '~', '-')),
    history_user_id INTEGER REFERENCES auth_user(id) ON DELETE SET NULL
);

CREATE INDEX finance_core_historicalaccount_id_idx ON finance_core_historicalaccount(id);
CREATE INDEX finance_core_historicalaccount_history_date_idx ON finance_core_historicalaccount(history_date);
CREATE INDEX finance_core_historicalaccount_history_user_id_idx ON finance_core_historicalaccount(history_user_id);
```

**`finance_core_historicalcostcenter` Table**:
```sql
CREATE TABLE finance_core_historicalcostcenter (
    history_id SERIAL PRIMARY KEY,
    id BIGINT NOT NULL,
    company_id BIGINT NOT NULL,
    code VARCHAR(20) NOT NULL,
    name VARCHAR(200) NOT NULL,
    parent_id BIGINT,
    is_active BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    history_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    history_change_reason VARCHAR(100),
    history_type VARCHAR(1) NOT NULL CHECK (history_type IN ('+', '~', '-')),
    history_user_id INTEGER REFERENCES auth_user(id) ON DELETE SET NULL
);

CREATE INDEX finance_core_historicalcostcenter_id_idx ON finance_core_historicalcostcenter(id);
CREATE INDEX finance_core_historicalcostcenter_history_date_idx ON finance_core_historicalcostcenter(history_date);
CREATE INDEX finance_core_historicalcostcenter_history_user_id_idx ON finance_core_historicalcostcenter(history_user_id);
```

**`finance_core_historicalbudget` Table**:
```sql
CREATE TABLE finance_core_historicalbudget (
    history_id SERIAL PRIMARY KEY,
    id BIGINT NOT NULL,
    account_id BIGINT NOT NULL,
    cost_center_id BIGINT NOT NULL,
    company_id BIGINT NOT NULL,
    year INTEGER NOT NULL,
    month SMALLINT NOT NULL,
    budgeted_amount NUMERIC(14, 2) NOT NULL,
    notes TEXT NOT NULL,
    created_by_id INTEGER,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    history_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    history_change_reason VARCHAR(100),
    history_type VARCHAR(1) NOT NULL CHECK (history_type IN ('+', '~', '-')),
    history_user_id INTEGER REFERENCES auth_user(id) ON DELETE SET NULL
);

CREATE INDEX finance_core_historicalbudget_id_idx ON finance_core_historicalbudget(id);
CREATE INDEX finance_core_historicalbudget_history_date_idx ON finance_core_historicalbudget(history_date);
CREATE INDEX finance_core_historicalbudget_history_user_id_idx ON finance_core_historicalbudget(history_user_id);
```

### 7.2 Indexes and Performance

#### 7.2.1 Primary Indexes

All tables use `BIGSERIAL` primary keys for scalability:
- `finance_core_account.id`
- `finance_core_costcenter.id`
- `finance_core_budget.id`

#### 7.2.2 Foreign Key Indexes

Django automatically creates indexes on foreign key columns:
- `finance_core_account.company_id`
- `finance_core_account.parent_id`
- `finance_core_costcenter.company_id`
- `finance_core_costcenter.parent_id`
- `finance_core_budget.account_id`
- `finance_core_budget.cost_center_id`
- `finance_core_budget.company_id`
- `finance_core_budget.created_by_id`

#### 7.2.3 Composite Indexes for Queries

**Budget Summary Queries**:
- `finance_core_budget(company_id, year, month)`: For monthly budget summaries
- `finance_core_budget(account_id, year)`: For account-level budget aggregation
- `finance_core_budget(cost_center_id, year)`: For cost center-level budget aggregation

**Query Example**:
```sql
-- Get total budget for a company in 2025
SELECT SUM(budgeted_amount) AS total_budget
FROM finance_core_budget
WHERE company_id = 1 AND year = 2025;
-- Uses index: finance_core_budget_company_year_month_idx
```

#### 7.2.4 Unique Constraints

**Uniqueness Enforcement**:
- `finance_core_account(company_id, code)`: Prevent duplicate account codes within a company
- `finance_core_costcenter(company_id, code)`: Prevent duplicate cost center codes within a company
- `finance_core_budget(account_id, cost_center_id, year, month)`: Prevent duplicate budget entries

### 7.3 Data Volume Estimates

**Assumptions**:
- 4 companies (Faroe Broodstock, Faroe Freshwater, Faroe Farming, Scotland Farming)
- 50 accounts per company (200 total)
- 20 cost centers per company (80 total)
- 12 months × 50 accounts × 20 cost centers = 12,000 budget entries per company per year
- 5 years of budget data

**Estimated Row Counts**:
- `finance_core_account`: 200 rows
- `finance_core_costcenter`: 80 rows
- `finance_core_budget`: 240,000 rows (4 companies × 12,000 entries/year × 5 years)

**Storage Estimates**:
- `finance_core_account`: ~50 KB (200 rows × ~250 bytes/row)
- `finance_core_costcenter`: ~20 KB (80 rows × ~250 bytes/row)
- `finance_core_budget`: ~60 MB (240,000 rows × ~250 bytes/row)
- Historical tables: ~180 MB (assuming 3× the size of main tables due to audit trail)

**Total Estimated Storage**: ~240 MB for 5 years of budget data (negligible compared to operational data like time-series environmental readings).

---

## 8. Migration Strategy

### 8.1 Initial Migration

**Migration File**: `apps/finance_core/migrations/0001_initial.py`

**Operations**:
1. Create `finance_core_account` table
2. Create `finance_core_costcenter` table
3. Create `finance_core_budget` table
4. Create historical tables (`finance_core_historicalaccount`, `finance_core_historicalcostcenter`, `finance_core_historicalbudget`)
5. Create indexes and constraints

**Django Management Command**:
```bash
python manage.py makemigrations finance_core
python manage.py migrate finance_core
```

### 8.2 Seed Data Migration (Optional)

**Migration File**: `apps/finance_core/migrations/0002_seed_default_accounts.py`

**Purpose**: Populate default Chart of Accounts for each company based on standard aquaculture accounting structure.

**Example Seed Data**:
```python
# apps/finance_core/migrations/0002_seed_default_accounts.py
from django.db import migrations

def seed_default_accounts(apps, schema_editor):
    Account = apps.get_model('finance_core', 'Account')
    DimCompany = apps.get_model('finance', 'DimCompany')
    
    # Get all companies
    companies = DimCompany.objects.all()
    
    for company in companies:
        # Create default accounts for each company
        # Assets
        cash = Account.objects.create(
            company=company,
            code="1000",
            name="Cash",
            account_type="ASSET",
            is_active=True
        )
        accounts_receivable = Account.objects.create(
            company=company,
            code="1100",
            name="Accounts Receivable",
            account_type="ASSET",
            is_active=True
        )
        
        # Revenue
        sales_revenue = Account.objects.create(
            company=company,
            code="4000",
            name="Sales Revenue",
            account_type="REVENUE",
            is_active=True
        )
        
        # Expenses
        operating_expenses = Account.objects.create(
            company=company,
            code="5000",
            name="Operating Expenses",
            account_type="EXPENSE",
            is_active=True
        )
        salaries = Account.objects.create(
            company=company,
            code="5100",
            name="Salaries",
            account_type="EXPENSE",
            parent=operating_expenses,
            is_active=True
        )
        feed_costs = Account.objects.create(
            company=company,
            code="5200",
            name="Feed Costs",
            account_type="EXPENSE",
            parent=operating_expenses,
            is_active=True
        )

def reverse_seed(apps, schema_editor):
    Account = apps.get_model('finance_core', 'Account')
    Account.objects.all().delete()

class Migration(migrations.Migration):
    dependencies = [
        ('finance_core', '0001_initial'),
        ('finance', '0005_transfer_finance_integration_phase1'),
    ]

    operations = [
        migrations.RunPython(seed_default_accounts, reverse_seed),
    ]
```

### 8.3 Phase 2 Migrations

**Migration File**: `apps/finance_core/migrations/0003_add_budget_template.py` (Phase 2)

**Purpose**: Add `BudgetTemplate` model for year-over-year budget planning.

**Operations**:
1. Create `finance_core_budgettemplate` table
2. Add foreign key relationships to `Account` and `CostCenter`

**Migration File**: `apps/finance/migrations/0006_add_cost_center_to_intercompany_transaction.py` (Phase 2)

**Purpose**: Add optional `cost_center_id` field to `finance.IntercompanyTransaction` for cost allocation.

**Operations**:
1. Add `cost_center_id` field to `finance_intercompanytransaction` table (nullable, foreign key to `finance_core_costcenter`)

---

## 9. Testing Strategy

### 9.1 Unit Tests

**Test Coverage**: All models, serializers, and business logic methods.

**Test Files**:
- `apps/finance_core/tests/test_models.py`
- `apps/finance_core/tests/test_serializers.py`
- `apps/finance_core/tests/test_viewsets.py`
- `apps/finance_core/tests/test_services.py`

**Example Unit Tests**:

```python
# apps/finance_core/tests/test_models.py
from django.test import TestCase
from django.core.exceptions import ValidationError
from apps.finance.models import DimCompany
from apps.finance_core.models import Account, CostCenter, Budget

class AccountModelTest(TestCase):
    def setUp(self):
        self.company = DimCompany.objects.create(
            geography_id=1,
            subsidiary='BRO',
            display_name='Test Company',
            currency='EUR'
        )
    
    def test_account_creation(self):
        """Test that an account can be created successfully."""
        account = Account.objects.create(
            company=self.company,
            code='5100',
            name='Salaries',
            account_type='EXPENSE',
            is_active=True
        )
        self.assertEqual(account.code, '5100')
        self.assertEqual(account.name, 'Salaries')
        self.assertEqual(account.account_type, 'EXPENSE')
    
    def test_account_code_uniqueness(self):
        """Test that account codes must be unique within a company."""
        Account.objects.create(
            company=self.company,
            code='5100',
            name='Salaries',
            account_type='EXPENSE'
        )
        with self.assertRaises(ValidationError):
            Account.objects.create(
                company=self.company,
                code='5100',  # Duplicate code
                name='Other Salaries',
                account_type='EXPENSE'
            )
    
    def test_hierarchical_account_validation(self):
        """Test that parent account must belong to the same company."""
        other_company = DimCompany.objects.create(
            geography_id=2,
            subsidiary='FRE',
            display_name='Other Company',
            currency='EUR'
        )
        parent_account = Account.objects.create(
            company=other_company,
            code='5000',
            name='Operating Expenses',
            account_type='EXPENSE'
        )
        
        with self.assertRaises(ValidationError):
            child_account = Account(
                company=self.company,  # Different company
                code='5100',
                name='Salaries',
                account_type='EXPENSE',
                parent=parent_account  # Parent from different company
            )
            child_account.full_clean()  # Should raise ValidationError
    
    def test_circular_reference_prevention(self):
        """Test that circular references are prevented."""
        account_a = Account.objects.create(
            company=self.company,
            code='5000',
            name='Operating Expenses',
            account_type='EXPENSE'
        )
        account_b = Account.objects.create(
            company=self.company,
            code='5100',
            name='Salaries',
            account_type='EXPENSE',
            parent=account_a
        )
        
        # Attempt to create circular reference
        account_a.parent = account_b
        with self.assertRaises(ValidationError):
            account_a.full_clean()  # Should raise ValidationError
```

### 9.2 Integration Tests

**Test Coverage**: API endpoints, database queries, and cross-app integrations.

**Test Files**:
- `apps/finance_core/tests/test_api_integration.py`
- `apps/finance_core/tests/test_finance_integration.py`

**Example Integration Test**:

```python
# apps/finance_core/tests/test_api_integration.py
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth.models import User
from apps.finance.models import DimCompany
from apps.finance_core.models import Account, CostCenter, Budget

class BudgetAPIIntegrationTest(APITestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
        self.client.force_authenticate(user=self.user)
        
        # Create test company
        self.company = DimCompany.objects.create(
            geography_id=1,
            subsidiary='BRO',
            display_name='Test Company',
            currency='EUR'
        )
        
        # Create test account
        self.account = Account.objects.create(
            company=self.company,
            code='5100',
            name='Salaries',
            account_type='EXPENSE'
        )
        
        # Create test cost center
        self.cost_center = CostCenter.objects.create(
            company=self.company,
            code='CC-110',
            name='Hatchery'
        )
    
    def test_create_budget_entry(self):
        """Test creating a budget entry via API."""
        url = '/api/v1/finance-core/budgets/'
        data = {
            'account': self.account.id,
            'cost_center': self.cost_center.id,
            'company': self.company.company_id,
            'year': 2025,
            'month': 1,
            'budgeted_amount': '45000.00',
            'notes': 'Test budget entry'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['budgeted_amount'], '45000.00')
    
    def test_budget_summary_aggregation(self):
        """Test budget summary endpoint aggregation."""
        # Create multiple budget entries
        Budget.objects.create(
            account=self.account,
            cost_center=self.cost_center,
            company=self.company,
            year=2025,
            month=1,
            budgeted_amount=45000
        )
        Budget.objects.create(
            account=self.account,
            cost_center=self.cost_center,
            company=self.company,
            year=2025,
            month=2,
            budgeted_amount=46000
        )
        
        # Get summary
        url = f'/api/v1/finance-core/budgets/summary/?company={self.company.company_id}&year=2025'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify aggregation
        summary = response.data['summary']
        expense_summary = next(s for s in summary if s['account_type'] == 'EXPENSE')
        self.assertEqual(expense_summary['total_budgeted'], '91000.00')
        self.assertEqual(expense_summary['entry_count'], 2)
```

### 9.3 Performance Tests

**Test Coverage**: Query performance, bulk operations, and scalability.

**Test Files**:
- `apps/finance_core/tests/test_performance.py`

**Example Performance Test**:

```python
# apps/finance_core/tests/test_performance.py
from django.test import TestCase
from django.test.utils import override_settings
from django.db import connection
from django.test.utils import CaptureQueriesContext
from apps.finance_core.models import Budget

class BudgetQueryPerformanceTest(TestCase):
    def setUp(self):
        # Create 10,000 budget entries for testing
        # ... (setup code omitted for brevity)
        pass
    
    def test_budget_summary_query_count(self):
        """Test that budget summary uses efficient queries."""
        with CaptureQueriesContext(connection) as context:
            url = f'/api/v1/finance-core/budgets/summary/?company=1&year=2025'
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            
            # Verify query count (should be < 5 queries)
            self.assertLess(len(context.captured_queries), 5)
    
    def test_bulk_create_performance(self):
        """Test bulk create performance."""
        import time
        budgets = [
            Budget(
                account_id=1,
                cost_center_id=1,
                company_id=1,
                year=2025,
                month=i % 12 + 1,
                budgeted_amount=1000
            )
            for i in range(1000)
        ]
        
        start_time = time.time()
        Budget.objects.bulk_create(budgets)
        elapsed_time = time.time() - start_time
        
        # Verify performance (should complete in < 1 second)
        self.assertLess(elapsed_time, 1.0)
```

---

## 10. Performance Considerations

### 10.1 Query Optimization

#### 10.1.1 Use `select_related()` for Foreign Keys

**Problem**: N+1 query problem when accessing related objects.

**Solution**: Use `select_related()` to perform JOINs in a single query.

**Example**:
```python
# Bad: N+1 queries
budgets = Budget.objects.filter(company_id=1, year=2025)
for budget in budgets:
    print(budget.account.name)  # Each iteration triggers a query

# Good: Single query with JOIN
budgets = Budget.objects.filter(company_id=1, year=2025).select_related('account', 'cost_center', 'company')
for budget in budgets:
    print(budget.account.name)  # No additional queries
```

#### 10.1.2 Use `prefetch_related()` for Reverse Foreign Keys

**Problem**: N+1 query problem when accessing reverse foreign key relationships (e.g., getting all child accounts for a parent account).

**Solution**: Use `prefetch_related()` to perform a separate query and cache the results.

**Example**:
```python
# Bad: N+1 queries
accounts = Account.objects.filter(company_id=1, parent__isnull=True)
for account in accounts:
    for child in account.children.all():  # Each iteration triggers a query
        print(child.name)

# Good: Two queries (one for parents, one for all children)
accounts = Account.objects.filter(company_id=1, parent__isnull=True).prefetch_related('children')
for account in accounts:
    for child in account.children.all():  # No additional queries
        print(child.name)
```

#### 10.1.3 Use Aggregation for Summary Queries

**Problem**: Fetching all budget entries and summing in Python is slow and memory-intensive.

**Solution**: Use database aggregation (`Sum`, `Count`, `Avg`) to perform calculations in the database.

**Example**:
```python
# Bad: Fetch all entries and sum in Python
budgets = Budget.objects.filter(company_id=1, year=2025)
total_budget = sum(b.budgeted_amount for b in budgets)  # Slow for large datasets

# Good: Use database aggregation
from django.db.models import Sum
total_budget = Budget.objects.filter(company_id=1, year=2025).aggregate(total=Sum('budgeted_amount'))['total']
```

### 10.2 Bulk Operations

#### 10.2.1 Use `bulk_create()` for Multiple Inserts

**Problem**: Creating budget entries one-by-one is slow (each insert is a separate database transaction).

**Solution**: Use `bulk_create()` to insert multiple rows in a single query.

**Example**:
```python
# Bad: Multiple inserts
for month in range(1, 13):
    Budget.objects.create(
        account_id=1,
        cost_center_id=1,
        company_id=1,
        year=2025,
        month=month,
        budgeted_amount=10000
    )

# Good: Bulk insert
budgets = [
    Budget(
        account_id=1,
        cost_center_id=1,
        company_id=1,
        year=2025,
        month=month,
        budgeted_amount=10000
    )
    for month in range(1, 13)
]
Budget.objects.bulk_create(budgets)
```

**Note**: `bulk_create()` does NOT trigger `save()` signals or call `full_clean()`. Use `bulk_create(budgets, ignore_conflicts=True)` to skip duplicate entries instead of raising errors.

#### 10.2.2 Use `bulk_update()` for Multiple Updates

**Problem**: Updating budget entries one-by-one is slow.

**Solution**: Use `bulk_update()` to update multiple rows in a single query.

**Example**:
```python
# Bad: Multiple updates
budgets = Budget.objects.filter(company_id=1, year=2025, month=1)
for budget in budgets:
    budget.budgeted_amount *= 1.05  # 5% increase
    budget.save()

# Good: Bulk update
budgets = Budget.objects.filter(company_id=1, year=2025, month=1)
for budget in budgets:
    budget.budgeted_amount *= 1.05
Budget.objects.bulk_update(budgets, ['budgeted_amount'])
```

### 10.3 Caching Strategy (Phase 2)

**Use Case**: Budget summary queries are read-heavy and can be cached to reduce database load.

**Implementation**: Use Django's cache framework with Redis backend.

**Example**:
```python
# finance_core/api/viewsets/budget_viewset.py
from django.core.cache import cache
from django.utils.encoding import force_str

class BudgetViewSet(viewsets.ModelViewSet):
    @action(detail=False, methods=['get'])
    def summary(self, request):
        company_id = request.query_params.get('company')
        year = request.query_params.get('year')
        group_by = request.query_params.get('group_by', 'account_type')
        
        # Generate cache key
        cache_key = f'budget_summary:{company_id}:{year}:{group_by}'
        
        # Try to get from cache
        cached_result = cache.get(cache_key)
        if cached_result:
            return Response(cached_result)
        
        # Calculate summary (expensive query)
        summary = self._calculate_summary(company_id, year, group_by)
        
        # Cache for 1 hour
        cache.set(cache_key, summary, timeout=3600)
        
        return Response(summary)
```

**Cache Invalidation**: Invalidate cache when budget entries are created/updated/deleted.

```python
# finance_core/models.py
from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver(post_save, sender=Budget)
@receiver(post_delete, sender=Budget)
def invalidate_budget_summary_cache(sender, instance, **kwargs):
    """Invalidate budget summary cache when budget entries change."""
    cache_pattern = f'budget_summary:{instance.company_id}:{instance.year}:*'
    cache.delete_pattern(cache_pattern)  # Requires Redis backend
```

### 10.4 Database Connection Pooling

**Use Case**: High-concurrency API requests can exhaust database connections.

**Implementation**: Use `pgbouncer` or Django's `CONN_MAX_AGE` setting to enable connection pooling.

**Configuration** (`settings.py`):
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'aquamind',
        'USER': 'aquamind_user',
        'PASSWORD': 'password',
        'HOST': 'localhost',
        'PORT': '5432',
        'CONN_MAX_AGE': 600,  # Keep connections alive for 10 minutes
    }
}
```

---

## Conclusion

This architecture document provides a comprehensive blueprint for implementing the **Financial Core** feature in AquaMind. The design ensures:

1. **Clear Separation**: The `finance_core` app is architecturally separate from the existing `finance` app, with well-defined integration points.
2. **Scalability**: The data model and API design support hierarchical accounts, cost centers, and multi-year budgeting.
3. **Performance**: Query optimization, bulk operations, and caching strategies ensure the system can handle large datasets efficiently.
4. **Maintainability**: Comprehensive testing, audit trails, and adherence to AquaMind's API standards ensure long-term maintainability.

The next step is to proceed with the **Implementation Plan** (separate document) and **API Specification** (separate document) to guide the development process.
