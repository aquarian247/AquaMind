# AquaMind Finance Core User Guide

**Version**: 1.0  
**Last Updated**: March 11, 2026  
**Audience**: Finance users, Finance Managers, and Administrators

---

## Table of Contents

1. [Overview](#overview)
2. [Who Can Use Finance Core](#who-can-use-finance-core)
3. [Core Concepts](#core-concepts)
4. [How To Open Finance Core](#how-to-open-finance-core)
5. [Page Layout](#page-layout)
6. [Chart Of Accounts](#chart-of-accounts)
7. [Cost Centers](#cost-centers)
8. [Budgeting](#budgeting)
9. [End-Of-Month Wizard](#end-of-month-wizard)
10. [Reports And Run Selection](#reports-and-run-selection)
11. [Locking And Reopening Periods](#locking-and-reopening-periods)
12. [Success Messages And Status Indicators](#success-messages-and-status-indicators)
13. [Recommended Monthly Workflow](#recommended-monthly-workflow)
14. [Best Practices](#best-practices)
15. [Troubleshooting](#troubleshooting)
16. [FAQ](#faq)

---

## Overview

Finance Core is AquaMind's financial planning, budgeting, and month-close workspace.

It brings together four connected areas in one page:

- **Chart of Accounts** for account groups and accounts
- **Cost Centers** for project and operating-unit allocation targets
- **Budgeting** for stable month-by-month budget entry
- **EoM Wizard** for end-of-month cost import, allocation, valuation, NAV preview, and period locking

Finance Core is intentionally separate from AquaMind's older operational `finance` domain.

The existing operational finance features still handle:

- intercompany transfer transactions
- harvest facts
- operational NAV export flows tied to transfer and harvest workflows

Finance Core handles:

- budgeting
- planning
- cost allocation
- valuation runs
- month-close workflow control

---

## Who Can Use Finance Core

### Finance Users

Finance users can:

- open the `Financial Planning` page
- maintain chart of accounts and cost centers
- edit budgets
- upload period cost imports
- run allocation previews
- run approved valuation closes
- lock a period

Finance users cannot:

- reopen a locked period

### Administrators

Administrators can do everything finance users can do, plus:

- reopen a locked period
- provide the required reopen reason

---

## Core Concepts

### Company

A **Company** is the finance company dimension used for budgeting and close reporting.

### Operating Unit

An **Operating Unit** is the site-level finance dimension used for allocation, valuation, and locking.

### Cost Group

A **Cost Group** is the import-facing grouping code used in NAV cost files.

### Account Group

An **Account Group** maps AquaMind planning categories to imported cost groups.

### Cost Center

A **Cost Center** is where cost is assigned. In practice this is usually:

- a site cost center
- a project cost center linked to a batch

### Budget

A **Budget** is the annual planning container for a company and fiscal year.

### Budget Entry

A **Budget Entry** is a monthly amount for:

- one account
- one cost center
- one month

### Allocation Preview

An **Allocation Preview** creates a `PREVIEW` valuation run that shows how imported period costs will be distributed across cost centers.

### Valuation Run

A **Valuation Run** is the immutable record of a month-close calculation.

Common statuses:

- `PREVIEW`
- `APPROVED`

### Period Lock

A **Period Lock** prevents further biology and finance-core edits for a specific company, operating unit, year, and month.

Every lock/reopen cycle increments a version number.

---

## How To Open Finance Core

1. Sign in to AquaMind.
2. In the sidebar, click **Financial Planning**.
3. The page opens at `/finance/planning`.

On first load, AquaMind usually auto-selects:

- the first available company
- the first available operating unit for that company
- the first available budget for the selected fiscal year

Always confirm those selections before performing close actions.

---

## Page Layout

The page has:

- a header with **Company**, **Fiscal Year**, and **Active Budget**
- four tabs:
  - **Chart of Accounts**
  - **Cost Centers**
  - **Budgeting**
  - **EoM Wizard**

The **Active Budget** badge shows the currently selected budget and version, for example:

`FC-DEMO Budget 2026 v1`

---

## Chart Of Accounts

The **Chart of Accounts** tab has two create forms and two tables.

### Add Account Group

Use **Add Account Group** to define high-level groupings for imported and planned costs.

Fields:

- `Code`
- `Name`
- `Account Type`
- `Import Cost Group`

Typical use:

- create a group such as `OPEX`
- map it to the import-facing cost group used in CSV uploads

### Add Account

Use **Add Account** to create leaf accounts under a group.

Fields:

- `Code`
- `Name`
- `Account Type`
- `Group`

### What You See

The tab also shows:

- an **Account Groups** table
- an **Accounts** table

These tables are the current source of truth for configured planning accounts.

---

## Cost Centers

The **Cost Centers** tab controls where costs are assigned.

### Add Cost Center

Use **Add Cost Center** to create:

- site cost centers
- project cost centers
- department cost centers
- other custom centers

Fields:

- `Code`
- `Name`
- `Operating Unit`
- `Type`

### Add Allocation Rule

Use **Add Allocation Rule** to override the default allocation behavior.

Fields:

- `Rule Name`
- `Account Group`
- `Cost Center Override`
- `Headcount Weight`
- `Biomass Weight`
- `Effective From`

Example:

- `Headcount Weight = 0.70`
- `Biomass Weight = 0.30`

This makes the rule favor fish count more than biomass for the selected scope.

### What You See

The tab also shows:

- **Configured Cost Centers**
- **Allocation Rules**

Project cost centers linked to active batches appear here and are used during valuation.

---

## Budgeting

The **Budgeting** tab has two parts:

- **Budget Controls**
- **Budget Grid**

### Budget Controls

Use this panel to:

- create a new budget
- choose the active budget
- copy a budget forward to a new fiscal year

Main controls:

- `Budget Name`
- `Status`
- `Create Budget`
- `Active Budget`
- `Copy To Year`
- `Copy Budget Forward`

### Budget Grid

The **Budget Grid** is the primary monthly planning workspace.

It shows:

- one row per account/cost-center combination
- month columns from `Jan` to `Dec`
- inline numeric month inputs
- a `Saved` or `Unsaved changes` badge

On smaller screens, the budget grid scrolls horizontally inside the grid area. The rest of the page should remain stable while you move across months.

### Add Budget Row

To add a new row:

1. Choose an **Account**.
2. Choose a **Cost Center**.
3. Click **Add Row**.

### Edit Monthly Values

To enter or change budget values:

1. Click the month cell for the target row.
2. Type the amount.
3. Repeat across months as needed.
4. Click **Save Grid Changes**.

### Remove A Budget Row

To remove a row:

1. Find the account/cost-center row.
2. Click **Remove**.
3. Click **Save Grid Changes**.

If the row already had saved month values, AquaMind deletes those saved entries during the next save.

### Reset Changes

If you want to discard unsaved edits:

1. Click **Reset**.
2. The grid returns to the last saved state.

### Save Behavior

When you click **Save Grid Changes**:

- changed numeric cells are upserted
- blanked cells with existing entries are deleted
- the grid returns to `Saved` once complete

### Grid Tips

- Use the month columns for fast side-by-side comparison
- Create the needed account/cost-center rows first
- Save after a logical batch of edits, not after every single cell
- Treat this as a stable planning matrix, not a full Excel replacement

---

## End-Of-Month Wizard

The **EoM Wizard** is the operational close workspace for the selected:

- company
- operating unit
- fiscal year
- month

It contains:

- a **Pre-Close Checklist**
- a **Last Action Result** panel after actions run
- quick status cards
- a **Report Run** selector
- action buttons
- close result tables

### Inputs At The Top

Before closing, confirm:

- `Budget`
- `Operating Unit`
- `Month`
- optional `Impairment %`

### Quick Status Cards

The wizard shows cards for:

- **Biology Source**
- **Latest Import**
- **Selected Run**
- **Lock State**

These tell you:

- whether biology came from `daily_state` or `assignment_fallback`
- when the latest import was loaded
- which run the lower reports are using
- whether the period is open or locked

### Pre-Close Checklist

The checklist is the best indicator of readiness.

Common items:

- `Import`
- `Biology`
- `Cost Projects`
- `Allocation`
- `Valuation`
- `NAV Preview`
- `Lock`

Possible statuses:

- `COMPLETE`
- `WARNING`
- `BLOCKED`
- `PENDING`
- `READY`

### Why Biology Can Show WARNING

A `WARNING` on **Biology** usually means the period is using `assignment_fallback` instead of a cleaner daily-state snapshot.

This does **not** automatically mean the close is wrong.

In feature-dev or sparse-data environments, this can be expected. In production usage, finance should still review whether the biology source is acceptable for the period being closed.

---

## Reports And Run Selection

### Report Run Selector

The **Report Run** dropdown controls which run is used for:

- ring valuation
- NAV export preview

The dropdown can contain both:

- `PREVIEW` runs
- `APPROVED` runs

Recommended practice:

- use `PREVIEW` runs for checking allocation behavior
- use `APPROVED` runs for final valuation and NAV review

### Valuation Runs Table

The **Valuation Runs** table shows:

- run version, for example `v4`
- status
- period
- timestamp
- closing value

### Movement Report

The **Movement Report** shows site-level movement of:

- allocated value
- closing value

### Ring Valuation

The **Ring Valuation** section shows:

- cost center
- biomass
- WAC per kg
- estimated value

### NAV Export Preview

The **NAV Export Preview** section shows the balanced journal lines generated from the selected approved run.

Example values you may see:

- `DEBIT`
- `CREDIT`
- account `8313`
- balancing account `2211`
- `SMOLT`
- period delta amount such as `3400.00`

---

## Locking And Reopening Periods

### Lock Period

To lock a period:

1. Complete or review the valuation workflow.
2. Enter a **Lock Reason**.
3. Click **Lock Period**.

After a successful lock:

- the lock state changes to `LOCKED`
- the lock version is shown
- the **Period Locks** table updates
- edit actions for that period are blocked

### Reopen Period

Only **Administrators** can reopen a locked period.

To reopen:

1. Sign in as an admin user.
2. Go to **Financial Planning** → **EoM Wizard**.
3. Enter a **Reopen Period** reason.
4. Click **Reopen Period**.

After a successful reopen:

- the lock state changes back to `OPEN`
- the version increments
- the **Period Locks** table shows `REOPENED`

### Important Permission Rule

Finance users can lock a period, but cannot reopen it.

If a finance user closes a month and later needs to revise it, an administrator must reopen the period.

---

## Success Messages And Status Indicators

After major actions, AquaMind shows a persistent result panel near the top of the wizard.

Examples:

### Allocation Preview

Title:

`Allocation preview ready`

Typical details:

- `Preview run v5 created for 2026-03`
- `Biology source rows: 2`
- `Allocated total 2100.00`

### Run Valuation

Title:

`Valuation approved`

Typical details:

- `Approved run v6 completed for 2026-03`
- `Closing value 5850.00`
- `Delta 3400.00`

### Lock Period

Title:

`Period locked`

Typical details:

- `FC-DEMO Station locked for 2026-03`
- `Version 2`
- your lock reason

### Reopen Period

Title:

`Period reopened`

Typical details:

- `FC-DEMO Station reopened at version 3`
- your reopen reason

### While Actions Run

Buttons disable while the request is processing. Do not click repeatedly. Wait for the success or error result panel to update.

---

## Recommended Monthly Workflow

Use this order every month.

### Step 1: Open The Correct Context

1. Open **Financial Planning**.
2. Confirm the correct **Company**.
3. Confirm the correct **Fiscal Year**.
4. Confirm the correct **Active Budget**.
5. In **EoM Wizard**, confirm the correct **Operating Unit** and **Month**.

### Step 2: Review Pre-Close Checklist

1. Check **Import** status.
2. Check **Biology** status.
3. Check **Cost Projects** status.
4. Make sure nothing is `BLOCKED`.

### Step 3: Upload NAV Cost File

1. Choose the CSV file.
2. Click **Upload NAV CSV**.
3. Confirm the success panel and **Recent Imports** table update.

### Step 4: Generate Allocation Preview

1. Click **Allocation Preview**.
2. Review the success panel.
3. Confirm a new `PREVIEW` run appears in **Valuation Runs**.

### Step 5: Run Valuation

1. Enter an impairment percentage if needed.
2. Click **Run Valuation**.
3. Confirm the success panel.
4. Confirm a new `APPROVED` run appears.

### Step 6: Review Reports

1. Use **Report Run** to select the correct run.
2. Review **Movement Report**.
3. Review **Ring Valuation**.
4. Review **NAV Export Preview**.

### Step 7: Lock The Period

1. Enter a lock reason.
2. Click **Lock Period**.
3. Confirm the lock state changes to `LOCKED`.

### Step 8: Reopen Only If Necessary

If changes are required after locking:

1. Ask an administrator to sign in.
2. Enter the reopen reason.
3. Use **Reopen Period**.
4. Re-run the needed close steps.

---

## Best Practices

- Always confirm company, site, month, and budget before closing.
- Treat `APPROVED` runs as your authoritative close candidates.
- Use `PREVIEW` runs to compare alternative allocation or impairment scenarios.
- Do not lock a period until the NAV preview looks correct.
- Always provide meaningful lock and reopen reasons for auditability.
- Save budgeting grid changes in logical batches.
- If biology shows `assignment_fallback`, review whether that is acceptable for the close.
- Prefer reopening only when absolutely necessary.

---

## Troubleshooting

### Problem: Allocation Preview Is Disabled

Possible causes:

- no budget selected
- no operating unit selected
- pre-close checklist says allocation is blocked
- period is already locked

What to do:

1. Confirm budget and site are selected.
2. Review the **Pre-Close Checklist**.
3. Resolve missing imports or missing project links first.

### Problem: Run Valuation Is Disabled

Possible causes:

- allocation preview has not been generated yet
- period is locked
- required context is missing

What to do:

1. Run **Allocation Preview** first.
2. Confirm the checklist shows allocation complete.

### Problem: Lock Period Is Disabled

Possible causes:

- valuation/NAV review is not ready
- period is already locked

What to do:

1. Review **Valuation Runs** and **NAV Export Preview**.
2. Confirm the checklist shows lock readiness.

### Problem: I Cannot See Reopen Period

Cause:

- you are signed in as a finance user, not an administrator

What to do:

1. Ask an administrator to reopen the period
2. Provide the business reason for reopening

### Problem: NAV Export Preview Is Empty

Possible causes:

- no approved run selected
- the selected run is only a preview
- valuation has not been completed for that month/site

What to do:

1. Use **Report Run** to select an `APPROVED` run.
2. Re-run valuation if needed.

### Problem: Budget Grid Shows Unsaved Changes

What it means:

- you edited cells but have not saved them yet

What to do:

1. Click **Save Grid Changes** to persist
2. Or click **Reset** to discard edits

---

## FAQ

### Do I need to upload a NAV CSV every time?

Yes, if you want current imported period costs for that close cycle.

Uploading a new file for the same period replaces the imported lines for that period/site context.

### What is the difference between PREVIEW and APPROVED?

- `PREVIEW` shows a draft allocation/valuation checkpoint
- `APPROVED` is the finalized valuation result used for closing review

### Why does the lock version change?

Each lock/reopen cycle increments the version to preserve an audit trail of period state changes.

### Can finance users reopen periods?

No. Reopening is admin-only.

### Can I switch between valuation runs?

Yes. Use **Report Run** to decide which run drives ring valuation and NAV preview.

### Why does Biology sometimes show WARNING?

Because AquaMind may be using a fallback source rather than a richer daily-state snapshot. This is especially common in sparse or development datasets.

---

## Final Note

Finance Core is designed to be used as one connected workflow, not as four isolated tabs.

The most reliable process is:

1. configure accounts and cost centers
2. maintain budgets
3. review the pre-close checklist
4. import actual period costs
5. preview allocation
6. run valuation
7. review reports
8. lock the period

Use reopening sparingly, and always document why.
