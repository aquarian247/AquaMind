# Agent Task Prompt Template

Use this template when assigning code review remediation tasks to AI agents. Each agent should tackle **one task** per session.

---

## 📋 Standard Prompt Format

```
You are working on the AquaMind aquaculture management system (Django backend + React frontend).

TASK: [Task Number and Title from REMEDIATION_PLAN.md]

CONTEXT:
- Review: Code review findings verified against PostgreSQL database (October 3, 2025)
- Documentation: /Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/code_review_findings/
- Your task details: REMEDIATION_PLAN.md, Task [NUMBER]

OBJECTIVE:
Implement the fix described in Task [NUMBER] following the exact specifications in the remediation plan.

REQUIREMENTS:
1. Read the full task specification in REMEDIATION_PLAN.md
2. Implement all backend changes listed
3. [If applicable] Consider frontend impact and document any breaking changes
4. Write/update tests as specified
5. Follow the coding guidelines in /.cursorrules
6. Verify the fix works by running the test commands provided
7. [If migration task] Follow the Database Migration Guide section
8. [If breaking API] Follow the API Versioning Strategy section
9. Create a clear commit message following the format below

TESTING:
Run these commands to verify your fix:
[Copy test commands from the task]

COMMIT FORMAT:
fix(app-name): [brief description of fix]

Fixes code review finding Task [NUMBER]: [issue description]

- [Change 1]
- [Change 2]
- [Change 3]

Closes: Task [NUMBER]

DO NOT:
- Skip tests
- Make changes beyond the scope of this task
- Modify unrelated code
- Skip the rollback procedure documentation if this is a critical task

SUCCESS CRITERIA:
✅ All changes from task specification implemented
✅ Tests pass (unit, integration, manual verification)
✅ No new linter errors introduced
✅ [If applicable] Frontend impact documented
✅ Commit message follows format
✅ Changes ready for code review
```

---

## 🎯 Task-Specific Prompt Examples

### Example 1: P0-1 (Security - Users Privilege Escalation)

```
You are working on the AquaMind aquaculture management system (Django backend + React frontend).

TASK: Task 1 - Fix Users App Privilege Escalation Vulnerability

CONTEXT:
- Review: Code review findings verified against PostgreSQL database (October 3, 2025)
- Documentation: /Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/code_review_findings/
- Your task details: REMEDIATION_PLAN.md, Task 1
- CRITICAL: This is a security vulnerability (P0 priority)

OBJECTIVE:
Fix the privilege escalation vulnerability where users can modify their own role to become admin.

REQUIREMENTS:
1. Read Task 1 in REMEDIATION_PLAN.md
2. Remove role, geography, subsidiary from UserProfileUpdateSerializer.Meta.fields
3. Add server-side enforcement in UserSerializer.update() to ignore RBAC fields
4. Create UserProfileAdminUpdateSerializer for admin-only updates
5. Add validation tests ensuring non-admin users cannot modify RBAC fields
6. Update UserProfileView to use read-only serializer for GET requests
7. Follow the API Versioning Strategy (Phased Deprecation) for this breaking change
8. Document rollback procedure per Task 1 Rollback section

TESTING:
Run these commands to verify your fix:
```bash
# Test that regular users cannot escalate privileges
python manage.py test apps.users.tests

# Manual verification
curl -X PATCH http://localhost:8000/api/v1/users/profile/ \
  -H "Authorization: Bearer $USER_TOKEN" \
  -d '{"role": "ADMIN"}' 
# Should fail with validation error

# Admin should be able to update roles via new endpoint
curl -X PATCH http://localhost:8000/api/v1/users/1/admin-update/ \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"role": "ADMIN"}'
# Should succeed for admin users only
```

FRONTEND IMPACT:
🔴 BREAKING CHANGES REQUIRED
- Remove role, geography, subsidiary fields from profile edit forms
- Create admin-only user management interface for RBAC changes
- Update TypeScript types to remove RBAC fields from UserProfileUpdateDTO
- Coordinate deployment with frontend team

COMMIT FORMAT:
fix(users): prevent privilege escalation via profile update

Fixes code review finding Task 1: Users can modify their own role

- Remove role/geography/subsidiary from UserProfileUpdateSerializer
- Add server-side enforcement in UserSerializer.update()
- Create UserProfileAdminUpdateSerializer for admin-only updates
- Add validation tests for RBAC field protection
- Implement phased deprecation with warnings

Breaking Change: PUT/PATCH /api/v1/users/profile/ now rejects RBAC fields
Migration Guide: See REMEDIATION_PLAN.md API Versioning Strategy

Closes: Task 1

DO NOT:
- Skip the phased deprecation approach (required for production safety)
- Skip the rollback procedure documentation
- Deploy without coordinating with frontend team

SUCCESS CRITERIA:
✅ UserProfileUpdateSerializer no longer exposes RBAC fields
✅ Tests verify non-admin users cannot modify role/geography/subsidiary
✅ Admin endpoint created and tested
✅ Phased deprecation warnings implemented
✅ Frontend team notified of breaking change
✅ Rollback procedure tested in dev environment
```

---

### Example 2: P0-2 (MortalityRecord TypeError)

```
You are working on the AquaMind aquaculture management system (Django backend + React frontend).

TASK: Task 2 - Fix MortalityRecord UserAssignmentMixin Conflict

CONTEXT:
- Review: Code review findings verified against PostgreSQL database
- Your task details: REMEDIATION_PLAN.md, Task 2
- Database verification: health_mortalityrecord table has NO user_id column
- Issue: UserAssignmentMixin tries to set user field that doesn't exist

OBJECTIVE:
Fix the TypeError that occurs when creating mortality records due to UserAssignmentMixin incompatibility.

REQUIREMENTS:
1. Read Task 2 in REMEDIATION_PLAN.md
2. Remove UserAssignmentMixin from MortalityRecordViewSet
3. Remove filter overrides for mortality_date and recorded_by (fields don't exist)
4. Update filterset_fields to: ['event_date', 'batch', 'container', 'reason']
5. Add integration tests for POST and filtered GET requests
6. Follow API Versioning Strategy for filter parameter changes

TESTING:
```bash
# Unit tests
python manage.py test apps.health.tests.test_api

# Manual verification - Create mortality record
curl -X POST http://localhost:8000/api/v1/health/mortality-records/ \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"batch": 1, "count": 5, "reason": 1, "event_date": "2025-10-03T10:00:00Z"}'
# Should succeed (currently fails with TypeError)

# Test filtering with correct field names
curl -X GET "http://localhost:8000/api/v1/health/mortality-records/?event_date__gte=2025-10-01" \
  -H "Authorization: Bearer $TOKEN"
# Should return results

# Test old filter param with deprecation
curl -X GET "http://localhost:8000/api/v1/health/mortality-records/?mortality_date=2025-10-01" \
  -H "Authorization: Bearer $TOKEN"
# Should work during transition phase with warning header
```

FRONTEND IMPACT:
🟡 MINOR CHANGES REQUIRED
- If frontend filters by mortality_date, change to event_date
- If frontend filters by recorded_by, remove that filter (field doesn't exist)
- Update mortality list table columns if using wrong field names

COMMIT FORMAT:
fix(health): remove incompatible UserAssignmentMixin from MortalityRecord

Fixes code review finding Task 2: MortalityRecord creation fails with TypeError

- Remove UserAssignmentMixin from MortalityRecordViewSet
- Update filterset_fields to match actual model fields
- Remove filters for non-existent mortality_date and recorded_by
- Add integration tests for create and filter operations
- Implement filter parameter deprecation mapping

Breaking Change: Filter parameter mortality_date renamed to event_date
Migration Guide: See REMEDIATION_PLAN.md section for filter mapping

Closes: Task 2

SUCCESS CRITERIA:
✅ MortalityRecord POST requests succeed
✅ Filters use correct field names (event_date, not mortality_date)
✅ Integration tests pass
✅ Filter parameter deprecation implemented
✅ Frontend team notified of filter changes
```

---

### Example 3: P0-4 (Broodstock timedelta - Simple Fix)

```
You are working on the AquaMind aquaculture management system (Django backend + React frontend).

TASK: Task 4 - Fix Broodstock Service timezone.timedelta Error

CONTEXT:
- Your task details: REMEDIATION_PLAN.md, Task 4
- Issue: Using timezone.timedelta which doesn't exist (AttributeError)
- Simple fix: Import timedelta from datetime module

OBJECTIVE:
Fix the AttributeError in broodstock service container statistics and maintenance checks.

REQUIREMENTS:
1. Read Task 4 in REMEDIATION_PLAN.md
2. Add 'from datetime import timedelta' at top of apps/broodstock/services/broodstock_service.py
3. Line 324: Change timezone.timedelta(days=30) to timedelta(days=30)
4. Line 444: Change timezone.timedelta(days=7) to timedelta(days=7)
5. Run existing tests to verify fix

TESTING:
```bash
# Run service tests
pytest apps/broodstock/tests/test_services.py::BroodstockServiceTestCase::test_get_container_statistics

# Full broodstock test suite
python manage.py test apps.broodstock
```

FRONTEND IMPACT:
🟢 NO CHANGES NEEDED
- Internal service method fix
- No API contract changes

COMMIT FORMAT:
fix(broodstock): use datetime.timedelta instead of timezone.timedelta

Fixes code review finding Task 4: AttributeError in container statistics

- Import timedelta from datetime module
- Fix line 324: get_container_statistics movement date filter
- Fix line 444: check_container_maintenance_due scheduled date filter
- Existing tests now pass

Closes: Task 4

SUCCESS CRITERIA:
✅ Import statement added
✅ Both timedelta references fixed
✅ Tests pass without AttributeError
✅ No linter errors introduced
```

---

## 🔧 Migration Task Template (Tasks 3, 6)

```
You are working on the AquaMind aquaculture management system (Django backend + React frontend).

TASK: Task [NUMBER] - [Title with Migration]

CONTEXT:
- Your task details: REMEDIATION_PLAN.md, Task [NUMBER]
- Migration Guide: See "Database Migration Guide" section in REMEDIATION_PLAN.md
- ⚠️ This task requires database migration

OBJECTIVE:
[Objective from task]

REQUIREMENTS:
1. Read Task [NUMBER] and Database Migration Guide in REMEDIATION_PLAN.md
2. Follow Pre-Migration Checklist (7 steps)
3. Create migration file as specified in the guide
4. Test migration in dev/staging following testing procedure
5. Test rollback procedure
6. Document any data integrity concerns
7. Prepare production execution plan

TESTING:
```bash
# Pre-migration checklist from REMEDIATION_PLAN.md
[Copy commands from migration guide]

# Test migration
python manage.py migrate [app] [migration_number] --plan
python manage.py migrate [app] [migration_number]

# Verify schema
python manage.py dbshell
\d [table_name]

# Test rollback
python manage.py migrate [app] [previous_migration]

# Verify rollback
\d [table_name]

# Re-apply for deployment
python manage.py migrate [app] [migration_number]
```

ROLLBACK PROCEDURE:
Follow Task [NUMBER] Rollback Procedure in REMEDIATION_PLAN.md exactly.
Test rollback before marking task complete.

COMMIT FORMAT:
feat(app): add database migration for [description]

Fixes code review finding Task [NUMBER]: [issue]

- Create migration to [add/alter] [columns/fields]
- Add model field definitions
- Update serializers to match new schema
- Test migration in dev environment
- Document rollback procedure
- Verify data integrity post-migration

Migration: [app].migrations.[XXXX_migration_name]

Closes: Task [NUMBER]

SUCCESS CRITERIA:
✅ Migration created and tested
✅ Rollback tested and documented
✅ Schema changes verified in database
✅ Data integrity maintained
✅ Serializers updated to match schema
✅ Production execution plan prepared
```

---

## 📚 Quick Reference for Agents

### Before Starting Any Task

1. **Read these documents**:
   - `REMEDIATION_PLAN.md` - Full task specification
   - `CRITICAL_ISSUES_QUICK_REF.md` - If it's a P0 task
   - `README.md` - For coordination guidelines

2. **Check task dependencies**:
   - Some tasks depend on others (noted in plan)
   - Coordinate with team if dependencies exist

3. **Verify database state**:
   ```bash
   # Check current schema
   python manage.py dbshell
   \d [table_name]
   ```

### During Implementation

1. **Follow the task specification exactly** - Don't deviate
2. **Run tests frequently** - Catch issues early
3. **Check linter** - `read_lints` before committing
4. **Document breaking changes** - Clearly note frontend impacts

### After Completing Task

1. **Run all tests**:
   ```bash
   python manage.py test apps.[app_name]
   pytest apps.[app_name]  # If pytest used
   ```

2. **Verify no regressions**:
   ```bash
   # Test related functionality
   curl [relevant endpoints]
   ```

3. **Document changes**:
   - Update task status in README.md
   - Note any deviations from plan
   - Document frontend coordination needs

4. **Commit with standard format** - See examples above

---

## ⚠️ Common Pitfalls to Avoid

1. **Don't skip tests** - Every task requires test verification
2. **Don't touch unrelated code** - Stay focused on the task
3. **Don't skip API versioning** - Breaking changes need deprecation period
4. **Don't skip rollback docs** - Critical tasks need rollback procedures
5. **Don't forget frontend** - Check frontend impact section
6. **Don't commit without linting** - Check for errors first
7. **Don't merge without review** - All changes need human review

---

## 🎯 Success Metrics

Each task should achieve:
- ✅ **100% of requirements** implemented
- ✅ **All tests passing** (unit + integration)
- ✅ **Zero new linter errors**
- ✅ **Frontend impact** documented if applicable
- ✅ **Clear commit message** following format
- ✅ **Ready for code review** by human developer

---

## 📞 When to Ask for Help

Ask the human developer if:
- Task specification is unclear or contradictory
- You discover additional issues not mentioned in the task
- Database state doesn't match expectations
- Tests fail in unexpected ways
- Frontend coordination is required immediately
- Rollback procedure needs to be tested in staging
- Migration will take longer than expected

---

## 🔄 Handoff Between Agents

When completing a task, document:
1. What was implemented (list all changes)
2. Any deviations from the plan (with justification)
3. Test results (all pass? any failures?)
4. Frontend coordination status (notified? changes made?)
5. Next recommended task (if any dependencies cleared)

This helps the next agent pick up smoothly.

---

**Last Updated**: 2025-10-03  
**For Questions**: Refer to REMEDIATION_PLAN.md or ask the human developer

