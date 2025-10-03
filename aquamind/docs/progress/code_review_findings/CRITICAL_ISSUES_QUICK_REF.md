# 🚨 Critical Issues - Quick Reference Card

**IMMEDIATE ACTION REQUIRED** - These issues are verified and will cause production failures or security breaches.

---

## 🔴 P0-1: Security Vulnerability (FIX IMMEDIATELY)

### Issue: Users Can Escalate Their Own Privileges
**File**: `apps/users/serializers.py` (line 212)  
**Database Verified**: ✅ role, geography, subsidiary columns ARE writable

**Problem**:
```python
# UserProfileUpdateSerializer - allows users to set their own role!
class Meta:
    fields = ['full_name', 'phone', 'profile_picture', 'job_title', 'department',
             'geography', 'subsidiary', 'role', ...]  # ← DANGER!
```

**Impact**: Any authenticated user can make themselves an admin.

**Quick Fix**:
```python
# Remove role, geography, subsidiary from fields list
class Meta:
    fields = ['full_name', 'phone', 'profile_picture', 'job_title', 'department',
             'language_preference', 'date_format_preference']
    read_only_fields = ['created_at', 'updated_at']
```

**Test**:
```bash
# Try to escalate privilege (should fail after fix)
curl -X PATCH http://localhost:8000/api/v1/users/profile/ \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"role": "ADMIN"}'
```

**Frontend**: Remove role/geography/subsidiary from profile edit forms.

---

## 🔴 P0-2: MortalityRecord Creation Fails

### Issue: TypeError When Creating Mortality Records
**File**: `apps/health/api/viewsets/mortality.py` (line 48)  
**Database Verified**: ✅ No user_id column in health_mortalityrecord table

**Problem**:
```python
# Viewset inherits UserAssignmentMixin which tries to set user field
class MortalityRecordViewSet(UserAssignmentMixin, ...):  # ← Problem
    # But MortalityRecord model has no user field!
```

**Impact**: All POST requests to create mortality records return 500 error.

**Quick Fix**:
```python
# Remove UserAssignmentMixin
class MortalityRecordViewSet(OptimizedQuerysetMixin, 
                            StandardFilterMixin, viewsets.ModelViewSet):
    queryset = MortalityRecord.objects.all()
    serializer_class = MortalityRecordSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    # Fix filter fields
    filterset_fields = ['event_date', 'batch', 'container', 'reason']
```

**Test**:
```bash
# Should succeed after fix
curl -X POST http://localhost:8000/api/v1/health/mortality-records/ \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"batch": 1, "count": 5, "reason": 1, "event_date": "2025-10-03T10:00:00Z"}'
```

**Frontend**: Change filter from `mortality_date` to `event_date` if used.

---

## 🔴 P0-3: PhotoperiodData API Broken

### Issue: FieldError on All PhotoperiodData POST/PUT Requests
**File**: `apps/environmental/api/serializers.py` (lines 227-243)  
**Database Verified**: ✅ artificial_light_start, artificial_light_end, notes columns DO NOT EXIST

**Problem**:
```python
# Serializer defines fields that don't exist in database
class PhotoperiodDataSerializer(serializers.ModelSerializer):
    # ... other fields ...
    artificial_light_start = serializers.TimeField(...)  # ← Not in DB
    artificial_light_end = serializers.TimeField(...)    # ← Not in DB
    notes = serializers.CharField(...)                    # ← Not in DB
```

**Impact**: All attempts to create/update photoperiod data fail with FieldError.

**Quick Fix (Option A - Remove fields)**:
```python
# Remove the three non-existent fields from serializer
class PhotoperiodDataSerializer(serializers.ModelSerializer):
    # Remove artificial_light_start, artificial_light_end, notes
    
    class Meta:
        model = PhotoperiodData
        fields = ['id', 'area', 'date', 'day_length_hours', 
                 'light_intensity', 'is_interpolated', 'created_at', 'updated_at']
```

**Test**:
```bash
# Should succeed after fix
curl -X POST http://localhost:8000/api/v1/environmental/photoperiod-data/ \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"area": 1, "date": "2025-10-03", "day_length_hours": 12.5}'
```

**Frontend**: Remove artificial light time fields from photoperiod forms if present.

---

## 🔴 P0-4: Broodstock Service Crashes

### Issue: AttributeError in Container Statistics
**File**: `apps/broodstock/services/broodstock_service.py` (lines 324, 444)  
**Code Verified**: ✅ Uses timezone.timedelta which doesn't exist

**Problem**:
```python
# Line 324 & 444 - timezone doesn't have timedelta attribute
movement_date__gte=timezone.now() - timezone.timedelta(days=30)  # ← Wrong!
```

**Impact**: Container statistics and maintenance checks crash with AttributeError.

**Quick Fix**:
```python
# Add import at top
from datetime import timedelta

# Fix both lines
movement_date__gte=timezone.now() - timedelta(days=30)  # Line 324
scheduled_date__lte=timezone.now() + timedelta(days=7)  # Line 444
```

**Test**:
```bash
# Should succeed after fix
pytest apps/broodstock/tests/test_services.py::BroodstockServiceTestCase::test_get_container_statistics
```

**Frontend**: No changes needed (internal service method).

---

## 🟠 P1-1: Batch Analytics Broken

### Issue: AttributeError on Batch Performance Metrics
**Files**: Batch analytics mixins and filters  
**Database Verified**: ✅ batch table has NO population_count or biomass_kg columns

**Problem**:
```python
# Code references fields that don't exist on Batch model
batch.population_count  # ← AttributeError! 
batch.biomass_kg        # ← AttributeError!

# They're properties instead:
batch.calculated_population_count  # ← Correct
batch.calculated_biomass_kg        # ← Correct
```

**Impact**: Performance metrics, growth analysis, and batch comparison endpoints fail.

**Quick Fix**:
```python
# Search and replace in batch analytics code:
batch.population_count → batch.calculated_population_count
batch.biomass_kg → batch.calculated_biomass_kg
```

**Frontend**: Verify analytics dashboards still render after fix. Some filters may be removed.

---

## 📋 Quick Action Checklist

```
Priority 0 (This Week):
□ P0-1: Remove role/geography/subsidiary from UserProfileUpdateSerializer
□ P0-2: Remove UserAssignmentMixin from MortalityRecordViewSet
□ P0-3: Fix PhotoperiodDataSerializer fields
□ P0-4: Fix timezone.timedelta in broodstock service

Priority 1 (Next Week):
□ P1-1: Update batch analytics to use calculated_ properties
□ Fix EnvironmentalParameter precision mismatch
□ Fix Health app filtering issues
□ Fix Growth sample validation
```

---

## 🧪 Testing Commands

```bash
# Test security fix
python manage.py test apps.users.tests

# Test mortality records
python manage.py test apps.health.tests.test_api

# Test photoperiod data
python manage.py test apps.environmental.tests

# Test broodstock service
pytest apps/broodstock/tests/test_services.py

# Test batch analytics
python manage.py test apps.batch.tests.test_analytics

# Run all affected tests
python manage.py test apps.users apps.health apps.environmental apps.broodstock apps.batch
```

---

## 📞 Emergency Contacts

If these issues are in production:
1. **Security Issue (P0-1)**: Disable user profile update endpoint immediately
2. **Data Corruption Risk**: Review recent mortality records and batch transfers
3. **Monitor Logs**: Check for AttributeError, FieldError, TypeError patterns

---

## 🔗 Full Documentation

- [Complete Remediation Plan](./REMEDIATION_PLAN.md) - All 21 tasks with details
- [README](./README.md) - Overview and coordination guide
- Individual app reviews - Original findings with full context

---

**Created**: 2025-10-03  
**Status**: VERIFIED VIA DATABASE SCHEMA  
**Next Action**: Begin P0 fixes immediately

