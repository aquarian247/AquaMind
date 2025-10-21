# Backend Remaining Work - Handoff Document

**Date:** October 20, 2025  
**Session:** Post Geography-Summary Implementation  
**Context:** Executive Dashboard backend support (Issue #104 complete)

---

## ✅ **What's Complete**

### **1. Geography Summary Endpoint** (October 20, 2025)
```
GET /api/v1/batch/batches/geography-summary/?geography={id}
```

**Status:** ✅ **DEPLOYED - Ready for Frontend**  
**Tests:** 10/10 passing  
**Real Data Validated:** ✅ Tested with 27M fish, 28M kg biomass  
**Documentation:** ✅ Updated both AGGREGATION_ENDPOINTS_CATALOG.md files  
**GitHub Issue:** [#104](https://github.com/aquarian247/AquaMind/issues/104) - Complete

**Provides:**
- Growth metrics (SGR, growth rate, biomass)
- Mortality metrics (total, rate, by cause)
- Feed metrics (total feed, costs)

**Frontend Handoff Doc:** `AquaMind-Frontend/docs/progress/executives_frontends/executive-dashboard-plan/BACKEND_HANDOFF_GEOGRAPHY_SUMMARY.md`

---

### **2. Transfer Workflow Architecture** (October 18, 2024)
**Status:** ✅ **Backend Complete**  
**Tests:** 6/6 passing  
**Documentation:** `aquamind/docs/progress/transfer_finance_enhancements/TRANSFER_WORKFLOW_IMPLEMENTATION_COMPLETE.md`

**Provides:**
- Multi-day transfer orchestration
- State machine (DRAFT → PLANNED → IN_PROGRESS → COMPLETED)
- Action-level execution tracking
- Intercompany detection (ready for finance integration)

**Awaiting:** Finance integration + Frontend UI

---

## 🎯 **Remaining Work - Logical Sequencing**

### **Critical Path Analysis:**

The remaining work has **dependencies** that must be considered:

```
┌─────────────────────────────────────────────────────────┐
│ PHASE 1: Transfer-Finance Integration                   │
│ └─> Unlocks financial data for aggregations             │
│     └─> Required for Executive Dashboard Financial Tab  │
└─────────────────────────────────────────────────────────┘
          ↓
┌─────────────────────────────────────────────────────────┐
│ PHASE 2: Financial Aggregation Endpoints                │
│ └─> Aggregates transaction data                         │
│     └─> Powers Executive Dashboard                      │
└─────────────────────────────────────────────────────────┘
          ↓
┌─────────────────────────────────────────────────────────┐
│ PHASE 3: Optional Enhancements                          │
│ └─> TGC, Market Prices, Trends                          │
└─────────────────────────────────────────────────────────┘
```

---

## 🔴 **PHASE 1: Transfer-Finance Integration** (HIGHEST PRIORITY)

**Why First:**
- Transfer Workflow backend is already complete
- Finance app exists with IntercompanyTransaction model
- Unlocks financial data needed for other aggregations
- Clear plan already exists

**Documentation:** `aquamind/docs/progress/transfer_finance_enhancements/transfer_finance_integration_plan.md`

### **Task 1.1: Make IntercompanyTransaction Polymorphic** (4-6 hours)

**Goal:** Support both harvest events AND transfer workflows as transaction sources

**File:** `apps/finance/models.py`

**Changes:**
```python
# Current (harvest only)
class IntercompanyTransaction(models.Model):
    harvest_event = models.ForeignKey(HarvestEvent, ...)

# New (polymorphic)
class IntercompanyTransaction(models.Model):
    content_type = models.ForeignKey(ContentType, ...)
    object_id = models.PositiveIntegerField()
    source = GenericForeignKey('content_type', 'object_id')
    
    # Add approval workflow
    approved_by = models.ForeignKey(User, null=True, ...)
    approval_date = models.DateTimeField(null=True, ...)
```

**Migration Strategy:**
1. Create new fields (content_type, object_id)
2. Backfill existing harvest_event → GenericForeignKey
3. Deprecate harvest_event FK (keep for backward compat)
4. Add data validation

**Tests:**
- Backward compatibility with existing harvest transactions
- New transfer transactions work
- Generic FK queries performant

---

### **Task 1.2: Extend IntercompanyPolicy for Lifecycle Stages** (3-4 hours)

**Goal:** Support smolt/parr pricing (not just harvest grades)

**File:** `apps/finance/models.py`

**Add Fields:**
```python
class IntercompanyPolicy(models.Model):
    # Existing: product_grade (for harvest)
    
    # NEW:
    lifecycle_stage = models.ForeignKey('batch.LifeCycleStage', null=True, ...)
    pricing_basis = models.CharField(
        choices=[
            ('GRADE', 'Product Grade (Harvest)'),
            ('LIFECYCLE', 'Lifecycle Stage (Smolt/Parr)')
        ]
    )
    price_per_kg = models.DecimalField(...)  # Flat rate for lifecycle
```

**Validation:**
- Must have EITHER product_grade OR lifecycle_stage (not both)
- pricing_basis determines which is required

**Seed Data:**
```python
# Create smolt pricing policies
IntercompanyPolicy.objects.create(
    from_company=norway_freshwater,
    to_company=norway_farming,
    lifecycle_stage=smolt_stage,
    pricing_basis='LIFECYCLE',
    price_per_kg=12.50,  # EUR
    effective_from='2024-01-01'
)
```

---

### **Task 1.3: Container→Company Mapping Service** (2-3 hours)

**Goal:** Determine which company owns a container

**File:** `apps/finance/services/dimension_mapping.py` (NEW)

```python
class DimensionMappingService:
    """Maps infrastructure → finance dimensions."""
    
    @staticmethod
    def get_company_for_container(container):
        """
        Returns DimCompany for a container.
        
        Logic:
        - Hall containers: Hall → Station → Geography → DimSite → DimCompany
        - Area containers: Area → Geography → DimSite → DimCompany
        """
        if container.hall:
            station = container.hall.freshwater_station
            site = DimSite.objects.get(
                source_model='freshwaterstation',
                source_pk=station.id
            )
        elif container.area:
            site = DimSite.objects.get(
                source_model='area',
                source_pk=container.area.id
            )
        else:
            raise ValueError("Container must have hall or area")
        
        return site.company
```

**Tests:**
- Hall-based container mapping
- Area-based container mapping
- Missing dimension error handling

---

### **Task 1.4: Transfer Finance Service** (4-6 hours)

**Goal:** Calculate transfer value and create IntercompanyTransaction

**File:** `apps/finance/services/transfer_finance.py` (NEW)

```python
class TransferFinanceService:
    """Handles financial transactions for batch transfers."""
    
    def __init__(self, workflow: BatchTransferWorkflow):
        self.workflow = workflow
    
    def calculate_transfer_value(self) -> Decimal:
        """
        Calculates total value of transfer.
        
        Formula: Sum(action.transferred_biomass_kg × policy.price_per_kg)
        """
        total = Decimal('0.00')
        for action in self.workflow.actions.filter(status='COMPLETED'):
            policy = self._get_pricing_policy(action)
            value = action.transferred_biomass_kg * policy.price_per_kg
            total += value
        return total
    
    def _get_pricing_policy(self, action) -> IntercompanyPolicy:
        """Lookup policy by companies + lifecycle stage."""
        from_company = DimensionMappingService.get_company_for_container(
            action.source_assignment.container
        )
        to_company = DimensionMappingService.get_company_for_container(
            action.dest_assignment.container
        )
        
        return IntercompanyPolicy.objects.get(
            from_company=from_company,
            to_company=to_company,
            lifecycle_stage=self.workflow.dest_lifecycle_stage,
            pricing_basis='LIFECYCLE',
            effective_from__lte=action.actual_execution_date
        )
    
    def create_transaction(self) -> IntercompanyTransaction:
        """Creates PENDING transaction."""
        return IntercompanyTransaction.objects.create(
            content_type=ContentType.objects.get_for_model(
                BatchTransferWorkflow
            ),
            object_id=self.workflow.id,
            from_company=...,
            to_company=...,
            amount=self.calculate_transfer_value(),
            state='PENDING',
            posting_date=self.workflow.actual_completion_date
        )
```

**Tests:**
- Value calculation (multiple actions)
- Policy lookup (lifecycle stages)
- Transaction creation (PENDING state)
- No duplicate transactions

---

### **Task 1.5: Workflow-Finance Signal Integration** (2-3 hours)

**Goal:** Auto-create transactions when workflow completes

**File:** `apps/batch/models/workflow.py`

**Add Method:**
```python
def save(self, *args, **kwargs):
    old_status = None
    if self.pk:
        old_status = BatchTransferWorkflow.objects.get(pk=self.pk).status
    
    super().save(*args, **kwargs)
    
    # Create finance transaction on completion
    if old_status != 'COMPLETED' and self.status == 'COMPLETED':
        if self.is_intercompany and not self.finance_transaction:
            self._create_finance_transaction()

def _create_finance_transaction(self):
    """Creates finance transaction for intercompany transfers."""
    from apps.finance.services.transfer_finance import TransferFinanceService
    
    service = TransferFinanceService(self)
    transaction = service.create_transaction()
    
    self.finance_transaction = transaction
    self.save(update_fields=['finance_transaction'])
```

---

### **Task 1.6: Finance Approval API** (3-4 hours)

**Goal:** Allow Farming Managers to approve transactions

**Files:**
- `apps/finance/api/viewsets.py` (NEW)
- `apps/batch/api/viewsets/workflows.py` (modify)

**New Endpoints:**
```python
# Finance app
GET  /api/v1/finance/intercompany-transactions/
GET  /api/v1/finance/intercompany-transactions/pending-approvals/
POST /api/v1/finance/intercompany-transactions/{id}/approve/

# Batch app (convenience)
POST /api/v1/batch/transfer-workflows/{id}/approve-finance/
```

**Permissions:**
```python
def approve_finance(self, request, pk=None):
    """Approve finance transaction (Farming Manager only)."""
    workflow = self.get_object()
    
    if not request.user.has_perm('finance.approve_intercompany'):
        return Response(
            {'error': 'Insufficient permissions'},
            status=403
        )
    
    workflow.finance_transaction.approve(request.user)
    return Response({'message': 'Transaction approved'})
```

---

### **Task 1.7: Tests** (3-4 hours)

**Files:**
- `apps/finance/tests/test_transfer_finance_service.py` (NEW)
- `apps/batch/tests/test_workflow_finance_integration.py` (NEW)

**Coverage:**
- Container→Company mapping (hall & area paths)
- Transfer value calculation
- Policy lookup (lifecycle stages)
- Transaction auto-creation on workflow completion
- Approval workflow
- Permissions enforcement
- No duplicate transactions

---

**PHASE 1 Total:** 21-30 hours (~4-5 days)

**Impact:**
- ✅ Transfers generate financial transactions
- ✅ Intercompany billing automated
- ✅ Approval workflow operational
- ✅ NAV export includes transfer transactions
- ✅ **Unlocks data for financial aggregations**

---

## 🟡 **PHASE 2: Financial Aggregation Endpoints** (AFTER PHASE 1)

**Why Second:**
- Requires transfer-finance integration to have complete data
- Executive Dashboard Financial Tab needs this
- Business logic depends on transaction model being complete

### **Task 2.1: Finance Summary Endpoint** (4-6 hours)

**Goal:** Geography-level financial KPIs

**File:** `apps/finance/api/viewsets.py`

```
GET /api/v1/finance/summary/?geography={id}&start_date={date}&end_date={date}
```

**Response:**
```json
{
  "geography_id": 1,
  "geography_name": "Faroe Islands",
  "period_start": "2024-10-01",
  "period_end": "2024-10-31",
  "revenue": {
    "total_harvest_revenue": 5000000.00,
    "total_transfer_revenue": 125000.00,
    "total": 5125000.00
  },
  "costs": {
    "feed_cost": 1200000.00,
    "labor_cost": 800000.00,
    "transfer_cost": 125000.00,
    "total": 2125000.00
  },
  "margins": {
    "gross_margin": 3000000.00,
    "gross_margin_percent": 58.5,
    "ebitda": 2500000.00
  }
}
```

**Data Sources:**
- Revenue: HarvestEvent transactions + IntercompanyTransaction (selling)
- Costs: FeedingEvent costs + IntercompanyTransaction (buying) + Labor (TBD)
- Margins: Calculated from revenue - costs

**Dependencies:**
- ✅ Harvest transactions (exist)
- ⚠️ Transfer transactions (PHASE 1 needed)
- ⚠️ Labor costs (may need new model or external data)

---

### **Task 2.2: Revenue Trends Endpoint** (3-4 hours)

```
GET /api/v1/finance/revenue-trends/?geography={id}&interval=monthly
```

**Response:**
```json
{
  "trends": [
    {
      "period": "2024-10",
      "harvest_revenue": 500000.00,
      "transfer_revenue": 12500.00,
      "total_revenue": 512500.00
    }
  ]
}
```

**Use Case:** Executive Dashboard Financial Tab - Revenue Trend Chart

---

### **Task 2.3: Cost Breakdown Endpoint** (3-4 hours)

```
GET /api/v1/finance/cost-breakdown/?geography={id}&start_date={date}
```

**Response:**
```json
{
  "breakdown": [
    {"category": "FEED", "amount": 1200000.00, "percentage": 56.5},
    {"category": "LABOR", "amount": 800000.00, "percentage": 37.6},
    {"category": "TRANSFERS", "amount": 125000.00, "percentage": 5.9}
  ]
}
```

**Use Case:** Executive Dashboard Financial Tab - Cost Breakdown Pie Chart

---

**PHASE 2 Total:** 10-14 hours (~2-3 days)

**Impact:**
- ✅ Executive Dashboard Financial Tab goes live
- ✅ Real revenue/cost/margin data
- ✅ Financial trend analysis enabled

---

## 🟢 **PHASE 3: Optional Enhancements** (LOWEST PRIORITY)

**Why Last:**
- Not blocking Executive Dashboard
- Can be added incrementally
- User feedback will guide priorities

### **Task 3.1: TGC Calculation** (4-6 hours)

**Goal:** Integrate temperature data into growth calculations

**Requires:**
- Join GrowthSample with EnvironmentalReading (by container, date)
- Calculate TGC = (W^1/3 - W0^1/3) / (∑°C × 1000)
- Update geography-summary endpoint to include avg_tgc

**Impact:** Medium - SGR is more commonly used anyway

---

### **Task 3.2: Market Price Integration** (8-12 hours)

**Goal:** Real-time salmon market prices

**Options:**
1. **External API** (Stágri Salmon Index, Fish Pool Index)
2. **Manual Entry** (MarketPrice model with admin UI)
3. **CSV Import** (Daily price updates)

**Endpoint:**
```
GET /api/v1/market/prices/?currency=EUR&date={date}
```

**Impact:** Medium - Useful for strategic planning

---

### **Task 3.3: Period-over-Period Trends** (4-6 hours)

**Goal:** Compare current vs previous period

**Approach:** Extend existing endpoints with `compare_to_previous=true` parameter

**Example:**
```json
{
  "current_period": {
    "avg_sgr": 3.65,
    "mortality_rate": 17.78
  },
  "previous_period": {
    "avg_sgr": 3.42,
    "mortality_rate": 18.92
  },
  "changes": {
    "sgr_change_percent": +6.7,
    "mortality_improvement": -1.14
  }
}
```

**Impact:** High UX value, but can wait for user feedback

---

**PHASE 3 Total:** 16-24 hours (~3-5 days)

---

## 🗺️ **Recommended Execution Order**

### **Session 1: Transfer-Finance Integration** ⭐ **START HERE**
**Estimated:** 21-30 hours (4-5 days)

**Goals:**
- [ ] Polymorphic IntercompanyTransaction model
- [ ] Lifecycle stage pricing policies
- [ ] Container→Company mapping service
- [ ] Transfer finance service (value calculation)
- [ ] Auto-create transactions on workflow completion
- [ ] Finance approval API
- [ ] Comprehensive tests

**Deliverables:**
- Transfers automatically generate financial transactions
- Farming managers can approve via UI/API
- NAV export includes transfer data
- Foundation for financial aggregations

**GitHub Issue:** Create new issue (reference transfer_finance_integration_plan.md)

---

### **Session 2: Financial Aggregation Endpoints** ⭐ **SECOND**
**Estimated:** 10-14 hours (2-3 days)

**Prerequisites:** PHASE 1 complete (needs transfer transaction data)

**Goals:**
- [ ] `/api/v1/finance/summary/` endpoint
- [ ] `/api/v1/finance/revenue-trends/` endpoint
- [ ] `/api/v1/finance/cost-breakdown/` endpoint
- [ ] Tests & documentation
- [ ] Update AGGREGATION_ENDPOINTS_CATALOG.md

**Deliverables:**
- Executive Dashboard Financial Tab can go live
- Real revenue/cost/margin data
- Trend analysis enabled

**GitHub Issue:** Create after PHASE 1 complete

---

### **Session 3: Optional Enhancements** (As Needed)
**Estimated:** 16-24 hours (3-5 days)

**Prerequisites:** User feedback on Phases 1 & 2

**Goals:** TBD based on:
- Executive team feedback on current dashboard
- Most requested features
- Business priority shifts

**Options:**
- TGC temperature integration
- Market price feeds
- Period-over-period comparisons
- Advanced financial analytics
- Forecasting/predictions

---

## 📊 **Alternative: Lightweight Financial Summary** (Skip PHASE 1)

If you want Executive Dashboard Financial Tab **faster** without waiting for transfer-finance integration:

### **Quick Win: Basic Finance Summary** (4-6 hours)

**Scope:**
- Aggregate only what exists TODAY:
  - Feed costs (from FeedingEvent.feed_cost)
  - Harvest revenue (from existing IntercompanyTransaction)
- Mark transfer costs as "Integration pending"

**Pros:**
- ✅ Fast delivery (1 session)
- ✅ Shows some financial data
- ✅ Unblocks Executive Dashboard Financial Tab

**Cons:**
- ⚠️ Incomplete (missing transfer costs)
- ⚠️ Will need rework later

**Recommendation:** Only do this if Transfer-Finance integration is >1 month away. Otherwise, wait and do it properly.

---

## 🎯 **My Recommended Path**

### **For Backend Work:**

**Priority 1:** Transfer-Finance Integration (PHASE 1)
- Well-documented plan exists
- Unlocks downstream features
- High business value (automated billing)

**Priority 2:** Financial Aggregation Endpoints (PHASE 2)
- Depends on PHASE 1
- Completes Executive Dashboard backend support

**Priority 3:** Optional enhancements based on feedback

---

### **For Frontend Work:**

**Immediate (This Week):**
1. Integrate geography-summary endpoint (1-2 hours)
   - Use handoff doc: `BACKEND_HANDOFF_GEOGRAPHY_SUMMARY.md`
   - Get real KPIs showing in Executive Dashboard
2. Deploy to staging for user testing

**Later (After PHASE 2):**
1. Add Financial Tab charts (revenue trends, cost breakdown)
2. Polish based on executive feedback

---

## 📋 **Handoff Checklist**

### **For Frontend Agent:**
- [x] Geography summary endpoint documented
- [x] Integration guide created
- [x] Real data examples provided
- [x] Code samples ready
- [x] Field mappings complete
- [x] Catalogs updated (both repos)

### **For Next Backend Agent:**
- [x] Remaining work identified
- [x] Dependencies mapped
- [x] Logical sequencing established
- [x] Existing plans referenced
- [x] Estimated efforts provided

---

## 🤔 **Decision Points**

### **Question 1: Transfer-Finance Integration**
**When do you want this?**
- **Option A:** Next sprint (recommended - unlocks everything)
- **Option B:** Later (defer financial features)

**If Option A:** Start with Task 1.1 (Polymorphic Transactions)  
**If Option B:** Build lightweight finance summary instead

---

### **Question 2: Market Price Integration**
**How should prices be sourced?**
- **Option A:** External API (Stágri, Fish Pool) - requires integration work
- **Option B:** Manual entry (MarketPrice model) - simpler, less accurate
- **Option C:** Skip for now - use placeholders

**Recommendation:** Option C - wait for user feedback on what they actually need

---

### **Question 3: Executive Dashboard Financial Tab**
**What data do executives ACTUALLY need?**

Before building endpoints, validate:
- Do they care about transfer costs? (Probably yes)
- Do they need cost breakdowns? (Probably yes)
- Do they need revenue trends? (Probably yes)
- Do they need market prices? (Ask them!)

**Recommendation:** Get feedback after geography-summary goes live, then prioritize

---

## 📚 **Reference Documentation**

**Transfer-Finance:**
- `aquamind/docs/progress/transfer_finance_enhancements/transfer_finance_integration_plan.md`
- `aquamind/docs/progress/transfer_finance_enhancements/TRANSFER_WORKFLOW_ARCHITECTURE.md`
- `aquamind/docs/progress/transfer_finance_enhancements/TRANSFER_WORKFLOW_IMPLEMENTATION_COMPLETE.md`

**Executive Dashboard:**
- `AquaMind-Frontend/docs/progress/executives_frontends/executive-dashboard-plan/IMPLEMENTATION_PLAN.md`
- `AquaMind-Frontend/docs/progress/executives_frontends/executive-dashboard-plan/BACKEND_HANDOFF_GEOGRAPHY_SUMMARY.md`

**Aggregation Patterns:**
- `aquamind/docs/development/aggregation_playbook.md`
- `aquamind/docs/quality_assurance/AGGREGATION_ENDPOINTS_CATALOG.md`

**Models:**
- `apps/batch/models/workflow.py` - Transfer workflows
- `apps/finance/models.py` - Finance transactions
- `apps/infrastructure/models/` - Geography/container mappings

---

## 🎯 **Summary: What to Do Next**

### **If You Want Executive Dashboard Live ASAP:**
1. ✅ Geography summary endpoint is ready (done today!)
2. Frontend integrates it (1-2 hours)
3. Show Financial Tab with "Integration pending" banners
4. Gather executive feedback
5. **Then** decide on PHASE 1 vs PHASE 2 vs PHASE 3

### **If You Want Complete Financial Data:**
1. Start PHASE 1 (Transfer-Finance Integration)
2. Then PHASE 2 (Financial Aggregations)
3. Frontend integrates everything at once
4. Full-featured Executive Dashboard launch

**My Vote:** Ship geography-summary to frontend NOW, gather feedback, then decide on financial work based on actual executive needs.

---

**Ready for next agent!** 🚀

All context preserved, logical sequencing established, and decisions clearly laid out. The handoff doc for frontend is ready in the Frontend repo.



