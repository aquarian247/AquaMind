# Financial Core Documentation Package

**AquaMind Financial Planning & Budgeting Module - Complete Implementation Guide**

**Version**: 1.0  
**Date**: October 28, 2025  
**Total Documentation**: ~110,000 words across 5 comprehensive documents

---

## Table of Contents

1. [Overview](#overview)
2. [Documentation Structure](#documentation-structure)
3. [Copy Instructions](#copy-instructions)
4. [Agent Workflow Recommendations](#agent-workflow-recommendations)
5. [Key Architecture Decisions](#key-architecture-decisions)
6. [Implementation Timeline](#implementation-timeline)
7. [Testing Strategy](#testing-strategy)
8. [Troubleshooting](#troubleshooting)

---

## Overview

This package contains complete, production-ready documentation for implementing the **Financial Core** feature in AquaMind. The feature provides comprehensive financial planning and budgeting capabilities, addressing the critical gap identified in the FishTalk feature analysis.

### What's Included

- **Backend Documentation** (3 files, ~90,000 words)
  - Complete data model (Account, CostCenter, Budget, BudgetEntry, AccountGroup)
  - API endpoints specification (REST + custom actions)
  - 12-week implementation roadmap with step-by-step tasks
  
- **Frontend Documentation** (2 files, ~20,000 words)
  - Complete UI/UX design (tabbed interface, spreadsheet-like budgeting grid)
  - Component specifications with React/TypeScript code examples
  - User workflows and integration patterns

### Key Features

1. **Chart of Accounts (CoA) Management**: Hierarchical account structure with 5 account types (Asset, Liability, Equity, Revenue, Expense)
2. **Cost Center Management**: Cost allocation across operational dimensions (farms, lifecycle stages, projects)
3. **Monthly Budgeting**: Spreadsheet-like data entry interface for 12-month budgets
4. **Budget Reports**: P&L projections, budget summaries, and variance analysis
5. **Scenario Integration**: Link budgets to scenarios for what-if analysis

---

## Documentation Structure

```
FINANCIAL_CORE_COMPLETE/
├── README.md (this file)
├── backend_docs/
│   ├── financial_core_architecture.md (28,000 words)
│   ├── financial_core_implementation_plan.md (30,000 words)
│   └── financial_core_api_specification.md (32,000 words)
└── frontend_docs/
    ├── financial_core_ui_specification.md (15,000 words)
    └── financial_planning_user_guide.md (5,000 words)
```

---

## Copy Instructions

### Backend Repository: `aquarian247/AquaMind`

**Target Directory**: `aquamind/docs/progress/financial_core/`

**Commands**:
```bash
# Navigate to your AquaMind backend repository
cd /path/to/AquaMind

# Create the progress directory for Financial Core
mkdir -p aquamind/docs/progress/financial_core

# Copy backend documentation
cp /path/to/FINANCIAL_CORE_COMPLETE/backend_docs/* aquamind/docs/progress/financial_core/

# Commit the documentation
git add aquamind/docs/progress/financial_core/
git commit -m "Add Financial Core implementation documentation"
git push origin main
```

**Files Copied**:
- `financial_core_architecture.md` → Complete data model, integration architecture, business logic
- `financial_core_implementation_plan.md` → 12-week implementation roadmap with tasks
- `financial_core_api_specification.md` → Complete REST API documentation

---

### Frontend Repository: `aquarian247/AquaMind-Frontend`

**Target Directory**: `docs/progress/financial_core/`

**Commands**:
```bash
# Navigate to your AquaMind frontend repository
cd /path/to/AquaMind-Frontend

# Create the progress directory for Financial Core
mkdir -p docs/progress/financial_core

# Copy frontend documentation
cp /path/to/FINANCIAL_CORE_COMPLETE/frontend_docs/* docs/progress/financial_core/

# Commit the documentation
git add docs/progress/financial_core/
git commit -m "Add Financial Core UI implementation documentation"
git push origin main
```

**Files Copied**:
- `financial_core_ui_specification.md` → Complete UI/UX design, component specifications
- `financial_planning_user_guide.md` → End-user documentation, workflows

---

## Agent Workflow Recommendations

### Backend Implementation (Cursor.ai / Windsurf)

**Phase 1: Data Model (Week 1-2)**

**Context to Provide**:
1. `financial_core_architecture.md` (Section 2: Data Model)
2. Existing `finance` app models (`apps/finance/models.py`) for reference
3. `aquamind/docs/database/data_model.md` for existing schema

**Tasks**:
1. Create `finance_core` app structure
2. Implement models: `AccountGroup`, `Account`, `CostCenter`, `Budget`, `BudgetEntry`
3. Create migrations
4. Run migrations and verify schema

**Acceptance Criteria**:
- All models created with correct fields and relationships
- Migrations applied successfully
- No conflicts with existing `finance` app

---

**Phase 2: API Layer (Week 3-4)**

**Context to Provide**:
1. `financial_core_api_specification.md` (complete)
2. `financial_core_architecture.md` (Section 4: API Design)
3. Existing API patterns from `apps/scenario/api/viewsets.py`

**Tasks**:
1. Create serializers for all models
2. Create ViewSets with filtering, searching, ordering
3. Add custom actions (`summary`, `copy`, `by-type`, `by-company`, `active`)
4. Register routers in `aquamind/api/router.py`

**Acceptance Criteria**:
- All CRUD endpoints functional
- Custom actions working
- API follows AquaMind standards (kebab-case, pagination)

---

**Phase 3: Integration (Week 5-6)**

**Context to Provide**:
1. `financial_core_architecture.md` (Section 3: Integration Architecture)
2. `apps/scenario/models.py` for Scenario integration
3. `apps/finance/models.py` for Finance app integration

**Tasks**:
1. Add `Budget.scenario` FK (nullable)
2. Create integration views for Budget vs. Actuals
3. Test scenario linking

**Acceptance Criteria**:
- Budgets can be linked to scenarios
- Budget data appears in scenario reports
- No breaking changes to existing apps

---

**Phase 4: Testing (Week 7-8)**

**Context to Provide**:
1. `financial_core_implementation_plan.md` (Section 5: Testing Strategy)
2. Existing test patterns from `apps/scenario/tests/`

**Tasks**:
1. Write model tests (validation, constraints)
2. Write API tests (CRUD, custom actions, filtering)
3. Write integration tests (scenario linking, finance integration)

**Acceptance Criteria**:
- All tests passing
- Code coverage > 80%

---

### Frontend Implementation (Cursor.ai / Windsurf)

**Phase 1: API Client Sync (Week 1)**

**Context to Provide**:
1. `financial_core_api_specification.md` (complete)
2. `docs/DJANGO_INTEGRATION_GUIDE.md`

**Tasks**:
1. Run `npm run sync:openapi` to generate API client
2. Verify new services: `AccountGroupService`, `AccountService`, `CostCenterService`, `BudgetService`, `BudgetEntryService`

**Acceptance Criteria**:
- API client generated successfully
- TypeScript types available for all models

---

**Phase 2: Core Components (Week 2-3)**

**Context to Provide**:
1. `financial_core_ui_specification.md` (Section 3: Component Specifications)
2. Existing component patterns from `client/src/pages/ScenarioPlanningPage.tsx`

**Tasks**:
1. Create `FinancialPlanningPage.tsx` with tabbed interface
2. Create `ChartOfAccountsManager.tsx` component
3. Create `CostCenterManager.tsx` component
4. Create `MonthlyBudgetingGrid.tsx` component
5. Create `EditableCell.tsx` component

**Acceptance Criteria**:
- All components render correctly
- Tabs switch correctly
- Data fetching works (using TanStack Query)

---

**Phase 3: Forms and Modals (Week 4)**

**Context to Provide**:
1. `financial_core_ui_specification.md` (Section 6: User Workflows)
2. Existing form patterns from `client/src/components/forms/`

**Tasks**:
1. Create "Add Account Group" modal
2. Create "Add Account" modal
3. Create "Add Cost Center" modal
4. Create "Create Budget" modal
5. Create "Copy Budget" modal

**Acceptance Criteria**:
- All forms validate correctly
- API mutations work (create, update, delete)
- Success/error toasts display

---

**Phase 4: Integration and Polish (Week 5-6)**

**Context to Provide**:
1. `financial_core_ui_specification.md` (Section 7: Responsive Design)
2. `financial_planning_user_guide.md` (for UX validation)

**Tasks**:
1. Add route to sidebar navigation
2. Implement responsive design (desktop, tablet, mobile)
3. Add loading states and error handling
4. Test theme switching (light/dark mode)

**Acceptance Criteria**:
- Page accessible from sidebar
- Responsive on all screen sizes
- Theme switching works
- No console errors

---

## Key Architecture Decisions

### 1. Separate `finance_core` App

**Decision**: Create a new Django app named `finance_core` instead of extending the existing `finance` app.

**Rationale**:
- **Clear Separation of Concerns**: The existing `finance` app handles operational financial reporting (harvest facts, intercompany transactions, NAV export). The new `finance_core` app handles financial planning and budgeting.
- **No Functional Overlap**: The two apps serve completely different purposes and have different data models.
- **Integration Points**: The two apps integrate at specific points (Budget vs. Actuals reporting, Cost Center allocation) without creating tight coupling.

### 2. Hierarchical Chart of Accounts

**Decision**: Use a two-level hierarchy (AccountGroup → Account) instead of a flat list or unlimited nesting.

**Rationale**:
- **Simplicity**: Two levels are sufficient for most organizations and avoid the complexity of recursive queries.
- **Performance**: Flat queries are faster than recursive queries for large datasets.
- **Extensibility**: If unlimited nesting is needed in the future, the `AccountGroup.parent` FK can be used recursively.

### 3. Monthly Budget Entries (Not Daily)

**Decision**: Budget entries are monthly (12 entries per account/cost center per year), not daily or weekly.

**Rationale**:
- **Standard Practice**: Most organizations budget at the monthly level, not daily.
- **Data Volume**: Monthly entries keep the database size manageable (e.g., 100 accounts × 10 cost centers × 12 months = 12,000 entries per year).
- **User Experience**: A 12-column grid is manageable in a spreadsheet-like interface; a 365-column grid is not.

### 4. Scenario Integration (Optional)

**Decision**: Budgets can optionally be linked to scenarios via a nullable FK (`Budget.scenario`).

**Rationale**:
- **Flexibility**: Not all budgets are scenario-based (e.g., the "Base Budget" is not linked to a scenario).
- **What-If Analysis**: Scenario-linked budgets enable what-if analysis (e.g., "What if we expand to a new farm?").
- **Backward Compatibility**: Existing scenarios are not affected by the addition of budgets.

### 5. Auto-Save in Budgeting Grid

**Decision**: Budget entries auto-save after a 500ms debounce, not on explicit "Save" button click.

**Rationale**:
- **User Experience**: Auto-save mimics the behavior of modern spreadsheet tools (Google Sheets, Excel Online).
- **Data Loss Prevention**: Users don't lose work if they forget to click "Save".
- **Performance**: Debouncing prevents excessive API calls during rapid editing.

---

## Implementation Timeline

### Backend: 8 Weeks

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| **Phase 1: Data Model** | 2 weeks | Models, migrations, schema |
| **Phase 2: API Layer** | 2 weeks | Serializers, ViewSets, routers |
| **Phase 3: Integration** | 2 weeks | Scenario linking, Finance integration |
| **Phase 4: Testing** | 2 weeks | Unit tests, API tests, integration tests |

### Frontend: 6 Weeks

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| **Phase 1: API Client Sync** | 1 week | Generated API client, TypeScript types |
| **Phase 2: Core Components** | 2 weeks | FinancialPlanningPage, ChartOfAccountsManager, CostCenterManager, MonthlyBudgetingGrid |
| **Phase 3: Forms and Modals** | 2 weeks | Add/Edit/Delete modals, validation |
| **Phase 4: Integration and Polish** | 1 week | Routing, responsive design, theme switching |

### Total: 14 Weeks (3.5 Months)

**Note**: Backend and frontend can be developed in parallel after Phase 1 (API client sync).

---

## Testing Strategy

### Backend Testing

**Unit Tests** (pytest):
- Model validation (e.g., unique codes, account type matching)
- Model methods (e.g., `Account.get_active()`, `Budget.get_summary()`)
- Business logic (e.g., budget copying, entry aggregation)

**API Tests** (pytest + Django REST Framework):
- CRUD operations for all models
- Custom actions (`summary`, `copy`, `by-type`, etc.)
- Filtering, searching, ordering
- Pagination
- Error handling (400, 404, 500)

**Integration Tests** (pytest):
- Scenario linking (create budget → link to scenario → verify in scenario reports)
- Finance integration (create budget → compare with actuals from `finance` app)

### Frontend Testing

**Unit Tests** (Vitest + React Testing Library):
- Component rendering (e.g., `ChartOfAccountsManager` renders account list)
- User interactions (e.g., click "Add Account" → modal opens)
- Form validation (e.g., required fields, unique codes)

**Integration Tests** (Vitest):
- API integration (e.g., create account → verify API call → verify UI update)
- State management (e.g., select budget → verify grid updates)

**E2E Tests** (Playwright):
- Complete budget creation workflow (CoA setup → Cost Center setup → Budget entry)
- Budget vs. Actuals report generation
- Multi-user budget editing (concurrent edits)

---

## Troubleshooting

### Issue: Migration Conflicts with Existing `finance` App

**Symptom**: Django migration fails with "relation already exists" error.

**Solution**:
1. **Check Existing Schema**: Run `python manage.py sqlmigrate finance 0001` to see existing tables.
2. **Rename Models**: If there's a naming conflict, rename the `finance_core` models (e.g., `Account` → `FinanceAccount`).
3. **Run Migrations Separately**: Run `python manage.py migrate finance` first, then `python manage.py migrate finance_core`.

### Issue: API Client Not Generated

**Symptom**: `npm run sync:openapi` fails or doesn't generate new services.

**Solution**:
1. **Check Backend**: Ensure the backend is running and the OpenAPI schema is accessible at `/api/schema/`.
2. **Clear Cache**: Delete `client/src/api/` and re-run `npm run sync:openapi`.
3. **Manual Generation**: Use `openapi-generator-cli` to generate the client manually.

### Issue: Budget Grid Performance Degradation

**Symptom**: Budget grid becomes slow with large datasets (e.g., 1000+ rows).

**Solution**:
1. **Use Filters**: Encourage users to filter by Account Type or Cost Center to reduce the number of rows.
2. **Implement Virtualization**: Use `@tanstack/react-virtual` to render only visible rows.
3. **Paginate**: Add pagination to the budget grid (e.g., 50 rows per page).

### Issue: Auto-Save Conflicts (Concurrent Edits)

**Symptom**: Two users edit the same budget entry simultaneously, causing data loss.

**Solution**:
1. **Optimistic Locking**: Add a `version` field to `BudgetEntry` and check it on update.
2. **Last-Write-Wins**: Accept the last update (current behavior).
3. **Conflict Resolution UI**: Show a modal when a conflict is detected, allowing the user to choose which version to keep.

---

## Conclusion

This documentation package provides everything needed to implement the Financial Core feature in AquaMind. The architecture is sound, the implementation plan is detailed, and the testing strategy is comprehensive.

**Next Steps**:
1. **Copy Documentation**: Use the commands in Section 3 to copy files to your repositories.
2. **Start Backend Implementation**: Begin with Phase 1 (Data Model) in Cursor.ai.
3. **Parallel Frontend Setup**: After API client sync, start frontend implementation in parallel.
4. **Iterate and Test**: Follow the phased approach, testing after each phase.

For questions or clarifications, refer to the individual documentation files or contact the AquaMind development team.

---

**Documentation Package Version**: 1.0  
**Last Updated**: October 28, 2025  
**Author**: Manus AI
