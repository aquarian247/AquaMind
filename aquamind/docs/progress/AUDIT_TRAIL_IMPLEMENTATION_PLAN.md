# Audit Trail Coverage Expansion — Implementation Plan

Date: 2025-09-10  
Owner: Backend Team  
Related: docs/progress/AUDIT_TRAIL_ASSESSMENT.md  

---

## 1. Objectives
• Achieve complete, reliable insight into all Create/Update/Delete (CUD) operations across core domains.  
• Standardize on django-simple-history for model-level auditing with user attribution and change reasons.  
• Exclude high-volume environmental hypertables from scope.  

## 2. Scope
In scope (add/ensure `HistoricalRecords()`):  
• **Batch**: BatchTransfer, BatchContainerAssignment, GrowthSample, MortalityEvent  
• **Inventory**: FeedingEvent  
• **Health**: JournalEntry, HealthLabSample, MortalityRecord, LiceCount, Treatment  
• **Infrastructure**: Geography, Area, FreshwaterStation, Hall, ContainerType, Sensor, FeedContainer  
• **Users**: UserProfile; register `auth.User` for history  

Out of scope (high-frequency hypertables):  
`environmental_environmentalreading`, `environmental_weatherdata`  

## 3. Design Decisions
1. Auditing mechanism: **django-simple-history** (already configured via app + HistoryRequestMiddleware).  
2. User attribution: `history_user` auto-populated from request user.  
3. Change reasons captured in DRF layer with `simple_history.utils.update_change_reason`.  
4. **created_by / updated_by / deleted_by** columns **not** added globally → avoid duplication; `history_user` is source of truth.  
   • Keep existing author fields where they have domain meaning (e.g., `recorded_by`).  
5. Deleted-by inferred from historical row with `history_type='-'`; revisit if soft-delete adopted.  
6. Historical backfill: run populate-history after migrations to snapshot pre-existing rows.  
7. History access primarily via Django admin but add read-only API endpoints that will be accessed by AquaMind-Frontend code in a future Audit Trail component.  

## 4. Implementation Phases

### Phase 0 – Foundations
• Verify `simple_history` in `INSTALLED_APPS`; confirm `HistoryRequestMiddleware` order.  
• Add reusable DRF mixin for change reasons:  
```python
from simple_history.utils import update_change_reason

class HistoryReasonMixin:
    def _reason(self, action):
        return f"{action} via API by {self.request.user}"

    def perform_create(self, serializer):
        instance = serializer.save()
        update_change_reason(instance, self._reason("created"))

    def perform_update(self, serializer):
        instance = serializer.save()
        update_change_reason(instance, self._reason("updated"))

    def perform_destroy(self, instance):
        update_change_reason(instance, self._reason("deleted"))
        instance.delete()
```  
• Adopt mixin in representative viewsets (Container, Batch, FeedingEvent) and document pattern.  
• CI: add test asserting change reason exists on create/update/delete for one model.  

### Phase 1 – High-Impact Domains (Batch + Inventory)
Models: `batch_batchtransfer`, `batch_batchcontainerassignment`, `batch_growthsample`, `batch_mortalityevent`, `inventory_feedingevent`  
Steps:  
1. Add `history = HistoricalRecords()`; create migrations.  
2. Backfill histories (`manage.py populate_history --auto`). NB! If this becomes complicated it can be skipped as therre is only limited test data in the db at this point. 
3. Ensure related viewsets inherit `HistoryReasonMixin`.  
4. Tests: CRUD produces history rows with correct `history_user`, `history_type`, and change reason.  
5. QA: manual admin verification.  

### Phase 2 – Health Domain
Models: `health_journalentry`, `health_healthlabsample`, `health_mortalityrecord`, `health_licecount`, `health_treatment`  
Same workflow as Phase 1 plus permission tests on any exposed history endpoints.  

### Phase 3 – Infrastructure Entities
Models: `infrastructure_geography`, `infrastructure_area`, `infrastructure_freshwaterstation`, `infrastructure_hall`, `infrastructure_containertype`, `infrastructure_sensor`, `infrastructure_feedcontainer`  
Add history, migrate, backfill (optional), basic CRUD history tests. Confirm no audit added to hypertables.  

### Phase 4 – Users & Auth
• Register Django User:  
```python
from django.apps import AppConfig
from django.contrib.auth import get_user_model
from simple_history import register

class UsersConfig(AppConfig):
    name = "apps.users"
    def ready(self):
        register(get_user_model())
```  
• Add `history = HistoricalRecords()` to `users_userprofile`.  
• Tests: admin edits create history; histories restricted to superusers.  

### Phase 5 – Operationalisation & APIs
• Create read-only history endpoints `/api/v1/history/<model>/` for all audit data.  
• Filters: date range, user, `history_type`; paginated.  
• OpenAPI spec updated via Spectacular.  
• Register `SimpleHistoryAdmin` for all new models.  

### Phase 6 – QA, Docs, Rollout
• Documentation updates:  
  – PRD: add section 3.1.9 “Audit Trail & CUD Logging (Core)”.  
  – Data model: append list of new historical tables and note `history_user_id` semantics (only if missing).  
  – Operator handbook: how to view history in admin / API.  
• QA checklist: tests green; manual CRUD checks; perf sanity.  
• Rollout plan: run migrations.

## 5. Migration & Backfill
• Generate migrations per app.  
• Execute `populate_history` for each new model (chunked if large). NB! As there is only sparse test data this can be skipped, if complicated and time consuming. 
• Ensure indexes on `history_date`, `history_user_id`, key FKs.  
• Rollback strategy: reverse migrations (historical tables remain for data integrity).  

## 6. Testing Strategy
• Unit tests per model factory CRUD → assert history rows (`+`, `~`, `-`).  
• Assert `history_user` == request user; `history_change_reason` contains action.  
• API tests for history endpoints: auth, filters, pagination.  
• Basic perf test: measure CRUD latency before/after auditing.  

## 7. Risks & Mitigations
| Risk | Mitigation |
|------|------------|
| Long backfill time on large tables | Run off-hours; chunked populate; temporarily disable heavy reads |
| PII exposure in histories | Limit access to admins; redact sensitive data if needed |
| Duplicate author fields vs history_user | Do not add new columns; document reliance on history_user |
| API history endpoint sprawl | Expose read-only, paginated, role-restricted endpoints |

## 8. Deliverables
• Code: HistoricalRecords on all scoped models; DRF mixin; optional history API.  
• Tests: unit + integration.  
• Docs: PRD section 3.1.9, data model append, operator guide.  
• Migrations + backfill scripts.  

## 9. Acceptance Criteria
• 100 % of scoped models create history rows on every CUD with correct `history_user`.  
• Change reasons populated for API-driven CUD actions.  
• Migrations + backfill executed (optional); admin shows history.  
• Tests cover representative flows; CI green.  
• PRD and data model docs updated accordingly.  
