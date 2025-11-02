# AquaMind RBAC Assessment

**Date:** 2025-11-02  
**Investigator:** Code Analysis  
**Status:** Foundation exists but major gaps in enforcement

---

## Executive Summary

**Overall Assessment:** AquaMind has a **solid RBAC foundation** with proper data models and authentication, but **lacks consistent enforcement** at the API layer. The system is approximately **30% complete** for production RBAC requirements.

### What's Working ✓
- User profile model with geography, subsidiary, and role fields
- JWT authentication with secure token management
- Privilege escalation prevention (users can't modify their own RBAC fields)
- Custom permission class for finance users
- Comprehensive audit trails via django-simple-history

### What's Missing ✗
- **Geographic/subsidiary data isolation** - Not enforced in ViewSets
- **Role-based functional access** - Veterinarians/QA/Operators can access anything
- **Container/area-level permissions** - Operators see all data, not just their locations
- **Consistent permission enforcement** - Most ViewSets only check `IsAuthenticated`
- **Queryset filtering** - No automatic filtering by user's geography/subsidiary

---

## Detailed Findings

### 1. Authentication & Authorization Foundation ✓

#### Current Implementation
```python
# apps/users/models.py
class UserProfile(models.Model):
    geography = models.CharField(
        max_length=3,
        choices=Geography.choices,
        default=Geography.ALL,
        help_text='Geographic region access level'
    )
    
    subsidiary = models.CharField(
        max_length=3,
        choices=Subsidiary.choices,
        default=Subsidiary.ALL,
        help_text='Subsidiary access level'
    )
    
    role = models.CharField(
        max_length=5,
        choices=Role.choices,
        default=Role.VIEWER,
        help_text='User role and permission level'
    )
    
    def has_geography_access(self, geography):
        """Check if user has access to a specific geography."""
        return self.user.is_superuser or self.geography == Geography.ALL or self.geography == geography
    
    def has_subsidiary_access(self, subsidiary):
        """Check if user has access to a specific subsidiary."""
        return self.user.is_superuser or self.subsidiary == Subsidiary.ALL or self.subsidiary == subsidiary
```

**Status:** ✓ **Complete** - Model structure is solid

**Roles Defined:**
- `ADMIN` - Full system access
- `MANAGER` (MGR) - High-level operational access
- `OPERATOR` (OPR) - Day-to-day operations
- `VETERINARIAN` (VET) - Health data access
- `QA` - Quality assurance access
- `FINANCE` (FIN) - Financial data access
- `VIEWER` - Read-only access

**Geographies:**
- `FAROE_ISLANDS` (FO)
- `SCOTLAND` (SC)
- `ALL` - Cross-geography access

**Subsidiaries:**
- `BROODSTOCK` (BS)
- `FRESHWATER` (FW)
- `FARMING` (FM)
- `LOGISTICS` (LG)
- `ALL` - Cross-subsidiary access

---

### 2. Geographic Data Isolation ✗

#### Current State: NOT IMPLEMENTED

**What Should Happen:**
- Users in Scotland (`geography=SC`) should only see Scottish data
- Users in Faroe Islands (`geography=FO`) should only see Faroese data
- Executives with `geography=ALL` should see everything

**What's Actually Happening:**
Most ViewSets look like this:
```python
# apps/batch/api/viewsets/batch.py
class BatchViewSet(viewsets.ModelViewSet):
    queryset = Batch.objects.all()
    # permission_classes = [IsAuthenticated]  # Only checks authentication!
    
    # NO get_queryset override to filter by geography
    # NO permission class checking user.profile.geography
```

**Impact:**
- ❌ Scottish users can see Faroese batches
- ❌ Faroese users can see Scottish batches
- ❌ No data isolation between geographies
- ❌ Violates PRD requirement: "Users shall only see data relevant to their geography"

**Example Missing Implementation:**
```python
# What SHOULD exist in batch/api/viewsets/batch.py
def get_queryset(self):
    queryset = super().get_queryset()
    user = self.request.user
    
    # Superusers see everything
    if user.is_superuser:
        return queryset
    
    profile = getattr(user, 'profile', None)
    if not profile:
        return queryset.none()
    
    # Filter by geography
    if profile.geography != Geography.ALL:
        # Batches are linked to containers, which are linked to areas/halls
        # Areas/halls are linked to geographies
        queryset = queryset.filter(
            Q(batchcontainerassignment__container__area__geography__name=profile.geography) |
            Q(batchcontainerassignment__container__hall__freshwater_station__geography__name=profile.geography)
        ).distinct()
    
    return queryset
```

---

### 3. Subsidiary Data Isolation ✗

#### Current State: NOT IMPLEMENTED

**What Should Happen:**
- Freshwater users (`subsidiary=FW`) should only see freshwater data
- Farming users (`subsidiary=FM`) should only see farming/sea ring data
- Broodstock users should only see broodstock data

**What's Missing:**
- No queryset filtering by subsidiary
- No permission checks based on subsidiary

**Example for Batch ViewSet:**
```python
# What SHOULD exist
def get_queryset(self):
    queryset = super().get_queryset()
    profile = self.request.user.profile
    
    if profile.subsidiary != Subsidiary.ALL:
        # Filter based on batch lifecycle stage and location
        if profile.subsidiary == Subsidiary.FRESHWATER:
            # Only freshwater lifecycle stages
            queryset = queryset.filter(
                lifecycle_stage__name__in=['Egg', 'Alevin', 'Fry', 'Parr', 'Smolt']
            )
        elif profile.subsidiary == Subsidiary.FARMING:
            # Only post-smolt and adult in sea rings
            queryset = queryset.filter(
                lifecycle_stage__name__in=['Post-Smolt', 'Adult'],
                batchcontainerassignment__container__area__isnull=False
            )
    
    return queryset
```

---

### 4. Role-Based Functional Access ✗

#### Current State: PARTIALLY IMPLEMENTED

**Finance Role:** ✓ **Implemented**
```python
# apps/finance/api/permissions/finance_role.py
class IsFinanceUser(permissions.BasePermission):
    def has_permission(self, request, view):
        if user.is_superuser:
            return True
        profile = getattr(user, "profile", None)
        return profile.role in {Role.ADMIN, Role.FINANCE}

# Usage in finance viewsets
class IntercompanyTransactionViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsFinanceUser]
```

**Other Roles:** ✗ **NOT Implemented**

**Recommended Permission Classes (aligned with QA+Vet may see and enter Health data; treatments reserved to Veterinarians/Admin):**

1) General health contributor (QA write allowed for non-treatment data)
```python
# apps/health/api/permissions.py
from rest_framework import permissions
from apps.users.models import Role

class IsHealthContributor(permissions.BasePermission):
    """VET/QA/Admin can read and write general health data (journal, lice,
    mortality, sampling, lab samples). Other roles are denied."""

    def has_permission(self, request, view):
        u = request.user
        if not u or not u.is_authenticated:
            return False
        if u.is_superuser:
            return True
        p = getattr(u, 'profile', None)
        return bool(p and p.role in {Role.ADMIN, Role.VETERINARIAN, Role.QA})
```

2) Treatment/vaccination editor (restrict to Veterinarian/Admin; QA read-only)
```python
class IsTreatmentEditor(permissions.BasePermission):
    """Only Veterinarian/Admin may create/update/delete treatments/vaccinations;
    QA may read."""

    def has_permission(self, request, view):
        u = request.user
        if not u or not u.is_authenticated:
            return False
        if u.is_superuser:
            return True
        p = getattr(u, 'profile', None)
        if not p:
            return False
        if request.method in permissions.SAFE_METHODS:
            return p.role in {Role.ADMIN, Role.VETERINARIAN, Role.QA}
        return p.role in {Role.ADMIN, Role.VETERINARIAN}
```

3) Operator/manager baseline (non-health operational access)
```python
class IsOperator(permissions.BasePermission):
    """Allow operators to access their assigned containers/areas."""
    
    def has_permission(self, request, view):
        profile = getattr(request.user, 'profile', None)
        if not profile:
            return False
        
        return profile.role in {Role.ADMIN, Role.MANAGER, Role.OPERATOR}
```

**Where These Should Be Applied:**

| App | ViewSet | Permission |
|-----|---------|------------|
| `health` | `JournalEntryViewSet` | `IsHealthContributor` |
| `health` | `HealthSamplingEventViewSet` | `IsHealthContributor` |
| `health` | `LiceCountViewSet` | `IsHealthContributor` |
| `health` | `MortalityRecordViewSet` | `IsHealthContributor` |
| `health` | `HealthLabSampleViewSet` | `IsHealthContributor` |
| `health` | `TreatmentViewSet` | `IsTreatmentEditor` |
| `batch` | `BatchViewSet` | `IsOperator` (plus queryset scoping) |
| `batch` | `BatchContainerAssignmentViewSet` | `IsOperator` (plus queryset scoping) |
| `inventory` | `FeedingEventViewSet` | `IsOperator` (plus queryset scoping) |

### 5. Object-level authorization for writes ✗

Even with queryset scoping, create/update operations must validate the target objects belong to the caller’s scope (geography, subsidiary, assigned locations). Ensure all perform_create/perform_update (or serializer.validate) checks reject out‑of‑scope IDs with 403/404 to prevent posting data into foreign geographies by guessing IDs.

---

### 6. Container/Area-Level Permissions ✗

#### Current State: NOT IMPLEMENTED

**Requirement from Personas:**
> "Sea area operators only see their area and what is going on there; the operators at freshwater stations see only their station's data"

**What's Missing:**
1. No way to assign users to specific containers/areas/stations
2. No queryset filtering based on user's assigned location
3. All operators see all locations in their geography

**Recommended Data Model Extension (simpler preferred approach):** add M2M fields on `UserProfile`; keep a dedicated assignment model only if you need per-link metadata.

```python
# apps/users/models.py (add to UserProfile)
allowed_areas = models.ManyToManyField('infrastructure.Area', blank=True, related_name='permitted_users')
allowed_stations = models.ManyToManyField('infrastructure.FreshwaterStation', blank=True, related_name='permitted_users')
allowed_containers = models.ManyToManyField('infrastructure.Container', blank=True, related_name='permitted_users')
```

**Filtering Implementation:**
```python
# apps/batch/api/viewsets/assignments.py
def get_queryset(self):
    queryset = super().get_queryset()
    user = self.request.user
    profile = getattr(user, 'profile', None)
    
    # Operators only see their assigned locations
    if profile and profile.role == Role.OPERATOR:
        area_ids = profile.allowed_areas.values_list('id', flat=True)
        station_ids = profile.allowed_stations.values_list('id', flat=True)
        container_ids = profile.allowed_containers.values_list('id', flat=True)

        queryset = queryset.filter(
            Q(container__area_id__in=area_ids) |
            Q(container__hall__freshwater_station_id__in=station_ids) |
            Q(container_id__in=container_ids)
        )
    
    return queryset
```

---

## Gap Analysis Summary

### Critical Gaps (High Priority)

| # | Gap | Impact | Effort |
|---|-----|--------|--------|
| 1 | **Geographic data isolation** | HIGH - Users can see data from other countries | MEDIUM |
| 2 | **Subsidiary data isolation** | HIGH - Freshwater users can see farming data | MEDIUM |
| 3 | **Veterinarian permissions** | HIGH - Anyone can modify health data | LOW |
| 4 | **Operator location restrictions** | MEDIUM - Operators see all locations | HIGH |
| 5 | **QA write policy alignment** | MEDIUM - Define QA write scope (non-treatment) | LOW |

### Moderate Gaps (Medium Priority)

| # | Gap | Impact | Effort |
|---|-----|--------|--------|
| 6 | **Manager hierarchical access** | MEDIUM - Managers need filtered views | MEDIUM |
| 7 | **Consistent permission classes** | MEDIUM - Inconsistent enforcement | MEDIUM |
| 8 | **Audit trail on RBAC changes** | LOW - Admin changes not well logged | LOW |

---

## Recommendations

### Phase 1: Critical Security Gaps (2-3 weeks)

**Priority 1: Geographic & Subsidiary Filtering**
1. Create base mixin for geographic/subsidiary filtering
   ```python
   # aquamind/api/mixins.py
   class GeographyFilterMixin:
       def filter_by_user_geography(self, queryset):
           # Implementation for geography filtering
           pass
   ```

2. Apply to all major ViewSets and ensure detail views derive from filtered get_queryset (no direct .get() bypassing scope):
   - `BatchViewSet`
   - `BatchContainerAssignmentViewSet`
   - `FeedingEventViewSet`
   - `HealthJournalEntryViewSet`
   - `InfrastructureViewSets`
3. Add DB indexes to common join/filter columns used in scoping: `container.area_id`, `container.hall_id`, `hall.freshwater_station_id`, `area.geography_id`, `environmental_reading.container_id`, etc.

**Priority 2: Role-Based Permission Classes**
1. Create missing permission classes:
   - `IsHealthContributor`
   - `IsTreatmentEditor`
   - `IsOperator`

2. Apply to health app ViewSets immediately
3. Apply to operational ViewSets

**Priority 3: Object-level Authorization & Testing**
1. Enforce object-level checks in perform_create/perform_update (or serializers) to validate IDs belong to caller’s scope.
2. Create comprehensive RBAC test suite
3. Test geographic isolation
4. Test role-based access, including QA write to non-treatment health endpoints and VET-only edits of treatments
5. Test privilege escalation scenarios and POST/PUT with out-of-scope IDs (expect 403/404)

### Phase 2: Fine-Grained Access Control (3-4 weeks)

**Operator Location Assignment**
1. Add M2M fields on `UserProfile` (`allowed_areas`, `allowed_stations`, `allowed_containers`) or introduce an assignment model if per-link metadata is required
2. Add admin interface for assigning users to locations
3. Implement queryset filtering in ViewSets
4. Test operator restrictions

**Manager Hierarchical Access**
1. Implement area-level manager permissions
2. Implement station-level manager permissions
3. Test manager data visibility

### Phase 3: Audit & Compliance (1-2 weeks)

**Enhanced Audit Logging**
1. Log RBAC field changes (already partially done)
2. Log permission denials
3. Create RBAC audit reports
4. Implement compliance reporting

---

## Implementation Priority Matrix

```
High Impact, Low Effort        │ High Impact, High Effort
───────────────────────────────┼─────────────────────────────
✓ Health contributor permission │ Geographic filtering
✓ Treatment editor permission   │ Subsidiary filtering
✓ IsOperator permission         │ Operator location assignment
✓ Apply permissions to health   │
                                │
Low Impact, Low Effort         │ Low Impact, High Effort
───────────────────────────────┼─────────────────────────────
✓ Audit trail enhancements     │ Complex hierarchical permissions
✓ Permission tests             │ Container-level ACLs
```

---

## Code Examples for Implementation

### 1. Geographic Filtering Mixin

```python
# aquamind/api/mixins.py
from django.db.models import Q
from apps.users.models import Geography, Subsidiary

class RBACFilterMixin:
    """
    Mixin to apply RBAC filtering based on user's geography and subsidiary.
    """
    
    # Subclasses should define these methods to specify how to filter
    geography_filter_field = None  # e.g., 'container__area__geography'
    subsidiary_filter_field = None  # e.g., 'subsidiary'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        return self.apply_rbac_filters(queryset)
    
    def apply_rbac_filters(self, queryset):
        """Apply geography and subsidiary filters based on user profile."""
        user = self.request.user
        
        # Superusers see everything
        if user.is_superuser:
            return queryset
        
        profile = getattr(user, 'profile', None)
        if not profile:
            return queryset.none()
        
        # Apply geography filter
        if profile.geography != Geography.ALL and self.geography_filter_field:
            geography_filter = {
                f'{self.geography_filter_field}': profile.geography
            }
            queryset = queryset.filter(**geography_filter)
        
        # Apply subsidiary filter
        if profile.subsidiary != Subsidiary.ALL and self.subsidiary_filter_field:
            subsidiary_filter = {
                f'{self.subsidiary_filter_field}': profile.subsidiary
            }
            queryset = queryset.filter(**subsidiary_filter)
        
        return queryset
```

### 2. Permission Classes

```python
# apps/health/api/permissions.py
from rest_framework import permissions
from apps.users.models import Role

class IsHealthContributor(permissions.BasePermission):
    """
    VET/QA/Admin can read and write general health data
    (journal, lice, mortality, sampling, lab samples).
    """

    message = "Health data is restricted to Veterinarians, QA, and Admins."

    def has_permission(self, request, view):
        u = request.user
        if not u or not u.is_authenticated:
            return False
        if u.is_superuser:
            return True
        p = getattr(u, 'profile', None)
        return bool(p and p.role in {Role.ADMIN, Role.VETERINARIAN, Role.QA})


class IsTreatmentEditor(permissions.BasePermission):
    """
    Only Veterinarian/Admin may create/update/delete treatments/vaccinations; QA may read.
    """

    message = "Only Veterinarian or Admin may modify treatments/vaccinations."

    def has_permission(self, request, view):
        u = request.user
        if not u or not u.is_authenticated:
            return False
        if u.is_superuser:
            return True
        p = getattr(u, 'profile', None)
        if not p:
            return False
        if request.method in permissions.SAFE_METHODS:
            return p.role in {Role.ADMIN, Role.VETERINARIAN, Role.QA}
        return p.role in {Role.ADMIN, Role.VETERINARIAN}
```

### 3. Example ViewSet Implementation

```python
# apps/health/api/viewsets/journal_entry.py
from rest_framework import viewsets, permissions
from aquamind.api.mixins import RBACFilterMixin
from apps.health.api.permissions import IsHealthContributor
from apps.health.models import JournalEntry
from apps.health.api.serializers import JournalEntrySerializer

class JournalEntryViewSet(RBACFilterMixin, viewsets.ModelViewSet):
    """
    API endpoint for health journal entries.
    
    - Veterinarians: Full access to entries in their geography
    - QA: Read-only access to entries in their geography
    - Operators: No access (unless also QA)
    """
    serializer_class = JournalEntrySerializer
    permission_classes = [permissions.IsAuthenticated, IsHealthContributor]
    
    # Geographic filtering through batch → container → area → geography
    geography_filter_field = 'batch__batchcontainerassignment__container__area__geography'
    
    # No direct subsidiary field, but could be derived from batch lifecycle stage
    
    def get_queryset(self):
        # Base queryset with optimizations
        queryset = JournalEntry.objects.select_related(
            'batch',
            'container',
            'user'
        ).prefetch_related(
            'batch__batchcontainerassignment_set__container__area'
        )
        
        # Apply RBAC filters from mixin
        return self.apply_rbac_filters(queryset)
```

---

## Testing Strategy

### Security Test Suite

```python
# apps/users/tests/test_rbac.py
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from apps.users.models import User, Geography, Subsidiary, Role
from apps.batch.models import Batch
from apps.infrastructure.models import Area, Container

class RBACSecurityTests(TestCase):
    """
    Comprehensive RBAC security tests ensuring data isolation.
    """
    
    def setUp(self):
        # Create Scottish user
        self.scottish_user = User.objects.create_user(
            username='scottish_operator',
            password='pass123'
        )
        self.scottish_user.profile.geography = Geography.SCOTLAND
        self.scottish_user.profile.subsidiary = Subsidiary.FARMING
        self.scottish_user.profile.role = Role.OPERATOR
        self.scottish_user.profile.save()
        
        # Create Faroese user
        self.faroese_user = User.objects.create_user(
            username='faroese_operator',
            password='pass123'
        )
        self.faroese_user.profile.geography = Geography.FAROE_ISLANDS
        self.faroese_user.profile.subsidiary = Subsidiary.FARMING
        self.faroese_user.profile.role = Role.OPERATOR
        self.faroese_user.profile.save()
        
        # Create Scottish and Faroese data
        # ... (create areas, containers, batches)
        
        self.client = APIClient()
    
    def test_scottish_user_cannot_see_faroese_batches(self):
        """Ensure geographic data isolation."""
        self.client.force_authenticate(user=self.scottish_user)
        response = self.client.get('/api/v1/batch/batches/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify only Scottish batches are returned
        batch_ids = [b['id'] for b in response.data['results']]
        self.assertIn(self.scottish_batch.id, batch_ids)
        self.assertNotIn(self.faroese_batch.id, batch_ids)
    
    def test_operator_cannot_access_health_data(self):
        """Ensure role-based access control."""
        self.client.force_authenticate(user=self.scottish_user)
        response = self.client.get('/api/v1/health/journal-entries/')
        
        # Should be denied (403 Forbidden)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_veterinarian_can_access_health_data_in_geography(self):
        """Ensure veterinarians have appropriate access."""
        vet_user = User.objects.create_user(
            username='scottish_vet',
            password='pass123'
        )
        vet_user.profile.geography = Geography.SCOTLAND
        vet_user.profile.role = Role.VETERINARIAN
        vet_user.profile.save()
        
        self.client.force_authenticate(user=vet_user)
        response = self.client.get('/api/v1/health/journal-entries/')
        
        # Should be allowed
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should only see Scottish entries
        # ... assertions
```

---

## Migration Path

### Step-by-Step Implementation

1. **Week 1: Foundation**
   - Create `RBACFilterMixin`
   - Create permission classes (`IsVeterinarian`, `IsQA`, `IsOperator`)
   - Write comprehensive test suite

2. **Week 2: Health App**
   - Apply permissions to all health ViewSets
   - Apply geographic filtering
   - Test thoroughly

3. **Week 3: Batch & Inventory Apps**
   - Apply geographic/subsidiary filtering
   - Apply operator permissions
   - Test thoroughly

4. **Week 4: Infrastructure & Other Apps**
   - Complete RBAC implementation across all apps
   - Integration testing
   - Performance testing

5. **Week 5: Operator Location Assignment**
   - Add M2M fields on `UserProfile` (`allowed_areas`, `allowed_stations`, `allowed_containers`) or introduce an assignment model if per-link metadata is required
   - Migrate existing users
   - Implement fine-grained filtering

6. **Week 6: Testing & Documentation**
   - Complete security audit
   - Update documentation
   - User acceptance testing

---

## Conclusion

AquaMind has a **solid RBAC foundation** but requires **significant implementation work** to meet the security requirements outlined in the PRD and personas. The good news is that the data model is correct, authentication is working, and privilege escalation is prevented. The main work is:

1. **Geographic/subsidiary filtering** - Most critical, moderate effort
2. **Role-based permission classes** - High impact, low effort
3. **Operator location restrictions** - Important for UX, higher effort
4. **Consistent enforcement** - Apply patterns across all ViewSets

**Estimated Effort:** 6-8 weeks for full RBAC implementation with testing.

**Risk Level:** **MEDIUM** - Current system allows unauthorized data access but has no active exploits. Priority should be fixing geographic/subsidiary isolation first, then role-based permissions.

---

## Next Steps

1. **Immediate (This Week):**
   - Review this assessment with product owner
   - Prioritize which gaps to address first
   - Get approval for data model changes (if needed)

2. **Short Term (Next 2-4 Weeks):**
   - Implement Phase 1 (Geographic filtering + Role permissions)
   - Deploy to development environment
   - Test with real user scenarios

3. **Medium Term (1-2 Months):**
   - Implement Phase 2 (Operator location assignment)
   - Complete all RBAC features
   - Security audit
   - Production deployment

4. **Ongoing:**
   - Monitor RBAC violations in logs
   - Regular security reviews
   - Update as requirements evolve
