# Transfer Workflow Finance Integration Plan

**Created**: October 18, 2024  
**Purpose**: Integrate BatchTransferWorkflow with Finance for intercompany transactions  
**Dependencies**: Transfer Workflow (completed), Finance app (existing)

---

## 📚 Context for AI Agents

### Required Reading
1. `apps/batch/models/workflow.py` - Workflow state machine, `detect_intercompany()` method
2. `apps/finance/models.py` - `IntercompanyTransaction`, `IntercompanyPolicy`, dimension models
3. `apps/infrastructure/models/` - Container→Hall/Area→Site→Company mapping
4. `apps/users/models.py` - Subsidiary enum, permission model

### Key Architecture
- **Polymorphic Transactions**: Single model supports harvest + transfer sources
- **Auto-Detection**: Workflow detects intercompany via container locations
- **Approval Flow**: PENDING → (Manager Approves) → POSTED → EXPORTED
- **Dimension Mapping**: Container → DimSite → DimCompany

---

## PHASE 1: Database Schema (3 days)

### Task 1.1: Make IntercompanyTransaction Polymorphic
**File**: `apps/finance/models.py`

**Changes**:
```python
# Replace event FK with GenericForeignKey
content_type = models.ForeignKey(ContentType, ...)
object_id = models.PositiveIntegerField()
source = GenericForeignKey('content_type', 'object_id')

# Add approval fields
approved_by = models.ForeignKey(User, null=True, ...)
approval_date = models.DateTimeField(null=True, ...)

# Reorder states: PENDING → POSTED → EXPORTED
```

**Migration**: Preserve existing harvest records, populate `content_type` + `object_id`

---

### Task 1.2: Extend IntercompanyPolicy for Lifecycle Stages
**File**: `apps/finance/models.py`

**Add**:
```python
lifecycle_stage = models.ForeignKey('batch.LifeCycleStage', null=True, ...)
pricing_basis = models.CharField(choices=['grade', 'lifecycle'], ...)
price_per_kg = models.DecimalField(null=True, ...)  # For STANDARD transfers
```

**Validation**: Require product_grade XOR lifecycle_stage based on pricing_basis

---

### Task 1.3: Seed Smolt Pricing Policies
**Command**: `python manage.py seed_smolt_policies`

**Create**:
- Parr: 8.50 EUR/kg
- Smolt: 12.50 EUR/kg
- Per geography (Norway, Iceland, etc.)
- Freshwater → Farming direction

---

## PHASE 2: Service Layer (4 days)

### Task 2.1: Container→Company Mapping Service
**File**: `apps/finance/services/dimension_mapping.py` (new)

```python
class DimensionMappingService:
    @staticmethod
    def get_company_for_container(container):
        """Maps container → DimSite → DimCompany"""
        if container.hall:
            site = DimSite.objects.get(source_model='station', source_pk=station_id)
        elif container.area:
            site = DimSite.objects.get(source_model='area', source_pk=area_id)
        return site.company
```

---

### Task 2.2: Transfer Finance Service
**File**: `apps/finance/services/transfer_finance.py` (new)

```python
class TransferFinanceService:
    def calculate_transfer_value(self):
        """Sums action biomass × policy price"""
    
    def _get_pricing_policy(self):
        """Looks up policy by companies + lifecycle_stage"""
    
    def create_transaction(self):
        """Creates PENDING IntercompanyTransaction"""
```

---

### Task 2.3: Integrate with Workflow
**File**: `apps/batch/models/workflow.py`

**Modify**:
```python
def save(self):
    if status_changed_to_COMPLETED and is_intercompany:
        self._create_intercompany_transaction()

def _create_intercompany_transaction(self):
    service = TransferFinanceService(self)
    self.finance_transaction = service.create_transaction()

def approve_finance_transaction(self, user):
    """Moves transaction PENDING → POSTED"""
    self.finance_transaction.state = 'POSTED'
    self.finance_transaction.approved_by = user
    self.finance_transaction.save()
```

---

### Task 2.4: Finance API Layer
**File**: `apps/finance/api/` (new)

**Create**:
- `serializers.py`: IntercompanyTransactionSerializer, IntercompanyPolicySerializer
- `viewsets.py`: ReadOnly viewsets + `pending_approvals` action
- `routers.py`: Register at `/api/finance/`

**Endpoints**:
```
GET /api/finance/intercompany-transactions/
GET /api/finance/intercompany-transactions/pending_approvals/
GET /api/finance/intercompany-policies/
```

---

### Task 2.5: Add Workflow Approval Endpoint
**File**: `apps/batch/api/viewsets/workflows.py`

```python
@action(detail=True, methods=['post'])
def approve_finance(self, request, pk=None):
    """Approves transaction if user is Farming Manager"""
    workflow.approve_finance_transaction(request.user)
    return Response({'message': 'Approved'})
```

---

## PHASE 3: Testing (2 days)

### Task 3.1: Unit Tests
**File**: `apps/finance/tests/test_transfer_finance.py`

**Coverage**:
- Container mapping (hall → company, area → company)
- Value calculation (biomass × price)
- Policy lookup (lifecycle stage matching)
- Transaction creation (PENDING state)
- Approval workflow (permission checks)
- No duplicate transactions

---

### Task 3.2: Integration Tests
**File**: `apps/batch/tests/test_workflow_finance_integration.py`

**Scenarios**:
- End-to-end: Create workflow → Execute → Complete → Transaction PENDING → Approve → POSTED
- Error handling: No policy found, insufficient data
- Permission tests: Only Farming managers can approve

---

## PHASE 4: Admin & Documentation (1 day)

### Task 4.1: Update Admin
**File**: `apps/finance/admin.py`

- Show source_type in transaction list
- Add approved_by, approval_date to readonly fields
- Filter by state, source_type

---

### Task 4.2: Create User Documentation
**File**: `docs/user_guides/intercompany_transfers.md`

**Topics**:
- How intercompany detection works
- Approval workflow for Farming managers
- Pricing policy configuration
- NAV export process

---

## Success Criteria

- ✅ Workflows auto-create transactions on completion
- ✅ Farming managers can approve via API
- ✅ Transactions appear in NAV export batches
- ✅ All tests pass
- ✅ No breaking changes to harvest flow
- ✅ Admin interface updated

---

## API Summary

**New Endpoints**:
```
POST /api/batch/transfer-workflows/{id}/approve_finance/
GET  /api/finance/intercompany-transactions/
GET  /api/finance/intercompany-transactions/pending_approvals/
GET  /api/finance/intercompany-policies/?pricing_basis=lifecycle
```

**Response Example**:
```json
{
  "tx_id": 123,
  "source_type": "batchtransferworkflow",
  "source_id": 456,
  "amount": "15625.00",
  "currency": "EUR",
  "state": "PENDING",
  "posting_date": "2024-10-20",
  "policy_details": {
    "from_company_name": "Norway Freshwater",
    "to_company_name": "Norway Farming",
    "lifecycle_stage_name": "Smolt",
    "price_per_kg": "12.50"
  }
}
```
