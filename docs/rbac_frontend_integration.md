# RBAC Frontend Integration Guide

**Date:** 2025-11-02  
**Status:** Implementation Guide  
**Related Docs:** `docs/rbac_assessment.md`, `docs/phase2_operator_location_assignment.md`

---

## Overview

This document outlines frontend integration requirements for the RBAC implementation (Phases 1 & 2). The backend provides complete RBAC enforcement at the API level, but the frontend should adapt to provide optimal UX based on user permissions and assignments.

---

## 1. API Client Regeneration ✅ REQUIRED

### TypeScript Client Generation

**Why**: New endpoints, changed response structures, and RBAC-related fields require updated TypeScript clients.

**Action Required**:
```bash
# Regenerate OpenAPI schema
python manage.py spectacular --file schema.yml

# Generate TypeScript client (if using openapi-generator)
npx openapi-generator-cli generate \
  -i schema.yml \
  -g typescript-axios \
  -o frontend/src/api/generated

# Or if using Orval
npx orval --config orval.config.js
```

**What's New in Schema**:
- UserProfile fields: `allowed_areas`, `allowed_stations`, `allowed_containers`
- History endpoints: `/api/v1/{app}/history/{model}/`
- Enhanced error responses with 403 Forbidden details
- RBAC filter parameters (implicit - no schema changes)

### API Response Changes

**User Profile Endpoint** (`/api/v1/users/profile/me/`):
```typescript
interface UserProfile {
  id: number;
  user: number;
  geography: 'SC' | 'FO' | 'ALL';
  subsidiary: 'BS' | 'FW' | 'FM' | 'LG' | 'ALL';
  role: 'ADMIN' | 'MGR' | 'OPR' | 'VET' | 'QA' | 'FIN' | 'VIEW';
  
  // NEW: Phase 2 fields
  allowed_areas: number[];        // Array of Area IDs
  allowed_stations: number[];     // Array of FreshwaterStation IDs
  allowed_containers: number[];   // Array of Container IDs
}
```

**List Endpoints** (No schema change, but behavior changes):
- Batches, containers, feeding events automatically filtered server-side
- Frontend receives ONLY authorized data (no client-side filtering needed)
- Empty arrays are valid responses for operators with no assignments

---

## 2. User Context Management 🔧 RECOMMENDED

### Store User Profile Globally

**React Context Example**:
```typescript
// contexts/UserContext.tsx
interface UserContextType {
  profile: UserProfile | null;
  isOperator: boolean;
  isManager: boolean;
  isVeterinarian: boolean;
  isQA: boolean;
  hasHealthAccess: boolean;
  hasOperationalAccess: boolean;
  hasLocationAssignments: boolean;
}

export const UserProvider: React.FC = ({ children }) => {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  
  const hasHealthAccess = useMemo(() => 
    profile?.role in ['ADMIN', 'VET', 'QA'], 
    [profile]
  );
  
  const hasLocationAssignments = useMemo(() =>
    profile?.allowed_areas.length > 0 ||
    profile?.allowed_stations.length > 0 ||
    profile?.allowed_containers.length > 0,
    [profile]
  );
  
  // ... fetch profile on mount
  
  return (
    <UserContext.Provider value={{ 
      profile, 
      hasHealthAccess, 
      hasLocationAssignments,
      // ...
    }}>
      {children}
    </UserContext.Provider>
  );
};
```

---

## 3. Permission-Based UI 🎨 RECOMMENDED

### Hide/Show Components Based on Role

**Example: Health Tab Visibility**:
```typescript
// components/Navigation.tsx
import { useUser } from '@/contexts/UserContext';

export const Navigation: React.FC = () => {
  const { hasHealthAccess } = useUser();
  
  return (
    <nav>
      <NavLink to="/batches">Batches</NavLink>
      <NavLink to="/feeding">Feeding</NavLink>
      
      {/* Only show for VET/QA/Admin */}
      {hasHealthAccess && (
        <NavLink to="/health">Health</NavLink>
      )}
    </nav>
  );
};
```

**Example: Treatment Edit Button**:
```typescript
// components/TreatmentList.tsx
export const TreatmentList: React.FC = () => {
  const { profile } = useUser();
  const canEditTreatments = profile?.role in ['ADMIN', 'VET'];
  
  return (
    <div>
      <TreatmentTable data={treatments} />
      
      {canEditTreatments && (
        <Button onClick={openCreateModal}>
          Add Treatment
        </Button>
      )}
    </div>
  );
};
```

### Role-Based UI Rules

| Feature | Visible To | Editable By |
|---------|-----------|-------------|
| Batch Management | OPERATOR, MANAGER, ADMIN | OPERATOR, MANAGER, ADMIN |
| Feeding Events | OPERATOR, MANAGER, ADMIN | OPERATOR, MANAGER, ADMIN |
| Health Journal | VET, QA, ADMIN | VET, QA, ADMIN |
| Treatments | VET, QA, ADMIN | VET, ADMIN only |
| Finance | FINANCE, ADMIN | FINANCE, ADMIN |

---

## 4. Empty State Handling ⚠️ REQUIRED

### Operators with No Location Assignments

**Problem**: Operator with no `allowed_areas`, `allowed_stations`, or `allowed_containers` will see empty lists for batches, feeding events, etc.

**Solution**: Show helpful empty state messages.

```typescript
// components/BatchList.tsx
import { useUser } from '@/contexts/UserContext';

export const BatchList: React.FC = () => {
  const { profile, isOperator, hasLocationAssignments } = useUser();
  const { data: batches, isLoading } = useQuery('batches', fetchBatches);
  
  if (isLoading) return <Spinner />;
  
  // Special handling for operators with no assignments
  if (isOperator && !hasLocationAssignments && batches.length === 0) {
    return (
      <EmptyState
        icon={<MapPinIcon />}
        title="No Location Assignments"
        description="You don't have any assigned areas, stations, or containers. Contact your manager to get location access."
        action={
          <Button onClick={() => window.open('/admin/users/userprofile/')}>
            Contact Administrator
          </Button>
        }
      />
    );
  }
  
  // Standard empty state (no batches exist)
  if (batches.length === 0) {
    return (
      <EmptyState
        title="No Batches Found"
        description="Create your first batch to get started."
        action={<Button onClick={openCreateModal}>Create Batch</Button>}
      />
    );
  }
  
  return <BatchTable data={batches} />;
};
```

---

## 5. Error Handling 🚨 RECOMMENDED

### Better 403 Forbidden Messages

**Before**:
```typescript
// Generic error
if (error.status === 403) {
  toast.error("Access denied");
}
```

**After**:
```typescript
// Role-specific messages
if (error.status === 403) {
  const message = error.response?.data?.detail || "Access denied";
  
  if (message.includes("Health data")) {
    toast.error("Health data access requires Veterinarian or QA role. Contact your administrator.");
  } else if (message.includes("Veterinarian")) {
    toast.error("Only Veterinarians can modify treatments. You have read-only access.");
  } else if (message.includes("geography")) {
    toast.error("This data is outside your geography. You only have access to your region's data.");
  } else {
    toast.error(message);
  }
}
```

---

## 6. Location Assignment Display 📍 OPTIONAL

### Show Operator's Assigned Locations

**User Profile Page**:
```typescript
// components/UserProfile.tsx
export const UserProfile: React.FC = () => {
  const { profile } = useUser();
  const { data: areas } = useQuery(
    ['areas', profile?.allowed_areas],
    () => fetchAreasByIds(profile?.allowed_areas || []),
    { enabled: !!profile?.allowed_areas?.length }
  );
  
  return (
    <div>
      <h2>{profile?.user.username}</h2>
      <p>Role: {profile?.role}</p>
      <p>Geography: {profile?.geography}</p>
      
      {profile?.role === 'OPR' && (
        <div>
          <h3>Your Assigned Locations</h3>
          {areas?.length > 0 ? (
            <ul>
              {areas.map(area => (
                <li key={area.id}>{area.name}</li>
              ))}
            </ul>
          ) : (
            <p>No locations assigned. Contact your manager.</p>
          )}
        </div>
      )}
    </div>
  );
};
```

---

## 7. Data Fetching Patterns ✅ NO CHANGES NEEDED

### Server-Side Filtering (Already Handled)

**Good News**: No changes needed to data fetching logic!

```typescript
// This code stays the same - server handles filtering
const { data: batches } = useQuery('batches', () => 
  api.batches.list()  // Automatically filtered by user's geography + location
);
```

**What Happens Behind the Scenes**:
1. User requests `/api/v1/batch/batches/`
2. Backend checks user's geography → filters queryset
3. Backend checks if user is operator with location filtering enabled → further filters
4. Frontend receives ONLY authorized batches

**No Frontend Filtering Required**:
```typescript
// ❌ DON'T DO THIS (unnecessary)
const filteredBatches = batches.filter(batch => 
  userProfile.allowed_areas.includes(batch.area_id)
);

// ✅ DO THIS (trust backend filtering)
const batches = await api.batches.list();  // Already filtered
```

---

## 8. Admin Interface Integration 🔧 OPTIONAL

### Custom React Admin for Location Assignment

If you have a custom React admin (not using Django admin):

```typescript
// components/admin/UserLocationAssignment.tsx
import { TransferList } from '@/components/ui/TransferList';

export const UserLocationAssignment: React.FC<{ userId: number }> = ({ userId }) => {
  const { data: profile } = useQuery(['userProfile', userId], () => 
    api.users.getProfile(userId)
  );
  const { data: allAreas } = useQuery('areas', api.areas.list);
  
  const handleAssignAreas = async (areaIds: number[]) => {
    await api.users.updateProfile(userId, {
      allowed_areas: areaIds
    });
    toast.success('Location assignments updated');
  };
  
  return (
    <div>
      <h3>Assigned Areas</h3>
      <TransferList
        available={allAreas}
        selected={profile?.allowed_areas || []}
        onChange={handleAssignAreas}
        renderItem={area => area.name}
      />
    </div>
  );
};
```

**Note**: If using Django admin (recommended), no custom UI needed - admin interface is already implemented in Phase 2.

---

## 9. Testing Checklist ✅

### Frontend RBAC Testing

**User Context Tests**:
- [ ] User profile loads on app mount
- [ ] Role-based permissions computed correctly
- [ ] Location assignments reflected in context

**UI Visibility Tests**:
- [ ] Health tab hidden for operators
- [ ] Treatment edit button hidden for QA users
- [ ] Operational tabs visible to operators/managers

**Empty State Tests**:
- [ ] Operator with no assignments sees helpful message
- [ ] Standard empty state for other users
- [ ] "Contact administrator" action works

**Error Handling Tests**:
- [ ] 403 errors show role-specific messages
- [ ] Health access denied shows correct message
- [ ] Geography restriction shows correct message

**Data Fetching Tests**:
- [ ] Scottish user only sees Scottish batches
- [ ] Operator sees only assigned area batches
- [ ] Manager sees all areas in geography

---

## 10. Implementation Priority

### Must-Have (Deploy Blockers)

1. **API Client Regeneration** ✅ CRITICAL
   - Without this, frontend won't know about new fields
   - Generate TypeScript clients from updated OpenAPI schema

2. **Empty State Handling** ⚠️ IMPORTANT
   - Operators with no assignments will be confused
   - Implement helpful empty states with admin contact info

3. **Error Message Improvements** 🚨 RECOMMENDED
   - Better 403 messages help users understand RBAC

### Nice-to-Have (Post-MVP)

4. **Permission-Based UI** 🎨 UX IMPROVEMENT
   - Hiding unauthorized features improves UX
   - Prevents confusion and wasted API calls

5. **User Context Management** 🔧 ARCHITECTURE
   - Cleaner code, easier to maintain
   - Avoids prop drilling

6. **Location Assignment Display** 📍 OPTIONAL
   - Helps operators know their assigned areas
   - Low priority if Django admin is primary interface

---

## 11. Migration Path

### Step 1: Backend Deployment (Already Done)
- ✅ RBAC enforcement active
- ✅ Geographic filtering operational
- ✅ Operator location filtering enabled

### Step 2: Frontend Compatibility (Immediate)
```bash
# Regenerate API clients
npm run generate:api

# Test with existing frontend (should work - backward compatible)
npm run dev
```

### Step 3: Frontend Enhancements (Iterative)
1. **Week 1**: Empty state improvements
2. **Week 2**: Error message enhancements
3. **Week 3**: Permission-based UI hiding
4. **Week 4**: User context refactoring

### Step 4: User Training
- Document new RBAC behavior
- Train administrators on location assignment
- Communicate role-based access to users

---

## 12. Backward Compatibility ✅

**Good News**: Frontend will continue to work without changes!

**Why**:
- Backend returns filtered data (frontend doesn't need to change queries)
- New UserProfile fields are optional (existing code won't break)
- 403 errors already handled (just not with helpful messages)

**Graceful Degradation**:
- Old frontend + new backend = ✅ Works (data filtered server-side)
- New frontend + old backend = ❌ Fails (new fields missing) - avoid this

**Deployment Strategy**:
1. Deploy backend RBAC (done)
2. Test with existing frontend (should work)
3. Deploy frontend enhancements iteratively

---

## 13. Common Pitfalls ⚠️

### Don't Try to Bypass Backend Filtering
```typescript
// ❌ BAD: Trying to fetch "all" batches
const batches = await api.batches.list({ bypassFilters: true });
// This won't work - backend enforces RBAC

// ✅ GOOD: Trust backend filtering
const batches = await api.batches.list();
```

### Don't Implement Client-Side Permission Logic
```typescript
// ❌ BAD: Reimplementing RBAC on frontend
if (userRole === 'OPERATOR' && batch.geography !== userGeography) {
  return null;  // Hide batch
}

// ✅ GOOD: Backend already did this
// Just render what you receive
```

### Don't Cache Filtered Data Globally
```typescript
// ❌ BAD: Caching across users
localStorage.setItem('allBatches', JSON.stringify(batches));

// ✅ GOOD: User-specific cache keys
queryClient.setQueryData(['batches', userId], batches);
```

---

## 14. Summary

### What Frontend MUST Do
1. ✅ Regenerate API clients from updated OpenAPI schema
2. ⚠️ Handle empty states for operators with no assignments
3. 🚨 Improve 403 error messages

### What Frontend SHOULD Do
4. 🎨 Hide unauthorized UI elements based on role
5. 🔧 Add user context for permission checking

### What Frontend DOESN'T Need to Do
- ❌ Filter data client-side (backend handles it)
- ❌ Implement RBAC logic (backend enforces it)
- ❌ Validate geography/location access (backend does it)

### Key Principle
**Trust the Backend**: The backend provides complete RBAC enforcement. The frontend's job is to provide good UX around that enforcement, not to re-implement it.

---

## 15. Support

**Questions**:
- Backend RBAC: See `docs/rbac_assessment.md`
- Phase 2 Details: See `docs/phase2_operator_location_assignment.md`
- API Schema: `GET /api/schema/` or `/api/schema/swagger-ui/`

**Testing Users** (for development):
```python
# Create test users with different RBAC profiles
python manage.py create_rbac_test_users
```
