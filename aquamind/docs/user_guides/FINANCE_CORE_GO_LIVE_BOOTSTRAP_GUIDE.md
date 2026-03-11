# AquaMind Finance Core Go-Live Bootstrap Guide

**Version**: 1.0  
**Last Updated**: March 11, 2026  
**Audience**: Finance Leads, Finance Managers, and Administrators preparing first-time live use of Finance Core

---

## Table of Contents

1. [Purpose](#purpose)
2. [Key Principle: No Historical FishTalk Finance Migration](#key-principle-no-historical-fishtalk-finance-migration)
3. [What Must Already Exist In AquaMind](#what-must-already-exist-in-aquamind)
4. [Choose Your Baseline Period](#choose-your-baseline-period)
5. [Bootstrap Roles And Responsibilities](#bootstrap-roles-and-responsibilities)
6. [Go-Live Bootstrap Procedure](#go-live-bootstrap-procedure)
7. [What To Do For Existing Active Batches](#what-to-do-for-existing-active-batches)
8. [First Live Month After Cutover](#first-live-month-after-cutover)
9. [What To Keep From FishTalk And NAV](#what-to-keep-from-fishtalk-and-nav)
10. [Troubleshooting](#troubleshooting)
11. [Sign-Off Checklist](#sign-off-checklist)

---

## Purpose

This guide explains how to bootstrap AquaMind Finance Core for live use without migrating historical FishTalk Finance history.

It is the **one-time go-live setup procedure** for:

- companies
- operating units
- existing active batches already present in AquaMind
- the first baseline month-close period

After this bootstrap is complete, monthly finance work should continue using the normal process described in:

- `aquamind/docs/user_guides/FINANCE_CORE_USER_GUIDE.md`

---

## Key Principle: No Historical FishTalk Finance Migration

Finance Core does **not** require a historical migration of FishTalk Finance costing history.

This is intentional.

### Why

- AquaMind replaces FishTalk Finance as the costing and month-close layer.
- NAV remains the accounting system of record.
- The biological and operational migration is already complex enough without replaying old costing logic.
- Reconstructing old finance overrides, valuation assumptions, and locked historical periods would add audit and mapping risk.

### Practical Result

Users do **not** backfill years of old FishTalk Finance records into AquaMind.

Instead, users:

1. prepare Finance Core configuration
2. verify cost-project coverage for active batches
3. upload NAV cost CSV data for the baseline period
4. create the first valuation baseline in AquaMind
5. lock that baseline period

From that point onward, AquaMind Finance Core becomes the live operating process.

---

## What Must Already Exist In AquaMind

Before finance bootstrap begins, AquaMind must already contain the relevant operational truth.

### Required

- migrated or manually created biology/operations data for active batches
- companies and sites resolvable through the existing finance dimensions
- active users with `Finance` or `Admin` access
- AquaMind code with Finance Core enabled and migrations applied

### Expected Operational Data

- active batches
- batch assignments in containers
- operating units/sites
- any biology needed for opening period valuation

### Not Required

- historical FishTalk Finance tables
- historical FishTalk valuation runs
- historical FishTalk budgets
- historical FishTalk delta journals

---

## Choose Your Baseline Period

The recommended baseline is:

- **the month before go-live**

Example:

- if live monthly operation in AquaMind starts in **April 2026**
- then bootstrap and lock **March 2026**

This gives you:

- one clean opening valuation baseline in AquaMind
- a stable starting point for the first live month

Do not try to start with a partially closed current month if you can avoid it.

---

## Bootstrap Roles And Responsibilities

### Finance Team

Finance users are responsible for:

- reviewing company and operating-unit context
- configuring account groups and accounts
- reviewing cost centers and allocation rules
- creating the first budget
- uploading baseline NAV CSV files
- running allocation preview and valuation
- locking the baseline period

### Administrator

An administrator is responsible for:

- reopening a locked period if a correction is required
- assisting with any missing access or environment issues

### Implementation Support / Technical Support

Technical support is only needed if:

- active legacy batches are missing finance-core project links
- finance dimensions are incomplete
- the environment has not been migrated/applied correctly

---

## Go-Live Bootstrap Procedure

Follow these steps in order.

### Step 1. Open Finance Core

1. Sign in to AquaMind.
2. Click **Financial Planning** in the sidebar.
3. Confirm the header selections:
   - **Company**
   - **Fiscal Year**
   - **Active Budget**

If the budget does not exist yet, you will create it in Step 5.

### Step 2. Confirm Company And Operating Unit Coverage

Go to **EoM Wizard** and verify the correct:

- company
- operating unit
- month

Also confirm the **Pre-Close Checklist** appears.

If the company or operating unit you need is not available, stop and resolve that before continuing.

### Step 3. Configure Chart Of Accounts

Go to **Chart of Accounts**.

Create or verify:

- required **Account Groups**
- required **Accounts**

At minimum, make sure imported cost groups from the baseline NAV CSV will map cleanly.

Typical actions:

1. Create an account group such as `OPEX`
2. Set the **Import Cost Group**
3. Create the corresponding leaf accounts

You should not upload baseline costs until these mappings exist.

### Step 4. Verify Cost Centers And Allocation Rules

Go to **Cost Centers**.

Verify:

- project cost centers exist for the active batches you plan to close
- operating-unit/site cost centers are sensible
- allocation rules are configured as needed

If you want to override the default 50/50 weighting, create the needed **Allocation Rule** now.

### Step 5. Create The First Budget

Go to **Budgeting**.

1. In **Budget Controls**, create the annual budget for the target fiscal year.
2. Select it as the active budget.
3. Use **Add Budget Row** plus the budget matrix to enter the minimum monthly planning rows you need.
4. Click **Save Grid Changes**.

You do not need a perfect long-range budget to bootstrap Finance Core, but you do need a coherent budget shell for the target company/year.

### Step 6. Upload The Baseline NAV CSV

Go to **EoM Wizard**.

1. Select the baseline month.
2. Upload the NAV CSV using **Upload NAV CSV**.
3. Confirm the **Recent Imports** section updates.
4. Confirm the **Pre-Close Checklist** moves `Import` to `COMPLETE`.

The uploaded CSV should follow the expected format:

- `CostGroup`
- `OperatingUnit`
- `Amount`

### Step 7. Review Pre-Close Checklist

Before any close action, review:

- `Import`
- `Biology`
- `Cost Projects`
- `Allocation`
- `Valuation`
- `NAV Preview`
- `Lock`

Interpretation:

- `COMPLETE`: ready or already done
- `WARNING`: usable, but review carefully
- `BLOCKED`: stop and resolve before continuing
- `PENDING`: not yet performed
- `READY`: next step can proceed

### Step 8. Run Allocation Preview

Click **Allocation Preview**.

Expected result:

- a `PREVIEW` run is created
- the success panel updates
- **Valuation Runs** shows a new preview version

Typical visible message:

- `Allocation preview ready`

Review:

- allocation total
- biology source row count
- run version

### Step 9. Run Valuation

If needed, enter an **Impairment %** first.

Then click **Run Valuation**.

Expected result:

- an `APPROVED` run is created
- the success panel updates
- `Valuation` becomes complete
- `NAV Preview` becomes complete
- `Movement Report`, `Ring Valuation`, and `NAV Export Preview` populate

Typical visible message:

- `Valuation approved`

### Step 10. Review The Baseline Reports

Still in **EoM Wizard**:

1. Use **Report Run** to select the correct approved run.
2. Review **Valuation Runs**.
3. Review **Movement Report**.
4. Review **Ring Valuation**.
5. Review **NAV Export Preview**.

You are looking for:

- a sensible closing value
- a sensible delta
- the expected NAV accounts and balancing lines
- correct operating-unit context

### Step 11. Lock The Baseline Period

1. Enter a clear **Lock Reason**.
2. Click **Lock Period**.
3. Confirm:
   - lock state changes to `LOCKED`
   - a lock version appears
   - **Period Locks** updates

Typical visible message:

- `Period locked`

This locked baseline becomes the opening point for live Finance Core operation going forward.

### Step 12. Repeat For Other Sites / Companies

If you operate multiple companies or operating units:

1. change the header company selection
2. select the next operating unit
3. repeat the same baseline procedure

Bootstrap should be completed for each live site/company context that Finance Core will close.

---

## What To Do For Existing Active Batches

This is the most important practical topic.

### Expected Outcome

Existing active AquaMind batches should end up with valid finance-core project cost centers so they can participate in allocation and valuation.

### What Finance Users Should Verify

In **Cost Centers** and **Pre-Close Checklist**, verify:

- the active batches are represented by project cost centers
- no finance close is blocked by missing cost-project linkage

### If Cost Projects Are Missing

If the checklist shows missing cost projects for already-existing legacy batches:

- do **not** continue the close
- resolve project linkage first

This is an implementation/bootstrap issue, not a reason to migrate historical FishTalk Finance tables.

In other words:

- you still do **not** migrate historical FishTalk Finance history
- you **do** make sure the currently active AquaMind batches have finance-core project coverage before the first close

---

## First Live Month After Cutover

Once the baseline month is locked:

1. move to the first live operating month
2. continue using the normal monthly workflow from `FINANCE_CORE_USER_GUIDE.md`

That means:

- upload current NAV costs
- run allocation preview
- run valuation
- review reports
- lock the period

At that point, AquaMind Finance Core is your active costing and close layer.

---

## What To Keep From FishTalk And NAV

### Keep FishTalk Finance As Read-Only Reference

During transition, FishTalk Finance can remain:

- read-only
- archive/reference only

### Keep NAV As The Accounting System Of Record

NAV remains:

- the accounting system of record
- the source for imported baseline actual cost files

Finance Core becomes:

- the planning and costing workspace
- the allocation and valuation layer
- the operational month-close control surface

---

## Troubleshooting

### Problem: Import Is COMPLETE But Allocation Is BLOCKED

Likely causes:

- no biology rows found
- missing cost-project links
- period already locked

Action:

1. review the `Biology` and `Cost Projects` checklist items
2. verify operating unit and month
3. resolve missing project coverage before proceeding

### Problem: Valuation Runs But Reports Look Empty

Action:

1. check **Report Run**
2. make sure you selected the approved run, not an older preview

### Problem: Period Was Locked Too Early

Action:

1. have an administrator reopen the period
2. provide a clear reopen reason
3. re-run the necessary close steps

### Problem: A Finance User Cannot Reopen

This is expected.

Only administrators can reopen a locked period.

---

## Sign-Off Checklist

Before declaring Finance Core live for a company/site, confirm all of the following:

- account groups and accounts are configured
- cost centers are present for active close-relevant batches
- the annual budget exists
- baseline NAV CSV imported successfully
- pre-close checklist has no blocking items
- allocation preview created successfully
- approved valuation created successfully
- reports reviewed
- baseline period locked successfully
- finance and admin users understand who can reopen a period
- FishTalk Finance is treated as archive/reference only

---

## Final Note

The go-live objective is **not** to recreate FishTalk Finance history inside AquaMind.

The objective is:

1. establish a clean baseline month in AquaMind
2. verify current active batches are finance-ready
3. lock that baseline
4. run all future month-close work in AquaMind Finance Core

That is the cleanest, safest, and lowest-risk cutover path.
