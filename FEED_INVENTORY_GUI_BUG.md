# Feed Inventory GUI Bug

**Date:** 2025-11-13  
**Issue:** GUI shows incorrect feed stock totals

---

## The Problem

**GUI Display:**
- Total Feed Stock: 1.9kg ❌
- Total Inventory Value: $4,373,036 ✅ (partially correct)

**Actual Database:**
- Total Feed Stock: 3,728,805 kg (3,729 tonnes) ✅
- Total Inventory Value: $7,785,102 ✅
- Stock Entries: 29,082

---

## Root Cause

**Frontend code** (`client/src/pages/inventory.tsx` line 430):
```javascript
const totalFeedStock = containerStock.reduce(
  (sum, s) => sum + parseFloat(s.quantity_kg), 
  0
);
```

**Problem:** `containerStock` only contains **page 1** (100 records) of 29,082 total records!

**API Response:**
```json
{
  "count": 29082,
  "next": "http://localhost:8000/api/v1/inventory/feed-container-stock/?page=2",
  "results": [/* only 100 items */]
}
```

**Result:** Sum of 100 items ≈ 1.9kg (wrong!)

---

## The Fix

**Backend has aggregation endpoint:**
`/api/v1/inventory/feed-container-stock/summary/`

**Returns:**
```json
{
  "total_quantity": "3728805.22",
  "total_value": "7785101.62",
  "unique_feed_types": 6,
  "unique_containers": 238,
  "by_feed_type": [...]
}
```

**Solution:** Update frontend to use summary endpoint instead of reducing paginated results.

---

## Frontend Fix Needed

**File:** `client/src/pages/inventory.tsx`

**Current (Wrong):**
```javascript
const totalQuantity = containerStock.reduce(
  (sum, item) => sum + parseFloat(item.quantityKg), 
  0
);
```

**Fix (Correct):**
```javascript
// Add query for summary endpoint
const { data: stockSummary } = useQuery({
  queryKey: ["/api/v1/inventory/feed-container-stock/summary/"],
  queryFn: async () => {
    const response = await fetch('/api/v1/inventory/feed-container-stock/summary/');
    return response.json();
  }
});

const totalQuantity = stockSummary?.total_quantity || 0;
const totalInventoryValue = stockSummary?.total_value || 0;
```

---

## Impact

**Current:** Users see misleading low stock levels (causes unnecessary orders)  
**Fixed:** Users see accurate stock totals for decision making

---

## Priority

**Medium** - Misleading but not blocking operations

**Workaround:** Backend data is correct, only display issue

---

**Status:** Documented, ready for frontend fix

