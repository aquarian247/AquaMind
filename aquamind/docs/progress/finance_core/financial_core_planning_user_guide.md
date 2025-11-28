# Financial Planning User Guide

**AquaMind Financial Planning & Budgeting Module - User Documentation**

**Version**: 2.0  
**Date**: November 26, 2025  
**Audience**: Finance Managers, CFOs, Budget Analysts, Station Operators

---

## Table of Contents

1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Chart of Accounts Management](#chart-of-accounts-management)
4. [Cost Center Management](#cost-center-management)
5. [Monthly Budgeting](#monthly-budgeting)
6. [Ongoing Budget Management](#ongoing-budget-management)
7. [End-of-Month (EoM) Processes](#end-of-month-eom-processes)
8. [Budget Reports](#budget-reports)
9. [Integration with Scenarios](#integration-with-scenarios)
10. [Integration with NAV and External Systems](#integration-with-nav-and-external-systems)
11. [Best Practices](#best-practices)
12. [Troubleshooting](#troubleshooting)

---

## Overview

The **Financial Planning** module in AquaMind provides comprehensive tools for managing your organization's financial planning, budgeting, and month-end (EoM) processes. This module enables you to:

- **Configure Chart of Accounts (CoA)**: Define and organize your financial accounts hierarchically
- **Manage Cost Centers**: Allocate costs across operational dimensions (farms, lifecycle stages, projects/batches, stations, areas, rings)
- **Create and Edit Budgets**: Enter monthly budget data in a spreadsheet-like interface
- **Handle Cost Allocation**: Spread pooled costs (e.g., salaries, maintenance) using rules like 50% headcount + 50% biomass
- **Perform EoM Finalization**: Import NAV costs, compute valuations, generate postings, and lock periods
- **Generate Reports**: View P&L projections, budget summaries, variance analysis, movement reports, and ring valuations (e.g., for insurance)
- **Integrate with Scenarios**: Link budgets to scenario planning for what-if analysis
- **Integrate with NAV**: Import/export via CSV/API for GL reconciliation

### Key Benefits

1. **Unified Financial Planning**: Replace spreadsheets with a centralized, auditable system
2. **Scenario-Based Budgeting**: Create multiple budget versions linked to operational scenarios
3. **Real-Time Variance Tracking**: Compare budgeted vs. actual performance (integrated with existing `finance` app)
4. **Granular Cost Allocation**: Track and spread costs by batch/project, station, area, or ring using aquaculture-specific bases (e.g., biomass)
5. **EoM Efficiency**: Automate allocations, valuations, and NAV postings with period locking for compliance
6. **Collaboration**: Multiple users can work on budgets simultaneously with auto-save

---

## Getting Started

### Accessing the Financial Planning Module

1. **Log in** to AquaMind
2. **Navigate** to the sidebar menu
3. **Click** "Finance" → "Financial Planning"

### Initial Setup Checklist

Before creating your first budget, complete these setup tasks:

- [ ] **Configure Chart of Accounts** (Section 3)
- [ ] **Create Cost Centers** (Section 4, including hierarchies for stations/areas/rings)
- [ ] **Set Company and Year** (use header dropdowns)
- [ ] **Define Cost Groups** (e.g., Feed, Salaries) in CoA for allocation rules

---

## Chart of Accounts Management

The Chart of Accounts (CoA) is the foundation of your financial planning. It defines the categories for tracking revenue, expenses, assets, liabilities, and equity.

### Understanding Account Types

AquaMind supports five standard account types:

| Account Type | Purpose | Example Accounts |
|--------------|---------|------------------|
| **ASSET** | Resources owned by the company | Cash, Inventory, Equipment |
| **LIABILITY** | Obligations owed to others | Loans, Accounts Payable |
| **EQUITY** | Owner's interest in the company | Retained Earnings, Capital |
| **REVENUE** | Income from operations | Harvest Sales, Intercompany Revenue |
| **EXPENSE** | Costs of operations | Feed, Labor, Depreciation |

### Cost Groups for Allocation

Cost Groups are predefined categories (e.g., Feed, Salaries) used for EoM pooling and spreading. Each has a posting mode (Direct or Allocated) and default allocation rule (e.g., 50% headcount + 50% biomass).

**Steps to Configure**:
1. **Navigate** to "Chart of Accounts" tab
2. **Select** an EXPENSE Account Group
3. **Add Cost Group**: Set mode/rule (e.g., Allocated, 50/50 biomass)
4. **Save**: Rules apply automatically in EoM workflows

### Creating Account Groups

Account groups provide hierarchical organization for your accounts.

**Example Hierarchy**:
```
OPEX (Operating Expenses)
├─ FEED (Feed Costs)
│  ├─ 5100 Smolt Feed
│  └─ 5110 Parr Feed
└─ LABOR (Labor Costs)
   └─ 5200 Farm Labor
```

**Steps**:
1. **Navigate** to "Chart of Accounts" tab
2. **Click** "+ Add Account Group"
3. **Fill Form**:
   - **Code**: Short identifier (e.g., "OPEX")
   - **Name**: Descriptive name (e.g., "Operating Expenses")
   - **Account Type**: Select from dropdown (e.g., "EXPENSE")
   - **Parent Group**: (Optional) Select parent for hierarchical nesting
   - **Display Order**: Number for sorting (lower numbers first)
   - **Cost Group Rules**: (If EXPENSE) Set posting mode and allocation rule
4. **Submit** → Group created; add child accounts as needed

---

## Cost Center Management

Cost Centers enable cost allocation across operational dimensions, supporting hierarchies like station > area > ring/container for granular spreading.

### Understanding Cost Centers

Cost Centers represent units like stations (Operating Units), areas, or rings (projects/batches). They support hierarchies and link to biology data (e.g., biomass for allocation).

| Level | Example | Use Case |
|-------|---------|----------|
| **Station** | Freshwater Hall 1 | Pool costs (e.g., energy) |
| **Area** | North Area (20 rings) | Intermediate allocation |
| **Ring/Container** | Ring 001 (100k smolt) | Final granularity for valuation |

### Creating Cost Centers

**Steps**:
1. **Navigate** to "Cost Centers" tab
2. **Click** "+ Add Cost Center"
3. **Fill Form**:
   - **Code**: e.g., "STATION-01"
   - **Name**: e.g., "Main Freshwater Station"
   - **Company**: Select subsidiary (e.g., Freshwater)
   - **Parent Center**: For hierarchy (e.g., area under station)
   - **Biology Link**: Link to Batch/Project for biomass/headcount
   - **Is Active**: Default true
4. **Submit** → Center created; auto-detect new batches for child centers

**Advanced**: For rings/projects, link to Batch model for auto-biomass pulls.

---

## Monthly Budgeting

Create budgets for planning, with monthly entries by Account and Cost Center.

**Steps**:
1. **Navigate** to "Budgeting" tab
2. **Click** "+ Create Budget"
3. **Fill Form**:
   - Name: e.g., "2025 Smolt Base Budget"
   - Year: 2025
   - Company: Freshwater
   - Scenario: (Optional)
   - Description: e.g., "Smolt EoM with 50/50 allocation"
4. **Submit** → Budget created
5. **Add Rows**: Select Account (e.g., Feed), Cost Center (e.g., Ring 001); enter monthly amounts
6. **Auto-Save** → Entries saved; totals update live

---

## Ongoing Budget Management

Once created, manage budgets for day-to-day updates.

### Handling One-Time Costs or Ad-Hoc Expenses
**Steps**:
1. **Select** active budget
2. **Click** "+ Add Row"
3. **Select** Account (e.g., "Maintenance - One-Time") and Cost Center
4. **Enter** amount in relevant month(s)
5. **Add Notes**: e.g., "Emergency pump replacement"
6. **Save**: Auto-save; impact on totals visible

**Best Practice**: Use dedicated Cost Group for one-time items.

### Distributing or Spreading Expenses
For costs spanning centers (e.g., station-level salaries to rings):
**Steps**:
1. **Add Rows** for each child Cost Center
2. **Apportion**: Enter proportions (e.g., 40% Ring 001 based on biomass)
3. **Verify**: Sum matches original; use preview tool
4. **Save**: Auto-applies rule (e.g., 50/50)

**Advanced**: Use "Allocate" button for rule-based spreading (e.g., 50% headcount + 50% biomass from Batch links).

### Daily Monitoring and Collaboration
- **Live Totals**: Grid shows sums/variances
- **Collaborate**: Real-time edits with highlights
- **Alerts**: Notifications for overruns (EoM preview)

---

## End-of-Month (EoM) Processes

EoM finalizes biology and finance for Smolt (extendable to Sea).

### Preparing for EoM
1. **Verify Feed/Inventory**: Confirm receipts; operator sign-off
2. **Detect New Projects**: Auto-list batches without Cost Centers; create via one-click

### Importing NAV Costs
**Steps**:
1. **Upload CSV**: Columns: CostGroup, OperatingUnit, Amount
2. **Validate**: Enforce Cost Groups (e.g., Feed, Salaries); preview totals
3. **Import**: Idempotent; creates BudgetEntries

### Cost Allocation and Valuation
**Steps**:
1. **Run Allocation**: Select budget; apply rules (e.g., 50/50 for pooled groups; direct for Eggs)
2. **Preview**: Table of distributions (e.g., Salaries: Ring 001 = 20k DKK)
3. **Approve**: Generate valuation roll-forward (Opening + Eggs/Allocations - Transfers/Mortality = Closing at WAC)
4. **Post**: Export to NAV (Dr 8310 / Cr 2211; dimensions: Operating Unit, PSG=Smolt)

**Transfers to Sea**: Biology-only (counts/kg/weight); optional pricing toggle (default off; no value carry).

### Mortality Expensing
**Steps**:
1. **Review**: View container mortalities from Batch/Health
2. **Trigger P&L**: Manual button to expense audited amounts (posts to 2211)
3. **Save**: Updates valuation; audit trail

### Period Locking
**Steps**:
1. **Finalize**: After reports, click "Lock Period" (Company + Operating Unit + Month)
2. **Confirm**: Blocks edits; generates audit log
3. **Reopen**: Admin-only with reason/versioning

---

## Budget Reports

### Budget vs. Actuals Report
Compares budgets to actuals (from `finance` app/NAV).

**Steps**:
1. **Select** budget
2. **Click** "View vs. Actuals"
3. **EoM Workflow**: Import actuals; analyze variances; drill to rings

### Movement Reports
Opening/Change/Closing for cost + biology.

**Steps**:
1. **Select** period/Cost Center
2. **Generate**: Includes WAC valuation for insurance

**Planned**: Ring-specific (biomass-based).

---

## Integration with Scenarios

Budgets link to Scenarios for what-if (e.g., biomass changes affecting allocation).

**Steps**:
1. **Edit** budget; select Scenario
2. **Save**: Projections update (e.g., EoM valuation under expansion)

### Comparing Budgets Across Scenarios
**Steps**:
1. **Navigate** to "Scenario Planning"
2. **Select** scenario
3. **View** "Financial Impact": Linked budget's EoM (allocations, valuation)

---

## Integration with NAV and External Systems

- **CSV Import/Export**: For costs/postings; validate schemas
- **API (Future)**: Bidirectional for real-time (e.g., push allocations)
- **Biology Sync**: Pulls from Batch for headcount/biomass

---

## Best Practices

### 1. Start with a Template
- Copy last year's; adjust for changes (e.g., new rings)

### 2. Use Scenarios for What-If
- Link budgets; test allocation impacts

### 3. Review and Approve
- Collaborative edits; activate post-approval

### 4. Monitor Variance
- Monthly reviews; revise for overruns

### 5. EoM Close Processes
- Lock after finalization; export to NAV promptly
- Use 50/50 defaults; document overrides

---

## Troubleshooting

### Issue: Cannot Delete an Account
**Cause**: Existing entries.

**Solution**: Deactivate; or delete entries first.

### Issue: Budget Grid Too Large
**Solution**: Filter by Cost Group/Center; split budgets.

### Issue: Auto-Save Not Working
**Solution**: Check network; refresh; contact support.

### Issue: Cannot Activate Budget
**Solution**: Deactivate existing; retry.

### Issue: Allocation Preview Errors
**Cause**: Missing biology (biomass/headcount).

**Solution**: Sync Batch data; use fallbacks (e.g., equal split).

### Issue: Unable to Edit Locked Period
**Solution**: Admin reopen with reason; creates version.

---

## Conclusion

The Financial Planning module streamlines budgeting and EoM for Smolt/Sea. Follow workflows for accuracy/compliance. For details, see **Financial Core Implementation Plan** and **API Specification**.