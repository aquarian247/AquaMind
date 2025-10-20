# Transfer Finance Integration - Phase 1 Complete ✅

**Date**: October 20, 2024  
**Status**: Phase 1 Database Schema - COMPLETE

---

## 🎯 Overview

Successfully completed Phase 1 of the Transfer Finance Integration, implementing polymorphic support for intercompany transactions and lifecycle-based pricing policies. The system now supports TWO types of intercompany transactions:

1. **Freshwater → Farming** (Post-Smolt transfer via BatchTransferWorkflow)
2. **Farming → Harvest** (Adult harvest via HarvestEvent)

---

## ✅ Completed Tasks

### **Task 1.1: Make IntercompanyTransaction Polymorphic** ✅

**Changes Made**:
- Added `content_type` and `object_id` fields for GenericForeignKey
- Added `source` GenericForeignKey property
- Made `event` FK nullable (deprecated, kept for backward compatibility)
- Added approval tracking fields:
  - `approved_by` (FK to User)
  - `approval_date` (DateTimeField)
- Reordered state choices: PENDING → POSTED → EXPORTED
- Added `source_type` and `source_display` properties
- Added `approve(user)` method for state transitions
- Added polymorphic unique constraint
- Added index on (content_type, object_id)

**File**: `apps/finance/models.py` (IntercompanyTransaction model)

---

### **Task 1.2: Extend IntercompanyPolicy for Lifecycle Stages** ✅

**Changes Made**:
- Added `pricing_basis` field (GRADE | LIFECYCLE)
- Added `lifecycle_stage` FK (nullable)
- Made `product_grade` FK nullable
- Added `price_per_kg` for STANDARD pricing
- Changed default method to STANDARD
- Added conditional unique constraints:
  - Grade-based: (from_company, to_company, product_grade)
  - Lifecycle-based: (from_company, to_company, lifecycle_stage)
- Added validation methods:
  - `_validate_pricing_basis()` - ensures correct field is set
  - `_validate_grade_pricing()` - validates grade-based policies
  - `_validate_lifecycle_pricing()` - validates lifecycle-based policies
  - `_validate_pricing_method()` - validates pricing requirements

**File**: `apps/finance/models.py` (IntercompanyPolicy model)

---

### **Task 1.3: Create Migration** ✅

**Migration**: `0005_transfer_finance_integration_phase1.py`

**Operations**:
1. Add pricing_basis, lifecycle_stage, price_per_kg to IntercompanyPolicy
2. Make product_grade nullable
3. Update unique constraints
4. Add content_type, object_id to IntercompanyTransaction
5. Make event nullable
6. Add approved_by, approval_date
7. Update state choices
8. Populate content_type/object_id from existing event FKs (data migration)
9. Add polymorphic constraints
10. Update historical models

**Status**: Applied successfully ✅

---

### **Task 1.4: Create seed_smolt_policies Management Command** ✅

**Command**: `python manage.py seed_smolt_policies`

**Functionality**:
- Seeds lifecycle-based pricing policies for all geographies
- Creates policies for Parr, Smolt, and Post-Smolt stages
- Pricing:
  - Parr: €8.50/kg
  - Smolt: €12.50/kg
  - Post-Smolt: €15.00/kg
- From: Freshwater Company
- To: Farming Company
- Supports `--dry-run` flag

**File**: `apps/finance/management/commands/seed_smolt_policies.py`

---

### **Task 1.5: Update Serializers** ✅

**Changes Made**:

#### IntercompanyPolicySummarySerializer:
- Added `pricing_basis`
- Added `lifecycle_stage` (LifeCycleStageSummarySerializer)
- Made `product_grade` allow_null
- Added `price_per_kg`

#### IntercompanyTransactionSerializer:
- Added `source_type` (polymorphic)
- Added `source_id` (object_id)
- Added `source_display` (human-readable)
- Added `approved_by`
- Added `approved_by_details` (UserSummarySerializer)
- Added `approval_date`
- Kept `event` as deprecated field

**File**: `apps/finance/api/serializers/intercompany_transaction.py`

---

### **Task 1.6: Update Admin Interface** ✅

**IntercompanyPolicyAdmin**:
- Added `pricing_basis`, `lifecycle_stage`, `price_per_kg` to list_display
- Added fieldsets:
  - Companies
  - Pricing Configuration (with helpful description)
  - Audit
- Updated filters and search fields

**IntercompanyTransactionAdmin**:
- Updated list_display with `source_type`, `approved_by`
- Added fieldsets:
  - Source (polymorphic fields + deprecated event)
  - Transaction Details
  - State & Approval
  - Audit
- Added `source_display` as readonly

**File**: `apps/finance/admin.py`

---

### **Task 1.7: Test Verification** ✅

**Tests Run**: `apps.finance.tests` (13 tests)

**Results**: ✅ All tests passing

**Verified**:
- Existing harvest flow works correctly
- Grade-based policies still function
- Data migration populated polymorphic fields
- Validation works correctly

---

## 📊 Database Schema Changes

### **IntercompanyPolicy**

**New Fields**:
```sql
pricing_basis VARCHAR(20) DEFAULT 'grade'
lifecycle_stage_id BIGINT NULL REFERENCES batch_lifecyclestage(id)
price_per_kg DECIMAL(10,2) NULL
```

**Modified Fields**:
```sql
product_grade_id BIGINT NULL  -- Was NOT NULL
method VARCHAR(20) DEFAULT 'standard'  -- Was 'market'
```

**New Constraints**:
- Conditional unique on (from_company, to_company, product_grade) WHERE pricing_basis='grade'
- Conditional unique on (from_company, to_company, lifecycle_stage) WHERE pricing_basis='lifecycle'

---

### **IntercompanyTransaction**

**New Fields**:
```sql
content_type_id BIGINT NULL REFERENCES django_content_type(id)
object_id INTEGER NULL
approved_by_id INTEGER NULL REFERENCES auth_user(id)
approval_date TIMESTAMPTZ NULL
```

**Modified Fields**:
```sql
event_id BIGINT NULL  -- Was NOT NULL
state VARCHAR(20) -- Updated choices display names
```

**New Constraints**:
- Unique on (content_type, object_id, policy)
- Index on (content_type, object_id)

---

## 🎯 Finance Transaction Flows

### **Flow 1: Freshwater → Farming (Post-Smolt Transfer)**

```
1. User completes BatchTransferWorkflow (Post-Smolt → Adult)
2. Workflow.check_completion() detects is_intercompany=True
3. Workflow._create_intercompany_transaction():
   - Finds lifecycle-based IntercompanyPolicy (Post-Smolt)
   - Calculates: total_biomass_kg × policy.price_per_kg
   - Creates IntercompanyTransaction:
     * content_type = BatchTransferWorkflow
     * object_id = workflow.id
     * state = PENDING
4. Farming Manager approves via API:
   POST /api/finance/intercompany-transactions/{id}/approve/
5. Transaction → POSTED
6. NAV export includes transaction
7. Transaction → EXPORTED
```

---

### **Flow 2: Farming → Harvest (Adult Harvest)**

```
1. HarvestEvent created (Adult → Processing)
2. Finance projection command runs
3. Detects intercompany (Farming → Harvest)
4. Finds grade-based IntercompanyPolicy (Superior/Standard/etc)
5. Creates IntercompanyTransaction:
   - content_type = HarvestEvent
   - object_id = event.id
   - state = PENDING
   - Uses market pricing or cost-plus markup
6. Finance Manager approves
7. Transaction → POSTED → EXPORTED
```

---

## 🔑 Key Design Decisions

### **1. Polymorphic Source Pattern**
- **Why**: Supports both HarvestEvent and BatchTransferWorkflow sources
- **How**: GenericForeignKey with ContentType
- **Benefit**: Single transaction model for all intercompany flows

### **2. Dual Pricing Basis**
- **Why**: Different pricing for transfers vs harvests
- **Grade-based**: For harvest (market/cost-plus from lot data)
- **Lifecycle-based**: For transfers (fixed €/kg by stage)
- **Benefit**: Flexible pricing strategies per business unit

### **3. State Machine Reordering**
- **Old**: PENDING → EXPORTED → POSTED
- **New**: PENDING → POSTED → EXPORTED
- **Why**: Approval must happen before export
- **Benefit**: Proper approval workflow

### **4. Backward Compatibility**
- Kept `event` FK as deprecated field
- Data migration populates polymorphic fields
- Old constraints conditional on event__isnull=False
- **Benefit**: Zero downtime, gradual migration

---

## 📋 Next Steps (Phase 2)

### **Service Layer Implementation**

**Task 2.1**: DimensionMappingService
- Container → DimSite → DimCompany mapping
- Handle both hall (freshwater) and area (farming) containers

**Task 2.2**: TransferFinanceService
- Calculate transfer value (biomass × price)
- Lookup pricing policies
- Create transactions

**Task 2.3**: Integrate with BatchTransferWorkflow
- Call service on completion
- Handle errors gracefully

**Task 2.4**: Add approval API endpoint
- `POST /api/batch/transfer-workflows/{id}/approve_finance/`
- Permission: Farming Manager only

**Task 2.5**: Update workflow to use real pricing
- Replace placeholder €8.50 with policy lookup
- Handle missing policies

---

## 🎓 Usage Examples

### **Create Lifecycle-Based Policy**

```python
from apps.finance.models import IntercompanyPolicy, DimCompany
from apps.batch.models import LifeCycleStage

policy = IntercompanyPolicy.objects.create(
    from_company=freshwater_company,
    to_company=farming_company,
    pricing_basis='lifecycle',
    lifecycle_stage=LifeCycleStage.objects.get(stage_name='Smolt'),
    method='standard',
    price_per_kg=Decimal('12.50'),
)
```

### **Create Transaction from Transfer Workflow**

```python
from apps.finance.models import IntercompanyTransaction
from django.contrib.contenttypes.models import ContentType

workflow_ct = ContentType.objects.get_for_model(BatchTransferWorkflow)

tx = IntercompanyTransaction.objects.create(
    content_type=workflow_ct,
    object_id=workflow.id,
    policy=policy,
    posting_date=workflow.actual_completion_date,
    amount=workflow.total_biomass_kg * policy.price_per_kg,
    currency='EUR',
    state='pending',
)
```

### **Approve Transaction**

```python
tx.approve(user=manager)
# State: PENDING → POSTED
# approved_by = manager
# approval_date = now()
```

---

## ✅ Success Criteria Met

- ✅ IntercompanyTransaction supports polymorphic sources
- ✅ IntercompanyPolicy supports lifecycle-based pricing
- ✅ Migration applied without data loss
- ✅ Seed command ready for policy creation
- ✅ Serializers expose new fields
- ✅ Admin interface updated
- ✅ All tests passing
- ✅ Backward compatible with existing harvest flow

---

## 🎉 Phase 1 Complete!

The database schema foundation is now ready for Phase 2 (Service Layer) implementation. The system can now:

1. ✅ Store transactions from multiple source types
2. ✅ Support lifecycle-based pricing for transfers
3. ✅ Track approval workflow
4. ✅ Maintain backward compatibility

**Ready to proceed with Phase 2!**

