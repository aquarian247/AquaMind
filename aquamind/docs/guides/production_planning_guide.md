# Production Planning Guide for AquaMind

## Overview

The Production Planning module in AquaMind provides comprehensive tools for planning, tracking, and analyzing operational activities across fish batch lifecycles. It enables proactive management of 50-60+ concurrent batches through scenario-based planning, template automation, and variance analysis.

**Key Capabilities:**
- Plan operational activities (vaccinations, treatments, transfers, sampling, etc.)
- Automate activity generation using configurable templates
- Track planned vs. actual execution with variance analysis
- Integrate with Transfer Workflows for complex multi-day operations
- Monitor overdue activities and completion rates

---

## Core Concepts

### Scenarios

A **Scenario** represents a planning context that groups related activities together. Scenarios enable:
- What-if analysis by comparing different operational strategies
- Batch-level planning within a consistent framework
- Activity isolation (deleting a scenario removes all its activities)

Every planned activity belongs to exactly one scenario. Multiple scenarios can exist for the same batch, allowing comparison of different approaches (e.g., "Aggressive Treatment Plan" vs. "Conservative Plan").

### Planned Activities

A **Planned Activity** represents a single operational task scheduled for a specific batch. Activities have:

| Field | Description |
|-------|-------------|
| Scenario | The planning context (required) |
| Batch | The fish batch this activity targets (required) |
| Activity Type | Category of operation (see table below) |
| Due Date | When the activity should be executed |
| Status | Current state (PENDING, IN_PROGRESS, COMPLETED, CANCELLED) |
| Container | Optional target container |
| Notes | Operational context and instructions |

**Activity Types:**

| Type | Description | Example |
|------|-------------|---------|
| VACCINATION | Scheduled immunization | "First vaccination - IHN" |
| TREATMENT | Health interventions | "De-licing treatment" |
| CULL | Removal of fish | "Remove underperformers" |
| HARVEST | Planned harvest | "Market harvest - 4.5kg target" |
| FEED_CHANGE | Diet transitions | "Switch to grower feed" |
| TRANSFER | Container movements | "Move to sea cages" |
| MAINTENANCE | Infrastructure upkeep | "Tank cleaning" |
| SAMPLING | Growth/health checks | "Weekly growth sampling" |
| OTHER | Custom activities | "Regulatory inspection" |

### Activity Statuses

Activities progress through a defined lifecycle:

```
PENDING → IN_PROGRESS → COMPLETED
    ↓
CANCELLED
```

| Status | Description | Can Transition To |
|--------|-------------|-------------------|
| PENDING | Planned but not started | IN_PROGRESS, COMPLETED, CANCELLED |
| IN_PROGRESS | Currently being executed | COMPLETED, CANCELLED |
| COMPLETED | Successfully finished | (terminal state) |
| CANCELLED | No longer needed | (terminal state) |

### Overdue Detection

Activities are automatically flagged as **overdue** when:
- Status is PENDING
- Due date is in the past

Overdue is a computed property—the stored status remains PENDING. This allows managers to see what's behind schedule without losing planning data.

### Activity Templates

**Templates** define reusable activity patterns for automatic generation. Templates specify:
- Activity type and notes template
- Trigger conditions for when to create activities
- Active/inactive status

**Trigger Types:**

| Trigger | Description | Example |
|---------|-------------|---------|
| DAY_OFFSET | Days after batch creation | "Day 45: First vaccination" |
| WEIGHT_THRESHOLD | When average weight reached | "At 100g: Transfer to sea" |
| STAGE_TRANSITION | When lifecycle stage changes | "On Smolt: Final freshwater sampling" |

Currently, **DAY_OFFSET** triggers are processed automatically when batches are created. WEIGHT_THRESHOLD and STAGE_TRANSITION triggers require manual generation or future automation.

### Variance Analysis

**Variance** measures the difference between planned due dates and actual completion:

```
Variance (days) = Completion Date - Due Date
```

| Variance | Interpretation |
|----------|----------------|
| Negative | Completed early |
| Zero | Completed on time |
| Positive | Completed late |

The Variance Report aggregates this data to identify patterns, problematic activity types, and operational efficiency trends.

---

## Production Planner Page

**Navigation:** Main Menu → Production Planner (or `/production-planner`)

### Page Layout

The Production Planner page displays all planned activities in a filterable, sortable interface:

**Header Section:**
- Page title with activity count
- Quick action buttons: "Templates", "Variance Report", "Create Activity"

**Filter Bar:**
- Scenario selector
- Activity type dropdown
- Status filter tabs (All, Pending, In Progress, Completed, Cancelled)
- Date range pickers
- Search box (searches notes)

**Activity List:**
- Sortable columns: Batch, Activity Type, Due Date, Status, Container
- Status badges with color coding
- Overdue indicators (red badge for past-due PENDING activities)
- Row actions: View, Edit, Complete, Delete

**View Toggle:**
- List view (default)
- Calendar view (activities on timeline)

### Creating an Activity

1. Click **"Create Activity"** button
2. Fill in the form:
   - Select **Scenario** (required)
   - Select **Batch** (required)
   - Choose **Activity Type**
   - Set **Due Date**
   - Optionally select **Container**
   - Add **Notes** with operational context
3. Click **Save**

The activity appears in the list with PENDING status.

### Editing an Activity

1. Click the activity row or the edit icon
2. Modify fields as needed
3. Click **Save**

**Note:** Editing a COMPLETED activity is allowed but should be done carefully to maintain audit integrity.

### Completing an Activity

**Method 1: Quick Complete**
1. Click the checkmark icon on the activity row
2. Confirm completion

**Method 2: Edit and Complete**
1. Open the activity
2. Change status to COMPLETED
3. Save

Completion records:
- Timestamp of completion
- User who completed the activity
- Full audit trail via history

### Viewing Overdue Activities

1. Click the **"Overdue"** status tab
2. Activities past their due date with PENDING status appear
3. Sort by due date to prioritize oldest items
4. Complete or reschedule as needed

---

## Activity Template Management

**Navigation:** Production Planner → "Templates" button (or `/activity-templates`)

### Template Management Page

The page provides a dedicated interface for managing activity templates:

**KPI Cards:**
- Total templates count
- Active templates count
- Inactive templates count

**Template List:**
- Searchable by name
- Filterable by status (All, Active, Inactive) and activity type
- Columns: Name, Activity Type, Trigger Type, Trigger Value, Status
- Row actions: Edit, Activate/Deactivate, Delete

### Creating a Template

1. Click **"New Template"** button
2. Fill in the form:
   - **Name**: Descriptive identifier (e.g., "Standard Salmon - First Vaccination")
   - **Description**: Purpose and context
   - **Activity Type**: Type of activity to generate
   - **Trigger Type**: When to create the activity
   - **Trigger Value**: 
     - For DAY_OFFSET: Number of days after batch creation
     - For WEIGHT_THRESHOLD: Target weight in grams
     - For STAGE_TRANSITION: Target lifecycle stage
   - **Notes Template**: Pre-filled notes for generated activities
   - **Active**: Whether template applies to new batches
3. Click **Save**

### Template Trigger Examples

| Template Name | Type | Trigger | Value | Generated Due Date |
|---------------|------|---------|-------|-------------------|
| First Vaccination | VACCINATION | DAY_OFFSET | 45 | Batch start + 45 days |
| Smolt Transfer | TRANSFER | DAY_OFFSET | 120 | Batch start + 120 days |
| Weekly Sampling | SAMPLING | DAY_OFFSET | 7 | Batch start + 7 days |
| Sea Transfer | TRANSFER | WEIGHT_THRESHOLD | 100 | When avg weight ≥ 100g |
| Final FW Sample | SAMPLING | STAGE_TRANSITION | Smolt | When stage becomes Smolt |

### Activating/Deactivating Templates

- **Active templates**: Apply to new batches (auto-generation for DAY_OFFSET)
- **Inactive templates**: Preserved for reference but not applied

Toggle status via the row action or edit form. Deactivating a template does not affect already-generated activities.

### Generating Activities Manually

For WEIGHT_THRESHOLD or STAGE_TRANSITION triggers, or to generate from an inactive template:

1. Open the template
2. Click **"Generate for Batch"**
3. Select the scenario and batch
4. Optionally override the due date
5. Click **Generate**

A new planned activity is created based on the template.

---

## Variance Report

**Navigation:** Production Planner → "Variance Report" button (or `/variance-report`)

### Purpose

The Variance Report provides insight into operational execution efficiency by comparing planned schedules with actual completion. Use it to:
- Identify consistently late activity types
- Track completion rates over time
- Spot operational bottlenecks
- Measure planning accuracy

### Report Layout

**KPI Cards:**
| Metric | Description |
|--------|-------------|
| Total Activities | Count of activities in filter scope |
| Completion Rate | Percentage completed (COMPLETED ÷ Total) |
| On-Time Rate | Percentage completed on or before due date |
| Overdue | Count of PENDING activities past due date |

**Charts:**

1. **Completion Rates by Activity Type**
   - Bar chart showing completion percentage per type
   - Quick visual comparison across activity categories

2. **Variance Distribution**
   - Bar chart showing Early / On-Time / Late counts
   - Overall execution timing distribution

3. **Performance Over Time**
   - Line chart showing completed vs. pending over periods
   - Trend visualization for operational velocity

**Statistics Table:**
- Detailed breakdown per activity type
- Total count, completed count, pending count
- Completion rate percentage
- Average variance (days)

### Using Filters

| Filter | Options | Effect |
|--------|---------|--------|
| Activity Type | All types or specific | Narrow to one activity category |
| From Date | Date picker | Include activities due on/after |
| To Date | Date picker | Include activities due on/before |
| Grouping | Weekly / Monthly | Time series aggregation period |

**Example Analysis Scenarios:**

1. **"Which activity types are consistently late?"**
   - View completion rates by type
   - Check average variance in statistics table
   - Focus improvement on lowest performers

2. **"Is our execution improving over time?"**
   - Set date range to last 6 months
   - View Performance Over Time chart
   - Look for increasing completion trend

3. **"How did we perform last quarter?"**
   - Set date range to quarter
   - Check overall completion rate and on-time rate
   - Compare to previous quarter

---

## Transfer Workflow Integration

### Concept

TRANSFER activities can spawn **Transfer Workflows** for complex multi-container, multi-day operations. This provides:
- Detailed planning in Production Planner
- Execution tracking in Transfer Workflow system
- Automatic status synchronization

### Workflow

```
Planned Activity (TRANSFER, PENDING)
         ↓ [Spawn Workflow]
Planned Activity (TRANSFER, IN_PROGRESS) ←→ Transfer Workflow (IN_PROGRESS)
         ↓ [Workflow Completes]
Planned Activity (TRANSFER, COMPLETED) ←→ Transfer Workflow (COMPLETED)
```

### Spawning a Transfer Workflow

1. Create a planned activity with **Activity Type = TRANSFER**
2. When ready to execute, click **"Spawn Workflow"**
3. Select workflow parameters:
   - Workflow Type (LIFECYCLE_TRANSITION, REDISTRIBUTION, etc.)
   - Source Lifecycle Stage
   - Destination Lifecycle Stage
4. Click **Create Workflow**

The system:
- Creates a Transfer Workflow linked to the activity
- Sets activity status to IN_PROGRESS
- Records the link for tracking

### Automatic Completion

When all Transfer Actions in the workflow complete:
- The workflow status becomes COMPLETED
- A signal automatically marks the linked planned activity as COMPLETED
- Completion timestamp and user are recorded

No manual intervention needed—the planning layer stays synchronized with execution.

### When to Use

| Scenario | Use Plain Activity | Use + Transfer Workflow |
|----------|-------------------|-------------------------|
| Simple container move | ✓ | |
| Multi-day transfer operation | | ✓ |
| Intercompany transfer | | ✓ |
| Track transfer mortality | | ✓ |
| Coordinate multiple container moves | | ✓ |

---

## Best Practices

### Planning

1. **Use Scenarios Consistently**
   - Create a "Production Plan" scenario for real operations
   - Use separate scenarios for what-if analysis
   - Archive completed scenarios rather than deleting

2. **Plan Ahead**
   - Enter activities 2-4 weeks before due dates
   - Use templates for recurring activities
   - Review upcoming activities weekly

3. **Be Specific with Notes**
   - Include context: "Vaccination with IHN-1234, requires vet approval"
   - Reference external documents or protocols
   - Note dependencies on other activities

### Templates

4. **Build a Template Library**
   - Create templates for standard lifecycle events
   - Use consistent naming: "[Species] - [Stage] - [Activity]"
   - Document trigger rationale in descriptions

5. **Test Templates Before Activating**
   - Use "Generate for Batch" on a test batch
   - Verify due dates calculate correctly
   - Check notes template formatting

### Execution

6. **Complete Activities Promptly**
   - Mark complete as soon as execution finishes
   - Don't batch completions—accuracy matters for variance

7. **Handle Overdue Activities**
   - Review overdue list daily
   - Either complete (if done) or reschedule (adjust due date)
   - Investigate patterns in frequently overdue types

### Variance Analysis

8. **Review Variance Weekly**
   - Check completion rates by type
   - Identify systemic delays
   - Adjust templates or planning based on data

9. **Set Realistic Due Dates**
   - If a type is consistently late, adjust template offsets
   - Account for weekends and holidays
   - Include buffer for complex activities

---

## API Reference Summary

### Planned Activities

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/planning/planned-activities/` | GET | List activities (with filtering) |
| `/api/v1/planning/planned-activities/` | POST | Create activity |
| `/api/v1/planning/planned-activities/{id}/` | GET | Retrieve activity |
| `/api/v1/planning/planned-activities/{id}/` | PUT/PATCH | Update activity |
| `/api/v1/planning/planned-activities/{id}/` | DELETE | Delete activity |
| `/api/v1/planning/planned-activities/{id}/mark-completed/` | POST | Quick complete |
| `/api/v1/planning/planned-activities/{id}/spawn-workflow/` | POST | Create Transfer Workflow |
| `/api/v1/planning/planned-activities/variance-report/` | GET | Variance analysis |

**Filter Parameters (GET list):**
- `scenario`: Scenario ID
- `batch`: Batch ID
- `activity_type`: Activity type code
- `status`: Status code
- `container`: Container ID
- `is_overdue`: true/false
- `due_date_after`: ISO date
- `due_date_before`: ISO date
- `search`: Text search in notes

### Activity Templates

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/planning/activity-templates/` | GET | List templates |
| `/api/v1/planning/activity-templates/` | POST | Create template |
| `/api/v1/planning/activity-templates/{id}/` | GET | Retrieve template |
| `/api/v1/planning/activity-templates/{id}/` | PUT/PATCH | Update template |
| `/api/v1/planning/activity-templates/{id}/` | DELETE | Delete template |
| `/api/v1/planning/activity-templates/{id}/generate-for-batch/` | POST | Generate activity |

### Variance Report

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/planning/planned-activities/variance-report/` | GET | Get variance analysis |

**Parameters:**
- `scenario`: Filter by scenario ID
- `due_date_after`: Include activities due on/after date
- `due_date_before`: Include activities due on/before date
- `activity_type`: Filter by activity type
- `grouping`: Time series grouping (weekly/monthly)

**Response Structure:**
```json
{
  "summary": {
    "total_activities": 100,
    "completed_activities": 75,
    "pending_activities": 20,
    "cancelled_activities": 5,
    "overdue_activities": 3,
    "completion_rate_percent": 75.0,
    "on_time_rate_percent": 90.0,
    "average_variance_days": 1.2,
    "late_count": 8,
    "early_count": 10
  },
  "by_activity_type": [
    {
      "activity_type": "VACCINATION",
      "activity_type_display": "Vaccination",
      "total": 20,
      "completed": 18,
      "pending": 2,
      "completion_rate": 90.0,
      "average_variance_days": 0.5
    }
  ],
  "time_series": [
    {
      "period_start": "2024-01-01",
      "period_end": "2024-01-07",
      "completed_count": 15,
      "pending_count": 5,
      "completion_rate": 75.0
    }
  ]
}
```

---

## Glossary

| Term | Definition |
|------|------------|
| Activity | A single planned operational task |
| Activity Type | Category of operation (VACCINATION, TRANSFER, etc.) |
| Due Date | Planned execution date |
| Overdue | PENDING activity past its due date |
| Scenario | Planning context grouping related activities |
| Template | Reusable pattern for generating activities |
| Trigger | Condition that determines when to create an activity |
| Variance | Difference between due date and completion date |
| Workflow | Multi-step transfer operation (Transfer Workflow system) |

---

## Support

For questions about Production Planning:
- **System Issues**: Contact AquaMind Development Team
- **Operational Questions**: Contact Operations Manager
- **Template Configuration**: Contact Production Planning Lead


