# AquaMind Audit Trail Implementation Assessment
Date: 2025-09-10  

---

## Executive Summary
- **django-auditlog** is **not** installed or used. Audit entries are not written to `django_admin_log` for API actions. [1], [2]  
- **django-simple-history** *is* installed and configured (app + middleware). It records create / update / delete (CUD) events with `history_user` for models that declare `HistoricalRecords()`. [1], [2], [8]  
- **Coverage is partial**: many transactional models are **not** tracked—e.g. FeedingEvent, BatchTransfer, MortalityEvent (batch app), Health journal / lab / mortality / lice, BatchContainerAssignment, GrowthSample, and most infrastructure entities except Container. [12]–[23]  
- **Tracked models** include Batch, Container, FeedStock, multiple Scenario models, and several Broodstock models; these *do* record CUD with user attribution. [3]–[7], [8]–[11]  
- **No custom DRF logging**: viewsets rely entirely on simple-history where enabled. [24]–[27]  

**Bottom line:** an audit trail exists but only for a subset of models. Extending simple-history and capturing change reasons in the API layer are required to meet “log all meaningful CUD actions” across apps.

---

## What’s Implemented
| Element | Status | Evidence |
|---------|--------|----------|
| Library | `django-simple-history==3.8.0` | [1] |
| App & Middleware | `simple_history` in `INSTALLED_APPS`; `HistoryRequestMiddleware` active | [2] |
| Tracked models (examples) | Batch, Container, FeedStock, Scenario models, Broodstock models | [3]–[7] |
| Historical tables | `history_type` (+ / ~ / −), `history_user`, `history_date`, `history_change_reason` | [8]–[11] |

### Representative Tracked Models
- **Batch** → `HistoricalBatch` [3], [8]  
- **Container** → `HistoricalContainer` [4], [9]  
- **FeedStock** → `HistoricalFeedStock` [5], [10]  
- **Scenario**: `TGCModel`, `FCRModel`, `MortalityModel`, `Scenario`, `ScenarioModelChange` each with history [6], [11]  
- **Broodstock**: `BroodstockFish`, `FishMovement`, `EggProduction`, `BreedingPair`, `BatchParentage` [7]  

---

## Gaps (Untracked Models / Actions)

| Domain | Key Models / Actions *not* tracked | Evidence |
|--------|-------------------------------------|----------|
| Inventory | FeedingEvent (record feeding) | [12] |
| Batch Lifecycle | BatchTransfer, BatchContainerAssignment, GrowthSample, MortalityEvent (batch) | [13], [22], [23], [14] |
| Health | JournalEntry, MortalityRecord, LiceCount, HealthLabSample | [15]–[17] |
| Infrastructure | Area, Hall, FreshwaterStation, Sensor, ContainerType | [19]–[21] |
| Users & RBAC | Django User, UserProfile | [18] |

Additionally:
- No DRF-level logging; relies solely on model coverage. [24]–[27]  
- `django_admin_log` only records Django-admin UI actions, not API calls. [2]

---

## Coverage Matrix (Selected)

| Model / Action | Covered? | Notes |
|----------------|----------|-------|
| Batch | ✅ | HistoricalBatch present |
| Container | ✅ | HistoricalContainer present |
| FeedStock | ✅ | HistoricalFeedStock present |
| Scenario models | ✅ | All core scenario models tracked |
| BroodstockFish, FishMovement, EggProduction, BreedingPair, BatchParentage | ✅ | Broodstock audit-ready |
| FeedingEvent | ❌ | No `HistoricalRecords()` |
| BatchTransfer | ❌ | No tracking |
| BatchContainerAssignment | ❌ | No tracking |
| GrowthSample | ❌ | No tracking |
| MortalityEvent (batch) | ❌ | No tracking |
| JournalEntry, MortalityRecord, LiceCount, HealthLabSample | ❌ | No tracking |
| Area, Hall, Station, Sensor, ContainerType | ❌ | Only Container tracked |
| User / UserProfile | ❌ | Not registered with simple-history |

---

## Recommendations

### 1  Expand simple-history Coverage
Add `history = HistoricalRecords()` to all untracked models that represent business-critical state transitions, prioritising:
- FeedingEvent, BatchTransfer, BatchContainerAssignment, GrowthSample, MortalityEvent (batch)
- Health: JournalEntry, HealthLabSample, MortalityRecord, LiceCount
- Infrastructure: Area, Hall, FreshwaterStation, Sensor, ContainerType
- Users: register Django’s built-in `User` and `UserProfile`

**Option A – inline field**  
Add the field to each model and generate migrations.

**Option B – central registration**  
For third-party or legacy models:

```python
# apps.core.apps.py (example)
from django.apps import AppConfig
from simple_history import register
from django.contrib.auth import get_user_model

class CoreConfig(AppConfig):
    name = "apps.core"

    def ready(self):
        register(get_user_model())
```

### 2  Capture Change Reasons via DRF
Provide human-readable *why* using a mixin:

```python
from simple_history.utils import update_change_reason
from rest_framework import mixins, viewsets

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

Inherit this mixin in each `ModelViewSet`.

### 3  Testing & CI
- Write tests asserting that POST / PUT / PATCH / DELETE create history rows with correct `history_user` and `history_type`.
- Example: after creating a FeedingEvent, assert a new `HistoricalFeedingEvent` row exists (once model is tracked).

### 4  Operational Access
- Optional read-only endpoints to expose history (paginated, filterable by user/date) for audit review.

---

## Conclusion
An audit trail exists but is incomplete. Extending simple-history to all transactional models, adding change-reason capture, and verifying via tests will satisfy the requirement to log all meaningful create/update/delete actions across the AquaMind platform.

---

## Sources
1. `requirements.txt` (django-simple-history present)  
2. `aquamind/settings.py` (simple_history app + middleware; django.contrib.admin present)  
3. `apps/batch/models/batch.py`  
4. `apps/infrastructure/models/container.py`  
5. `apps/inventory/models/stock.py`  
6. `apps/scenario/models.py`  
7. `apps/broodstock/models.py`  
8. `apps/batch/migrations/0016_historicalbatch.py`  
9. `apps/infrastructure/migrations/0006_historicalcontainer.py`  
10. `apps/inventory/migrations/0008_historicalfeedstock.py`  
11. `apps/scenario/migrations/0001_initial.py`  
12. `apps/inventory/models/feeding.py`  
13. `apps/batch/models/transfer.py`  
14. `apps/batch/models/mortality.py`  
15. `apps/health/models/journal_entry.py`  
16. `apps/health/models/mortality.py`  
17. `apps/health/models/lab_sample.py`  
18. `apps/users/models.py`  
19. `apps/infrastructure/models/container_type.py`  
20. `apps/infrastructure/models/area.py`  
21. `apps/infrastructure/models/sensor.py`  
22. `apps/batch/models/assignment.py`  
23. `apps/batch/models/growth.py`  
24. `apps/batch/api/viewsets.py`  
25. `apps/inventory/api/viewsets/feeding.py`  
26. `apps/infrastructure/api/viewsets/container.py`  
27. `apps/users/api/views.py`  
