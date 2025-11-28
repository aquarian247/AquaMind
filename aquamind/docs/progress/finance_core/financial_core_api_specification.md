# Financial Core API Specification

**AquaMind Financial Planning & Budgeting Module - REST API Documentation**

**Version**: 2.0  
**Date**: November 26, 2025  
**Base URL**: `/api/v1/finance-core/`

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Account Group Endpoints](#account-group-endpoints)
4. [Account Endpoints](#account-endpoints)
5. [Cost Center Endpoints](#cost-center-endpoints)
6. [Budget Endpoints](#budget-endpoints)
7. [Budget Entry Endpoints](#budget-entry-endpoints)
8. [Period Lock Endpoints](#period-lock-endpoints)
9. [Valuation Run Endpoints](#valuation-run-endpoints)
10. [Reporting Endpoints](#reporting-endpoints)
11. [Error Handling](#error-handling)
12. [Rate Limiting](#rate-limiting)

---

## Overview

The Financial Core API provides RESTful endpoints for managing the Chart of Accounts (CoA), Cost Centers, Budgets, and EoM processes (allocation, valuation, locking) in AquaMind. All endpoints follow Django REST Framework conventions and return JSON responses.

NB! Do not take for granted that all variables and data types are 100% correct. This is a blueprint/guide - not the code. 

### API Conventions

- **URL Structure**: `/api/v1/finance-core/{resource}/`
- **Naming**: Kebab-case for URLs (`account-groups`, `cost-centers`)
- **HTTP Methods**: GET (list/retrieve), POST (create), PUT/PATCH (update), DELETE (delete)
- **Pagination**: Default page size is 50, configurable via `?page_size=` parameter
- **Filtering**: Query parameters for filtering (e.g., `?account_type=EXPENSE`)
- **Searching**: `?search=` parameter for full-text search
- **Ordering**: `?ordering=` parameter for sorting (e.g., `?ordering=-created_at`)

### Currency Handling
All monetary amounts (e.g., `budgeted_amount`, totals in reports) are in the specified currency, using ISO 4217 3-letter alphabetic codes (e.g., "DKK" for Danish Krone, "EUR" for Euro, "GBP" for Pound Sterling, "USD" for United States Dollar). Currencies must match the company's default currency (from `finance.DimCompany.currency`) unless explicitly overridden in Budget Entries. The API does not perform automatic currency conversion—clients must handle conversions if needed. Invalid codes (e.g., non-ISO like "US Dollars") will raise validation errors. For a full list of active codes, refer to the ISO 4217 standard.

---

## Authentication

All API endpoints require authentication. Use Django REST Framework's token authentication or session authentication.

**Header**:
```
Authorization: Token <your_api_token>
```

**Example**:
```bash
curl -H "Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b" \
     https://aquamind.example.com/api/v1/finance-core/accounts/
```

---

## Account Group Endpoints

Account Groups provide hierarchical organization for the Chart of Accounts.

### 1. List Account Groups

**Endpoint**: `GET /api/v1/finance-core/account-groups/`

**Description**: Retrieve a paginated list of all account groups.

**Query Parameters**:
- `account_type` (string, optional): Filter by account type (`ASSET`, `LIABILITY`, `EQUITY`, `REVENUE`, `EXPENSE`)
- `parent` (integer, optional): Filter by parent group ID
- `search` (string, optional): Search by code or name
- `ordering` (string, optional): Sort by field (e.g., `display_order`, `-created_at`)
- `page` (integer, optional): Page number (default: 1)
- `page_size` (integer, optional): Items per page (default: 50)

**Example Request**:
```bash
GET /api/v1/finance-core/account-groups/?account_type=EXPENSE&ordering=display_order
```

**Example Response** (200 OK):
```json
{
  "count": 3,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "code": "OPEX",
      "name": "Operating Expenses",
      "account_type": "EXPENSE",
      "parent": null,
      "parent_code": null,
      "full_path": "OPEX",
      "display_order": 1,
      "created_at": "2025-01-15T10:00:00Z",
      "updated_at": "2025-01-15T10:00:00Z"
    },
    {
      "id": 2,
      "code": "FEED",
      "name": "Feed Costs",
      "account_type": "EXPENSE",
      "parent": 1,
      "parent_code": "OPEX",
      "full_path": "OPEX > FEED",
      "display_order": 1,
      "created_at": "2025-01-15T10:05:00Z",
      "updated_at": "2025-01-15T10:05:00Z"
    }
  ]
}
```

### 2. Create Account Group

**Endpoint**: `POST /api/v1/finance-core/account-groups/`

**Description**: Create a new account group.

**Request Body**:
```json
{
  "code": "LABOR",
  "name": "Labor Costs",
  "account_type": "EXPENSE",
  "parent": 1,
  "display_order": 2
}
```

**Example Response** (201 Created):
```json
{
  "id": 3,
  "code": "LABOR",
  "name": "Labor Costs",
  "account_type": "EXPENSE",
  "parent": 1,
  "parent_code": "OPEX",
  "full_path": "OPEX > LABOR",
  "display_order": 2,
  "created_at": "2025-01-15T11:00:00Z",
  "updated_at": "2025-01-15T11:00:00Z"
}
```

**Validation Errors** (400 Bad Request):
```json
{
  "code": ["This field must be unique."],
  "parent": ["Parent group must have the same account type."]
}
```

### 3. Retrieve Account Group

**Endpoint**: `GET /api/v1/finance-core/account-groups/{id}/`

**Description**: Retrieve a single account group by ID.

**Example Response** (200 OK):
```json
{
  "id": 1,
  "code": "OPEX",
  "name": "Operating Expenses",
  "account_type": "EXPENSE",
  "parent": null,
  "parent_code": null,
  "full_path": "OPEX",
  "display_order": 1,
  "created_at": "2025-01-15T10:00:00Z",
  "updated_at": "2025-01-15T10:00:00Z"
}
```

### 4. Update Account Group

**Endpoint**: `PUT /api/v1/finance-core/account-groups/{id}/`  
**Endpoint**: `PATCH /api/v1/finance-core/account-groups/{id}/` (partial update)

**Description**: Update an existing account group.

**Request Body** (PATCH example):
```json
{
  "name": "Operating Expenses (Updated)",
  "display_order": 0
}
```

**Example Response** (200 OK):
```json
{
  "id": 1,
  "code": "OPEX",
  "name": "Operating Expenses (Updated)",
  "account_type": "EXPENSE",
  "parent": null,
  "parent_code": null,
  "full_path": "OPEX",
  "display_order": 0,
  "created_at": "2025-01-15T10:00:00Z",
  "updated_at": "2025-01-15T12:00:00Z"
}
```

### 5. Delete Account Group

**Endpoint**: `DELETE /api/v1/finance-core/account-groups/{id}/`

**Description**: Delete an account group. Fails if the group has child groups or accounts.

**Example Response** (204 No Content):
```
(empty response body)
```

**Error Response** (400 Bad Request):
```json
{
  "detail": "Cannot delete account group with child groups or accounts."
}
```

---

## Account Endpoints

Accounts represent individual line items in the Chart of Accounts.

### 1. List Accounts

**Endpoint**: `GET /api/v1/finance-core/accounts/`

**Description**: Retrieve a paginated list of all accounts.

**Query Parameters**:
- `account_type` (string, optional): Filter by account type
- `group` (integer, optional): Filter by account group ID
- `is_active` (boolean, optional): Filter by active status (`true` or `false`)
- `search` (string, optional): Search by code, name, or description
- `ordering` (string, optional): Sort by field (e.g., `code`, `-created_at`)
- `page` (integer, optional): Page number
- `page_size` (integer, optional): Items per page

**Example Request**:
```bash
GET /api/v1/finance-core/accounts/?account_type=EXPENSE&is_active=true&ordering=code
```

**Example Response** (200 OK):
```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "code": "5100",
      "name": "Smolt Feed",
      "account_type": "EXPENSE",
      "group": 2,
      "group_code": "FEED",
      "group_name": "Feed Costs",
      "description": "Feed costs for smolt production",
      "is_active": true,
      "created_at": "2025-01-15T10:10:00Z",
      "updated_at": "2025-01-15T10:10:00Z"
    },
    {
      "id": 2,
      "code": "5110",
      "name": "Parr Feed",
      "account_type": "EXPENSE",
      "group": 2,
      "group_code": "FEED",
      "group_name": "Feed Costs",
      "description": "Feed costs for parr production",
      "is_active": true,
      "created_at": "2025-01-15T10:15:00Z",
      "updated_at": "2025-01-15T10:15:00Z"
    }
  ]
}
```

### 2. Create Account

**Endpoint**: `POST /api/v1/finance-core/accounts/`

**Description**: Create a new account.

**Request Body**:
```json
{
  "code": "5200",
  "name": "Farm Labor",
  "account_type": "EXPENSE",
  "group": 3,
  "description": "Labor costs for farm operations",
  "is_active": true
}
```

**Example Response** (201 Created):
```json
{
  "id": 3,
  "code": "5200",
  "name": "Farm Labor",
  "account_type": "EXPENSE",
  "group": 3,
  "group_code": "LABOR",
  "group_name": "Labor Costs",
  "description": "Labor costs for farm operations",
  "is_active": true,
  "created_at": "2025-01-15T11:00:00Z",
  "updated_at": "2025-01-15T11:00:00Z"
}
```

**Validation Errors** (400 Bad Request):
```json
{
  "code": ["This field must be unique."],
  "account_type": ["Account type must match group type."]
}
```

### 3. Retrieve Account

**Endpoint**: `GET /api/v1/finance-core/accounts/{id}/`

**Description**: Retrieve a single account by ID.

**Example Response** (200 OK):
```json
{
  "id": 1,
  "code": "5100",
  "name": "Smolt Feed",
  "account_type": "EXPENSE",
  "group": 2,
  "group_code": "FEED",
  "group_name": "Feed Costs",
  "description": "Feed costs for smolt production",
  "is_active": true,
  "created_at": "2025-01-15T10:10:00Z",
  "updated_at": "2025-01-15T10:10:00Z"
}
```

### 4. Update Account

**Endpoint**: `PUT /api/v1/finance-core/accounts/{id}/`  
**Endpoint**: `PATCH /api/v1/finance-core/accounts/{id}/` (partial update)

**Description**: Update an existing account.

**Request Body** (PATCH example):
```json
{
  "name": "Smolt Feed (Updated)",
  "is_active": false
}
```

**Example Response** (200 OK):
```json
{
  "id": 1,
  "code": "5100",
  "name": "Smolt Feed (Updated)",
  "account_type": "EXPENSE",
  "group": 2,
  "group_code": "FEED",
  "group_name": "Feed Costs",
  "description": "Feed costs for smolt production",
  "is_active": false,
  "created_at": "2025-01-15T10:10:00Z",
  "updated_at": "2025-01-15T12:00:00Z"
}
```

### 5. Delete Account

**Endpoint**: `DELETE /api/v1/finance-core/accounts/{id}/`

**Description**: Delete an account. Fails if the account has budget entries.

**Example Response** (204 No Content):
```
(empty response body)
```

**Error Response** (400 Bad Request):
```json
{
  "detail": "Cannot delete account with existing budget entries."
}
```

### 6. Custom Action: Get Accounts by Type

**Endpoint**: `GET /api/v1/finance-core/accounts/by-type/`

**Description**: Retrieve accounts filtered by account type (only active accounts).

**Query Parameters**:
- `type` (string, required): Account type (`ASSET`, `LIABILITY`, `EQUITY`, `REVENUE`, `EXPENSE`)

**Example Request**:
```bash
GET /api/v1/finance-core/accounts/by-type/?type=REVENUE
```

**Example Response** (200 OK):
```json
[
  {
    "id": 10,
    "code": "4000",
    "name": "Harvest Revenue",
    "account_type": "REVENUE",
    "group": 5,
    "group_code": "REVENUE",
    "group_name": "Sales Revenue",
    "description": "Revenue from harvest sales",
    "is_active": true,
    "created_at": "2025-01-15T10:20:00Z",
    "updated_at": "2025-01-15T10:20:00Z"
  }
]
```

### 7. Custom Action: Get Active Accounts

**Endpoint**: `GET /api/v1/finance-core/accounts/active/`

**Description**: Retrieve only active accounts (shortcut for `?is_active=true`).

**Example Response** (200 OK):
```json
[
  {
    "id": 1,
    "code": "5100",
    "name": "Smolt Feed",
    "account_type": "EXPENSE",
    ...
  },
  {
    "id": 2,
    "code": "5110",
    "name": "Parr Feed",
    "account_type": "EXPENSE",
    ...
  }
]
```

---

## Cost Center Endpoints

Cost Centers enable cost allocation across operational dimensions (farms, lifecycle stages, projects).

### 1. List Cost Centers

**Endpoint**: `GET /api/v1/finance-core/cost-centers/`

**Description**: Retrieve a paginated list of all cost centers.

**Query Parameters**:
- `company` (integer, optional): Filter by company ID
- `is_active` (boolean, optional): Filter by active status
- `search` (string, optional): Search by code, name, or description
- `ordering` (string, optional): Sort by field (e.g., `code`, `-created_at`)
- `page` (integer, optional): Page number
- `page_size` (integer, optional): Items per page

**Example Request**:
```bash
GET /api/v1/finance-core/cost-centers/?company=1&is_active=true&ordering=code
```

**Example Response** (200 OK):
```json
{
  "count": 3,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "code": "FARM-01",
      "name": "Faroe Islands - Farm 1",
      "company": 1,
      "company_code": "BAKKAFROST",
      "company_name": "Bakkafrost P/F",
      "description": "Main farm in Faroe Islands",
      "is_active": true,
      "created_at": "2025-01-15T10:25:00Z",
      "updated_at": "2025-01-15T10:25:00Z"
    },
    {
      "id": 2,
      "code": "HATCHERY",
      "name": "Main Hatchery",
      "company": 1,
      "company_code": "BAKKAFROST",
      "company_name": "Bakkafrost P/F",
      "description": "Central hatchery facility",
      "is_active": true,
      "created_at": "2025-01-15T10:30:00Z",
      "updated_at": "2025-01-15T10:30:00Z"
    }
  ]
}
```

### 2. Create Cost Center

**Endpoint**: `POST /api/v1/finance-core/cost-centers/`

**Description**: Create a new cost center.

**Request Body**:
```json
{
  "code": "SMOLT-HALL",
  "name": "Smolt Production Hall",
  "company": 1,
  "description": "Smolt production facility",
  "is_active": true
}
```

**Example Response** (201 Created):
```json
{
  "id": 3,
  "code": "SMOLT-HALL",
  "name": "Smolt Production Hall",
  "company": 1,
  "company_code": "BAKKAFROST",
  "company_name": "Bakkafrost P/F",
  "description": "Smolt production facility",
  "is_active": true,
  "created_at": "2025-01-15T11:00:00Z",
  "updated_at": "2025-01-15T11:00:00Z"
}
```

### 3. Retrieve Cost Center

**Endpoint**: `GET /api/v1/finance-core/cost-centers/{id}/`

**Description**: Retrieve a single cost center by ID.

**Example Response** (200 OK):
```json
{
  "id": 1,
  "code": "FARM-01",
  "name": "Faroe Islands - Farm 1",
  "company": 1,
  "company_code": "BAKKAFROST",
  "company_name": "Bakkafrost P/F",
  "description": "Main farm in Faroe Islands",
  "is_active": true,
  "created_at": "2025-01-15T10:25:00Z",
  "updated_at": "2025-01-15T10:25:00Z"
}
```

### 4. Update Cost Center

**Endpoint**: `PUT /api/v1/finance-core/cost-centers/{id}/`  
**Endpoint**: `PATCH /api/v1/finance-core/cost-centers/{id}/` (partial update)

**Description**: Update an existing cost center.

**Request Body** (PATCH example):
```json
{
  "name": "Faroe Islands - Farm 1 (Expanded)",
  "is_active": false
}
```

**Example Response** (200 OK):
```json
{
  "id": 1,
  "code": "FARM-01",
  "name": "Faroe Islands - Farm 1 (Expanded)",
  "company": 1,
  "company_code": "BAKKAFROST",
  "company_name": "Bakkafrost P/F",
  "description": "Main farm in Faroe Islands",
  "is_active": false,
  "created_at": "2025-01-15T10:25:00Z",
  "updated_at": "2025-01-15T12:00:00Z"
}
```

### 5. Delete Cost Center

**Endpoint**: `DELETE /api/v1/finance-core/cost-centers/{id}/`

**Description**: Delete a cost center. Fails if the cost center has budget entries.

**Example Response** (204 No Content):
```
(empty response body)
```

### 6. Custom Action: Get Active Cost Centers

**Endpoint**: `GET /api/v1/finance-core/cost-centers/active/`

**Description**: Retrieve only active cost centers.

**Example Response** (200 OK):
```json
[
  {
    "id": 1,
    "code": "FARM-01",
    "name": "Faroe Islands - Farm 1",
    ...
  }
]
```

### 7. Custom Action: Get Cost Centers by Company

**Endpoint**: `GET /api/v1/finance-core/cost-centers/by-company/`

**Description**: Retrieve cost centers for a specific company (only active).

**Query Parameters**:
- `company_id` (integer, required): Company ID

**Example Request**:
```bash
GET /api/v1/finance-core/cost-centers/by-company/?company_id=1
```

**Example Response** (200 OK):
```json
[
  {
    "id": 1,
    "code": "FARM-01",
    "name": "Faroe Islands - Farm 1",
    ...
  },
  {
    "id": 2,
    "code": "HATCHERY",
    "name": "Main Hatchery",
    ...
  }
]
```

---

## Budget Endpoints

Budgets represent annual financial plans, optionally linked to scenarios.

### 1. List Budgets

**Endpoint**: `GET /api/v1/finance-core/budgets/`

**Description**: Retrieve a paginated list of all budgets.

**Query Parameters**:
- `year` (integer, optional): Filter by fiscal year
- `company` (integer, optional): Filter by company ID
- `scenario` (integer, optional): Filter by scenario ID
- `is_active` (boolean, optional): Filter by active status
- `search` (string, optional): Search by name or description
- `ordering` (string, optional): Sort by field (e.g., `-year`, `name`)
- `page` (integer, optional): Page number
- `page_size` (integer, optional): Items per page

**Example Request**:
```bash
GET /api/v1/finance-core/budgets/?year=2025&company=1&ordering=-created_at
```

**Example Response** (200 OK):
```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "2025 Base Budget",
      "year": 2025,
      "company": 1,
      "company_code": "BAKKAFROST",
      "company_name": "Bakkafrost P/F",
      "scenario": null,
      "scenario_name": null,
      "description": "Base budget for 2025 fiscal year",
      "currency": "DKK",  // Added: Assumed from company.currency
      "is_active": true,
      "entry_count": 120,
      "total_budgeted": 5000000.00,
      "created_at": "2025-01-15T10:35:00Z",
      "updated_at": "2025-01-15T10:35:00Z",
      "created_by": 1
    },
    {
      "id": 2,
      "name": "2025 Expansion Scenario",
      "year": 2025,
      "company": 1,
      "company_code": "BAKKAFROST",
      "company_name": "Bakkafrost P/F",
      "scenario": 5,
      "scenario_name": "Farm Expansion 2025",
      "description": "Budget for expansion scenario",
      "currency": "DKK",  // Added: Assumed from company.currency
      "is_active": false,
      "entry_count": 150,
      "total_budgeted": 7500000.00,
      "created_at": "2025-01-15T11:00:00Z",
      "updated_at": "2025-01-15T11:00:00Z",
      "created_by": 1
    }
  ]
}
```

### 2. Create Budget

**Endpoint**: `POST /api/v1/finance-core/budgets/`

**Description**: Create a new budget.

**Request Body**:
```json
{
  "name": "2026 Base Budget",
  "year": 2026,
  "company": 1,
  "scenario": null,
  "description": "Base budget for 2026 fiscal year",
  "is_active": false
}
```

**Example Response** (201 Created):
```json
{
  "id": 3,
  "name": "2026 Base Budget",
  "year": 2026,
  "company": 1,
  "company_code": "BAKKAFROST",
  "company_name": "Bakkafrost P/F",
  "scenario": null,
  "scenario_name": null,
  "description": "Base budget for 2026 fiscal year",
  "currency": "DKK",
  "is_active": false,
  "entry_count": 0,
  "total_budgeted": 0.00,
  "created_at": "2025-01-15T12:00:00Z",
  "updated_at": "2025-01-15T12:00:00Z",
  "created_by": 1
}
```

### 3. Retrieve Budget

**Endpoint**: `GET /api/v1/finance-core/budgets/{id}/`

**Description**: Retrieve a single budget by ID (includes all budget entries).

**Example Response** (200 OK):
```json
{
  "id": 1,
  "name": "2025 Base Budget",
  "year": 2025,
  "company": 1,
  "company_code": "BAKKAFROST",
  "company_name": "Bakkafrost P/F",
  "scenario": null,
  "scenario_name": null,
  "description": "Base budget for 2025 fiscal year",
  "currency": "DKK",
  "is_active": true,
  "entry_count": 2,
  "total_budgeted": 100000.00,
  "created_at": "2025-01-15T10:35:00Z",
  "updated_at": "2025-01-15T10:35:00Z",
  "created_by": 1,
  "entries": [
    {
      "id": 1,
      "budget": 1,
      "currency": "DKK",
      "account": 1,
      "account_code": "5100",
      "account_name": "Smolt Feed",
      "cost_center": 1,
      "cost_center_code": "FARM-01",
      "cost_center_name": "Faroe Islands - Farm 1",
      "month": 1,
      "budgeted_amount": 50000.00,
      "notes": "",
      "created_at": "2025-01-15T10:40:00Z",
      "updated_at": "2025-01-15T10:40:00Z"
    },
    {
      "id": 2,
      "budget": 1,
      "currency": "DKK",
      "account": 1,
      "account_code": "5100",
      "account_name": "Smolt Feed",
      "cost_center": 1,
      "cost_center_code": "FARM-01",
      "cost_center_name": "Faroe Islands - Farm 1",
      "month": 2,
      "budgeted_amount": 50000.00,
      "notes": "",
      "created_at": "2025-01-15T10:45:00Z",
      "updated_at": "2025-01-15T10:45:00Z"
    }
  ]
}
```

### 4. Update Budget

**Endpoint**: `PUT /api/v1/finance-core/budgets/{id}/`  
**Endpoint**: `PATCH /api/v1/finance-core/budgets/{id}/` (partial update)

**Description**: Update an existing budget.

**Request Body** (PATCH example):
```json
{
  "name": "2025 Base Budget (Revised)",
  "is_active": false
}
```

**Example Response** (200 OK):
```json
{
  "id": 1,
  "name": "2025 Base Budget (Revised)",
  "year": 2025,
  ...
  "is_active": false,
  "updated_at": "2025-01-15T13:00:00Z"
}
```

### 5. Delete Budget

**Endpoint**: `DELETE /api/v1/finance-core/budgets/{id}/`

**Description**: Delete a budget (cascades to all budget entries).

**Example Response** (204 No Content):
```
(empty response body)
```

### 6. Custom Action: Get Budget Summary

**Endpoint**: `GET /api/v1/finance-core/budgets/{id}/summary/`

**Description**: Get aggregated budget summary by account type.

**Example Response** (200 OK):
```json
{
  "budget_id": 1,
  "budget_name": "2025 Base Budget",
  "year": 2025,
  "currency": "DKK",
  "summary_by_type": [
    {
      "account_type": "REVENUE",
      "total": 10000000.00
    },
    {
      "account_type": "EXPENSE",
      "total": 8000000.00
    }
  ],
  "net_income": 2000000.00
}
```

### 7. Custom Action: Copy Budget

**Endpoint**: `POST /api/v1/finance-core/budgets/{id}/copy/`

**Description**: Copy a budget to a new year with all entries.

**Request Body**:
```json
{
  "new_year": 2026,
  "new_name": "2026 Base Budget (Copied from 2025)"
}
```

**Example Response** (201 Created):
```json
{
  "id": 4,
  "name": "2026 Base Budget (Copied from 2025)",
  "year": 2026,
  "company": 1,
  ...
  "entry_count": 120,
  "created_at": "2025-01-15T13:00:00Z"
}
```

### 8. Custom Action: Get Budgets by Scenario

**Endpoint**: `GET /api/v1/finance-core/budgets/by-scenario/`

**Description**: Retrieve budgets for a specific scenario.

**Query Parameters**:
- `scenario_id` (integer, required): Scenario ID

**Example Request**:
```bash
GET /api/v1/finance-core/budgets/by-scenario/?scenario_id=5
```

**Example Response** (200 OK):
```json
[
  {
    "id": 2,
    "name": "2025 Expansion Scenario",
    "year": 2025,
    "scenario": 5,
    "scenario_name": "Farm Expansion 2025",
    ...
  }
]
```

---

## Budget Entry Endpoints

Budget Entries represent monthly budgeted amounts for specific account/cost center combinations.

### 1. List Budget Entries

**Endpoint**: `GET /api/v1/finance-core/budget-entries/`

**Description**: Retrieve a paginated list of all budget entries.

**Query Parameters**:
- `budget` (integer, optional): Filter by budget ID
- `currency` (string, optional): Filter by ISO 4217 code (e.g., "DKK")
- `account` (integer, optional): Filter by account ID
- `cost_center` (integer, optional): Filter by cost center ID
- `month` (integer, optional): Filter by month (1-12)
- `ordering` (string, optional): Sort by field (e.g., `month`, `-budgeted_amount`)
- `page` (integer, optional): Page number
- `page_size` (integer, optional): Items per page

**Example Request**:
```bash
GET /api/v1/finance-core/budget-entries/?budget=1&month=1&ordering=account__code
```

**Example Response** (200 OK):
```json
{
  "count": 10,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "budget": 1,
      "currency": "DKK",
      "account": 1,
      "account_code": "5100",
      "account_name": "Smolt Feed",
      "cost_center": 1,
      "cost_center_code": "FARM-01",
      "cost_center_name": "Faroe Islands - Farm 1",
      "month": 1,
      "budgeted_amount": 50000.00,
      "notes": "",
      "created_at": "2025-01-15T10:40:00Z",
      "updated_at": "2025-01-15T10:40:00Z"
    }
  ]
}
```

### 2. Create Budget Entry

**Endpoint**: `POST /api/v1/finance-core/budget-entries/`

**Description**: Create a new budget entry.

**Request Body**:
```json
{
  "budget": 1,
  "currency": "DKK",
  "account": 1,
  "cost_center": 1,
  "month": 3,
  "budgeted_amount": 52000.00,
  "notes": "Increased due to seasonal demand"
}
```

**Example Response** (201 Created):
```json
{
  "id": 3,
  "budget": 1,
  "currency": "DKK",
  "account": 1,
  "account_code": "5100",
  "account_name": "Smolt Feed",
  "cost_center": 1,
  "cost_center_code": "FARM-01",
  "cost_center_name": "Faroe Islands - Farm 1",
  "month": 3,
  "budgeted_amount": 52000.00,
  "notes": "Increased due to seasonal demand",
  "created_at": "2025-01-15T12:00:00Z",
  "updated_at": "2025-01-15T12:00:00Z"
}
```

### 3. Retrieve Budget Entry

**Endpoint**: `GET /api/v1/finance-core/budget-entries/{id}/`

**Description**: Retrieve a single budget entry by ID.

**Example Response** (200 OK):
```json
{
  "id": 1,
  "budget": 1,
  "currency": "DKK",
  "account": 1,
  "account_code": "5100",
  "account_name": "Smolt Feed",
  "cost_center": 1,
  "cost_center_code": "FARM-01",
  "cost_center_name": "Faroe Islands - Farm 1",
  "month": 1,
  "budgeted_amount": 50000.00,
  "notes": "",
  "created_at": "2025-01-15T10:40:00Z",
  "updated_at": "2025-01-15T10:40:00Z"
}
```

### 4. Update Budget Entry

**Endpoint**: `PUT /api/v1/finance-core/budget-entries/{id}/`  
**Endpoint**: `PATCH /api/v1/finance-core/budget-entries/{id}/` (partial update)

**Description**: Update an existing budget entry.

**Request Body** (PATCH example):
```json
{
  "budgeted_amount": 55000.00,
  "notes": "Revised upward due to price increase"
}
```

**Example Response** (200 OK):
```json
{
  "id": 1,
  "budget": 1,
  "currency": "DKK",
  "account": 1,
  "account_code": "5100",
  "account_name": "Smolt Feed",
  "cost_center": 1,
  "cost_center_code": "FARM-01",
  "cost_center_name": "Faroe Islands - Farm 1",
  "month": 1,
  "budgeted_amount": 55000.00,
  "notes": "Revised upward due to price increase",
  "created_at": "2025-01-15T10:40:00Z",
  "updated_at": "2025-01-15T13:00:00Z"
}
```

### 5. Delete Budget Entry

**Endpoint**: `DELETE /api/v1/finance-core/budget-entries/{id}/`

**Description**: Delete a budget entry.

**Example Response** (204 No Content):
```
(empty response body)
```

### 6. Custom Action: Bulk Create Budget Entries

**Endpoint**: `POST /api/v1/finance-core/budget-entries/bulk-create/`

**Description**: Create multiple budget entries in a single request (useful for spreadsheet-like data entry).

**Request Body**:
```json
{
  "entries": [
    {
      "budget": 1,
      "currency": "DKK",
      "account": 1,
      "cost_center": 1,
      "month": 1,
      "budgeted_amount": 50000.00
    },
    {
      "budget": 1,
      "currency": "GBP",
      "account": 1,
      "cost_center": 1,
      "month": 2,
      "budgeted_amount": 52000.00
    },
    {
      "budget": 1,
      "currency": "EUR",
      "account": 1,
      "cost_center": 1,
      "month": 3,
      "budgeted_amount": 51000.00
    }
  ]
}
```

**Example Response** (201 Created):
```json
[
  {
    "id": 10,
    "budget": 1,
    "currency": "DKK",
    "account": 1,
    "account_code": "5100",
    "account_name": "Smolt Feed",
    "cost_center": 1,
    "cost_center_code": "FARM-01",
    "cost_center_name": "Faroe Islands - Farm 1",
    "month": 1,
    "budgeted_amount": 50000.00,
    ...
  },
  {
    "id": 11,
    "budget": 1,
    ...
    "month": 2,
    "budgeted_amount": 52000.00,
    ...
  },
  {
    "id": 12,
    "budget": 1,
    ...
    "month": 3,
    "budgeted_amount": 51000.00,
    ...
  }
]
```

**Note**: All entries in a budget should use the same currency to avoid aggregation issues; mixed currencies are allowed but reports assume uniformity.

---

## Reporting Endpoints

Reporting endpoints provide aggregated financial data for dashboards and analysis.

### 1. Budget Summary Report

**Endpoint**: `GET /api/v1/finance-core/reports/budget-summary/`

**Description**: Get budget summary with monthly and account type aggregations.

**Query Parameters**:
- `budget_id` (integer, required): Budget ID

**Example Request**:
```bash
GET /api/v1/finance-core/reports/budget-summary/?budget_id=1
```

**Example Response** (200 OK):
```json
{
  "budget_id": 1,
  "budget_name": "2025 Base Budget",
  "year": 2025,
  "monthly_summary": [
    {
      "account__account_type": "REVENUE",
      "month": 1,
      "total": 800000.00,
      "currency": "DKK"
    },
    {
      "account__account_type": "EXPENSE",
      "month": 1,
      "total": 650000.00,
      "currency": "DKK"
    },
    {
      "account__account_type": "REVENUE",
      "month": 2,
      "total": 850000.00,
      "currency": "DKK"
    },
    {
      "account__account_type": "EXPENSE",
      "month": 2,
      "total": 680000.00,
      "currency": "DKK"
    }
  ],
  "totals_by_type": [
    {
      "account__account_type": "REVENUE",
      "total": 10000000.00,
      "currency": "DKK"
    },
    {
      "account__account_type": "EXPENSE",
      "total": 8000000.00,
      "currency": "DKK"
    }
  ]
}
```

### 2. P&L Projection Report

**Endpoint**: `GET /api/v1/finance-core/reports/pl-projection/`

**Description**: Get Profit & Loss projection based on budget data.

**Query Parameters**:
- `budget_id` (integer, required): Budget ID

**Example Request**:
```bash
GET /api/v1/finance-core/reports/pl-projection/?budget_id=1
```

**Example Response** (200 OK):
```json
{
  "budget_id": 1,
  "budget_name": "2025 Base Budget",
  "year": 2025,
  "total_revenue": 10000000.00,
  "total_expenses": 8000000.00,
  "net_income": 2000000.00,
  "currency": "DKK",
  "monthly_pl": [
    {
      "month": 1,
      "revenue": 800000.00,
      "expenses": 650000.00,
      "net_income": 150000.00,
      "currency": "DKK"
    },
    {
      "month": 2,
      "revenue": 850000.00,
      "expenses": 680000.00,
      "net_income": 170000.00,
      "currency": "DKK"
    },
    ...
  ]
}
```

---

## Error Handling

All API endpoints return standard HTTP status codes and JSON error responses.

### HTTP Status Codes

- **200 OK**: Successful GET/PUT/PATCH request
- **201 Created**: Successful POST request
- **204 No Content**: Successful DELETE request
- **400 Bad Request**: Validation error or malformed request
- **401 Unauthorized**: Authentication required
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Resource does not exist
- **500 Internal Server Error**: Server-side error

### Error Response Format

**Example** (400 Bad Request):
```json
{
  "code": ["This field must be unique."],
  "budgeted_amount": ["Ensure this value is greater than or equal to 0."]
}
```

**Example** (404 Not Found):
```json
{
  "detail": "Not found."
}
```

**Example** (500 Internal Server Error):
```json
{
  "detail": "Internal server error. Please contact support."
}
```

---

## Rate Limiting

API requests are rate-limited to prevent abuse.

- **Limit**: 1000 requests per hour per user
- **Header**: `X-RateLimit-Remaining` (number of requests remaining)
- **Response** (429 Too Many Requests):
```json
{
  "detail": "Request was throttled. Expected available in 3600 seconds."
}
```

---

## Conclusion

This API specification provides complete documentation for all Financial Core endpoints. Frontend agents can use this specification to integrate with the backend API, ensuring consistent data exchange and error handling.

For implementation details, see the **Financial Core Implementation Plan** and **Financial Core Architecture** documents.
```