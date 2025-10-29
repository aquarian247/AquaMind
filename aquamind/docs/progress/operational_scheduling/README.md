# Operational Scheduling Feature - Complete Documentation Package

**Version**: 1.0  
**Last Updated**: October 28, 2025  
**Prepared by**: Manus AI

---

## Overview

This package contains all the documentation needed to implement the **Operational Scheduling** feature (Production Planner) in AquaMind. The documentation is organized for **agent-driven development** in Cursor.ai IDE, with clear separation between backend and frontend concerns.

### What's Included

1. **Backend Documentation** (3 files, ~70,000 words)
   - Complete architecture and data model
   - Step-by-step implementation plan
   - REST API specification

2. **Frontend Documentation** (2 files, ~40,000 words)
   - UI/UX specifications with component details
   - User guide with workflows

3. **Stakeholder Presentation** (1 file)
   - 24-slide presentation with Aquatic Blueprint aesthetic
   - Covers feature overview, workflows, and implementation roadmap

4. **This README**
   - Copy instructions for all files
   - Agent workflow recommendations

---

## File Organization

### Backend Documentation

Copy these files to: `aquarian247/AquaMind/aquamind/docs/progress/`

| File Name | Size | Description |
|-----------|------|-------------|
| `operational_scheduling_architecture.md` | ~22,000 words | Complete data model, integration architecture, business logic, and database schema |
| `operational_scheduling_implementation_plan.md` | ~30,000 words | Step-by-step implementation guide with tasks, acceptance criteria, and testing strategy |
| `planned_activity_api_specification.md` | ~18,000 words | REST API documentation with request/response examples and error handling |

**Total Backend Documentation**: ~70,000 words

### Frontend Documentation

Copy these files to: `aquarian247/AquaMind-Frontend/docs/progress/`

| File Name | Size | Description |
|-----------|------|-------------|
| `operational_scheduling_ui_specification.md` | ~30,000 words | Complete UI/UX design, component specifications, API integration, and responsive design |
| `production_planner_user_guide.md` | ~10,000 words | End-user documentation with workflows, best practices, and troubleshooting |

**Total Frontend Documentation**: ~40,000 words

### Presentation

Copy this file to: `aquarian247/AquaMind/aquamind/docs/presentations/` (or share with stakeholders)

| File Name | Description |
|-----------|-------------|
| `operational_scheduling_presentation/` | 24-slide presentation (HTML format) with Aquatic Blueprint aesthetic |

**Note**: The presentation can be exported to PDF or PPT using the `manus-export-slides` utility if needed.

---

## Copy Instructions

### Step 1: Copy Backend Documentation

```bash
# Navigate to the AquaMind backend repository
cd /path/to/aquarian247/AquaMind

# Create the progress directory if it doesn't exist
mkdir -p aquamind/docs/progress

# Copy the three backend documentation files
cp /home/ubuntu/backend_docs/operational_scheduling_architecture.md aquamind/docs/progress/
cp /home/ubuntu/backend_docs/operational_scheduling_implementation_plan.md aquamind/docs/progress/
cp /home/ubuntu/backend_docs/planned_activity_api_specification.md aquamind/docs/progress/
```

### Step 2: Copy Frontend Documentation

```bash
# Navigate to the AquaMind frontend repository
cd /path/to/aquarian247/AquaMind-Frontend

# Create the progress directory if it doesn't exist
mkdir -p docs/progress

# Copy the two frontend documentation files
cp /home/ubuntu/frontend_docs/operational_scheduling_ui_specification.md docs/progress/
cp /home/ubuntu/frontend_docs/production_planner_user_guide.md docs/progress/
```

### Step 3: Copy Presentation (Optional)

```bash
# Navigate to the AquaMind backend repository
cd /path/to/aquarian247/AquaMind

# Create the presentations directory if it doesn't exist
mkdir -p aquamind/docs/presentations

# Copy the presentation directory
cp -r /home/ubuntu/operational_scheduling_presentation aquamind/docs/presentations/
```

---

## Agent Workflow Recommendations

### For Backend Agents (Cursor.ai)

**Context to Provide**:
1. `aquamind/docs/progress/operational_scheduling_architecture.md` (PRIMARY)
2. `aquamind/docs/progress/operational_scheduling_implementation_plan.md` (SECONDARY)
3. `aquamind/docs/progress/planned_activity_api_specification.md` (REFERENCE)
4. `aquamind/docs/architecture.md` (EXISTING - for project standards)
5. `aquamind/docs/quality_assurance/api_standards.md` (EXISTING - for API conventions)
6. `aquamind/docs/quality_assurance/code_organization_guidelines.md` (EXISTING - for file structure)

**Recommended Workflow**:

1. **Phase 1: Data Model** (Week 1)
   - Start with the architecture document
   - Create the `planning` app structure
   - Implement `PlannedActivity` and `ActivityTemplate` models
   - Run migrations

2. **Phase 2: API Endpoints** (Week 2)
   - Implement serializers and viewsets
   - Add custom actions (`mark-completed`, `spawn-workflow`)
   - Register routers
   - Test endpoints with Postman/curl

3. **Phase 3: Integration** (Week 3)
   - Add custom action to `ScenarioViewSet`
   - Implement Transfer Workflow linking logic
   - Add business logic (overdue detection, completion tracking)

4. **Phase 4: Testing** (Week 4)
   - Write unit tests for models
   - Write integration tests for API endpoints
   - Test Transfer Workflow integration

**Key Reminders for Backend Agents**:
- ✅ Follow the existing `batch` app structure (models, serializers, viewsets, routers)
- ✅ Use kebab-case for API endpoint basenames (`planned-activities`, not `planned_activities`)
- ✅ Add filtering and searching to all list endpoints
- ✅ Use `TimestampedModel` as the base class for all models
- ✅ Add audit fields (`created_by`, `updated_by`) to all models

---

### For Frontend Agents (Cursor.ai)

**Context to Provide**:
1. `docs/progress/operational_scheduling_ui_specification.md` (PRIMARY)
2. `docs/progress/production_planner_user_guide.md` (SECONDARY - for understanding user workflows)
3. `docs/architecture.md` (EXISTING - for project standards)
4. `docs/DJANGO_INTEGRATION_GUIDE.md` (EXISTING - for API integration patterns)

**Recommended Workflow**:

1. **Phase 1: API Client Sync** (Day 1)
   - Run `npm run sync:openapi` to generate TypeScript API client
   - Verify that `PlanningService` and `ScenarioService` methods are available

2. **Phase 2: Core Components** (Week 1)
   - Create `ProductionPlannerPage.tsx`
   - Implement `ProductionPlannerKPIDashboard.tsx`
   - Implement `PlannedActivityFilters.tsx`
   - Add routing in `App.tsx`

3. **Phase 3: Timeline View** (Week 2)
   - Implement `ProductionPlannerTimeline.tsx` (Gantt chart)
   - Add batch grouping and expansion logic
   - Implement activity click handlers

4. **Phase 4: Forms and Modals** (Week 3)
   - Implement `PlannedActivityForm.tsx` (Create/Edit)
   - Implement `PlannedActivityDetailModal.tsx`
   - Add form validation with Zod
   - Implement mutations (create, update, mark-completed)

5. **Phase 5: Integration** (Week 4)
   - Add "Planned Activities" tab to Batch Detail page
   - Add "Planned Activities" section to Scenario Planning page
   - Implement Transfer Workflow linking UI
   - Test responsive design on mobile

**Key Reminders for Frontend Agents**:
- ✅ Use TanStack Query for all API calls (no direct fetch/axios)
- ✅ Use Shadcn/ui components (`Button`, `Card`, `Dialog`, `Table`, etc.)
- ✅ Follow the Solarized theme (colors defined in `index.css`)
- ✅ Use React Hook Form + Zod for all forms
- ✅ Invalidate queries after mutations to trigger refetch

---

## Key Architecture Decisions

### 1. Coexistence with Transfer Workflows

**Decision**: Planned Activities and Transfer Workflows **coexist** as separate but linked features.

**Rationale**:
- **Transfer Workflows** are a mature, well-designed feature for executing complex, multi-day transfers with financial implications.
- **Planned Activities** are a new feature for simple, single-event operational planning across all activity types.
- Linking the two provides the best of both worlds: simple planning UX + detailed execution tracking.

**Implementation**:
- `PlannedActivity.transfer_workflow` (FK, nullable) links to `TransferWorkflow`
- `PlannedActivity.activity_type = TRANSFER` can spawn a new workflow via custom action
- When a `TransferWorkflow` is completed, the linked `PlannedActivity` is auto-completed

### 2. Activity Types

**Final List** (7 types):
1. **Vaccination**: Scheduled immunization events
2. **Treatment/Health Intervention**: De-licing, disease treatments, parasite control, veterinary procedures
3. **Culling**: Planned removal of underperforming or diseased fish
4. **Sale/Harvest**: Planned harvest events for market delivery
5. **Feed Strategy Change**: Transition to new feed type or feeding regime
6. **Input/Consumable**: Planned addition of consumables (oxygen, chemicals)
7. **Transfer**: Container-to-container movements (can link to Transfer Workflows)

**Note**: Type 2 (Treatment/Health Intervention) was added based on stakeholder feedback to support de-licing and other health interventions common in sea-based salmon farming.

### 3. Scenario Integration

**Decision**: All Planned Activities belong to a `Scenario`.

**Rationale**:
- Enables what-if analysis (e.g., "Aggressive Growth Plan" vs. "Conservative Growth Plan")
- Allows users to compare different operational strategies
- Aligns with AquaMind's core strength in scenario-based planning

**Implementation**:
- `PlannedActivity.scenario` (FK, required)
- Custom action on `ScenarioViewSet`: `/api/v1/scenario/scenarios/{id}/planned-activities/`
- Frontend filters activities by selected scenario

### 4. No Temporary Code

**Decision**: Implement the complete, final architecture from the start (no phased rollout with temporary code).

**Rationale**:
- The application is in active development without users or real data
- Ample time is available for implementation
- Avoiding technical debt and refactoring costs

**Implementation**:
- All models, API endpoints, and UI components are designed for the final state
- Phasing refers to **implementation sequencing** (what to build first), not feature limitations

---

## Testing Strategy

### Backend Testing

**Unit Tests** (`apps/planning/tests/test_models.py`):
- Test `PlannedActivity` model creation and validation
- Test `is_overdue` property logic
- Test `ActivityTemplate` model creation and application

**Integration Tests** (`apps/planning/tests/test_api.py`):
- Test CRUD operations on `/api/v1/planning/planned-activities/`
- Test custom actions (`mark-completed`, `spawn-workflow`)
- Test scenario-based filtering on `/api/v1/scenario/scenarios/{id}/planned-activities/`
- Test Transfer Workflow linking logic

**Coverage Target**: 90%+ for all new code

### Frontend Testing

**Component Tests** (Vitest + React Testing Library):
- Test `ProductionPlannerKPIDashboard` rendering and click handlers
- Test `PlannedActivityFilters` filter logic
- Test `PlannedActivityForm` validation and submission

**Integration Tests**:
- Test full user workflows (create activity → mark as completed)
- Test Transfer Workflow spawning flow

**E2E Tests** (Playwright - optional):
- Test critical user journeys from Production Planner to Transfer Workflow

**Coverage Target**: 80%+ for all new components

---

## Migration and Rollout Strategy

### Database Migrations

1. **Initial Migration** (`0001_initial.py`):
   - Create `PlannedActivity` table
   - Create `ActivityTemplate` table
   - Add indexes on `scenario`, `batch`, `due_date`, `status`

2. **Add Transfer Workflow Link** (`0002_add_transfer_workflow_link.py`):
   - Add `transfer_workflow` FK to `PlannedActivity`
   - Add index on `transfer_workflow`

3. **Add Completion Tracking** (`0003_add_completion_tracking.py`):
   - Add `completed_at`, `completed_by` fields to `PlannedActivity`

### Data Seeding (Optional)

Create sample data for testing:

```python
# apps/planning/management/commands/seed_planned_activities.py

from django.core.management.base import BaseCommand
from apps.planning.models import PlannedActivity
from apps.scenario.models import Scenario
from apps.batch.models import Batch
from datetime import date, timedelta

class Command(BaseCommand):
    help = 'Seed sample planned activities for testing'

    def handle(self, *args, **kwargs):
        scenario = Scenario.objects.first()
        batches = Batch.objects.all()[:5]
        
        for batch in batches:
            # Create a vaccination activity
            PlannedActivity.objects.create(
                scenario=scenario,
                batch=batch,
                activity_type='VACCINATION',
                due_date=date.today() + timedelta(days=7),
                notes='First vaccination at 50g average weight',
            )
            
            # Create a transfer activity
            PlannedActivity.objects.create(
                scenario=scenario,
                batch=batch,
                activity_type='TRANSFER',
                due_date=date.today() + timedelta(days=30),
                notes='Transfer to sea cages',
            )
        
        self.stdout.write(self.style.SUCCESS('Successfully seeded planned activities'))
```

Run with: `python manage.py seed_planned_activities`

---

## Troubleshooting Common Issues

### Issue 1: OpenAPI Sync Fails

**Symptoms**: `npm run sync:openapi` fails with "Cannot connect to backend"

**Solution**:
1. Ensure the Django backend is running (`python manage.py runserver`)
2. Verify the backend URL in `package.json` (should be `http://localhost:8000`)
3. Check that the `planning` app is registered in `INSTALLED_APPS`
4. Verify that the router is included in `aquamind/api/router.py`

### Issue 2: Migrations Fail

**Symptoms**: `python manage.py migrate` fails with "Table already exists"

**Solution**:
1. Drop the `planning_plannedactivity` and `planning_activitytemplate` tables manually
2. Delete the migration files in `apps/planning/migrations/` (except `__init__.py`)
3. Run `python manage.py makemigrations planning`
4. Run `python manage.py migrate`

### Issue 3: API Returns 404

**Symptoms**: Frontend API calls to `/api/v1/planning/planned-activities/` return 404

**Solution**:
1. Verify that the `planning` app router is included in `aquamind/api/router.py`
2. Check that the URL pattern is correct (kebab-case: `planned-activities`, not `planned_activities`)
3. Restart the Django server
4. Test the endpoint with curl: `curl http://localhost:8000/api/v1/planning/planned-activities/`

### Issue 4: Timeline Not Rendering

**Symptoms**: The Production Planner timeline is blank or shows no activities

**Solution**:
1. Check the browser console for errors
2. Verify that the API call is successful (check Network tab)
3. Ensure that the `scenarioId` is set correctly
4. Check that the `activities` array is not empty
5. Verify that the date range filter is not excluding all activities

---

## Additional Resources

### Related Documentation

1. **AquaMind PRD** - `aquamind/docs/prd.md`
   - Section 3.1.2.1: Transfer Workflows
   - Section 3.1.3: Scenario Planning

2. **AquaMind Data Model** - `aquamind/docs/database/data_model.md`
   - Batch app models
   - Scenario app models

3. **Transfer Workflow Finance Guide** - `aquamind/docs/user_guides/TRANSFER_WORKFLOW_FINANCE_GUIDE.md`
   - Understanding the existing Transfer Workflow feature

4. **Frontend Architecture** - `AquaMind-Frontend/docs/architecture.md`
   - React/TypeScript conventions
   - TanStack Query patterns

### External References

1. **Django REST Framework** - https://www.django-rest-framework.org/
2. **TanStack Query** - https://tanstack.com/query/latest
3. **Shadcn/ui** - https://ui.shadcn.com/
4. **React Hook Form** - https://react-hook-form.com/
5. **Zod** - https://zod.dev/

---

## Contact and Support

For questions or clarifications about this documentation:

1. **Architecture Questions**: Review `operational_scheduling_architecture.md`
2. **Implementation Questions**: Review `operational_scheduling_implementation_plan.md`
3. **API Questions**: Review `planned_activity_api_specification.md`
4. **UI/UX Questions**: Review `operational_scheduling_ui_specification.md`
5. **User Workflow Questions**: Review `production_planner_user_guide.md`

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | October 28, 2025 | Initial release with complete documentation package |

---

**End of README**
