# Implementation Plan: Freshwater-to-Sea Transfers

## 1. Overview

### 1.1 Purpose
This document outlines the implementation plan for a new critical feature in AquaMind: **Freshwater-to-Sea Transfers**. This feature will manage the operational, logistical, and financial processes involved when salmon smolts are transferred from land-based freshwater stations to sea-based farming areas.

### 1.2 Scope
The scope of this project includes:
1.  **Inter-Subsidiary Financial Transactions:** A system to record the sale and purchase of smolts between the 'Freshwater' and 'Farming' subsidiaries, including pricing per kilogram.
2.  **Digital Ship Transport Reporting:** A module for ship crews to digitally fill out transport reports, replacing the current manual Word template process.
3.  **Integration with Batch Management:** Seamless integration of these new functionalities into the existing `batch` application.

### 1.3 Goals
-   **Enhance Financial Accuracy:** Provide a clear, auditable record of inter-subsidiary sales, improving financial reporting.
-   **Improve Operational Efficiency:** Digitize and streamline the transfer process, eliminating manual paperwork for ship crews.
-   **Increase Data Traceability:** Create a single, unified record for each transfer that links operational, logistical, and financial data.
-   **Empower Mobile Workforce:** Provide a mobile-friendly interface for ship crews to perform their duties on-site.

---

## 2. Background & Current State Analysis

A review of the current AquaMind system reveals the following:

-   **What Exists:**
    -   A `BatchTransfer` model in the `batch` app that can record the movement of fish between containers.
    -   A `UserProfile` model that assigns users to specific subsidiaries (`Freshwater`, `Farming`, `Logistics`).
    -   A `personas.md` document that confirms the need for transport reports and highlights the manual process currently used by ship crews.

-   **What is Missing:**
    -   **Financial Layer:** There is no mechanism to associate a monetary value or price with a `BatchTransfer`.
    -   **Transport-Specific Data:** The current `BatchTransfer` model does not capture logistical details required for a transport report (e.g., ship details, crew information, environmental conditions during transit).
    -   **Defined Workflow:** There is no defined system workflow that orchestrates the actions required from managers and ship crews during a freshwater-to-sea transfer.

---

## 3. Proposed Architecture and Solution

To address these gaps, we propose creating two new models and extending the existing `BatchTransfer` model. This will be supported by new API endpoints and a clearly defined user workflow.

### 3.1 Data Model Changes

We will introduce a new Django app `transactions` for financial models and utilize the existing `operational` app for logistical reports.

#### 3.1.1 New App & Model: `transactions.InterSubsidiaryTransaction`
This model will handle the financial aspect of the transfer.

```python
# apps/transactions/models.py

from django.db import models
from django.conf import settings
from apps.users.models import Subsidiary
from apps.batch.models import BatchTransfer

class InterSubsidiaryTransaction(models.Model):
    """
    Records the financial transaction for the transfer of assets (e.g., fish)
    between two internal subsidiaries.
    """
    class TransactionStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending Approval'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    batch_transfer = models.OneToOneField(
        BatchTransfer,
        on_delete=models.CASCADE,
        related_name='financial_transaction'
    )
    source_subsidiary = models.CharField(max_length=3, choices=Subsidiary.choices)
    destination_subsidiary = models.CharField(max_length=3, choices=Subsidiary.choices)
    
    # Values at time of transfer initiation
    estimated_biomass_kg = models.DecimalField(max_digits=10, decimal_places=2)
    price_per_kg = models.DecimalField(max_digits=8, decimal_places=2)
    estimated_total_value = models.DecimalField(max_digits=12, decimal_places=2)

    # Values at time of completion
    actual_biomass_kg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    actual_total_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    status = models.CharField(max_length=10, choices=TransactionStatus.choices, default=TransactionStatus.PENDING)
    notes = models.TextField(blank=True)

    initiated_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='initiated_transactions', on_delete=models.PROTECT)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='approved_transactions', on_delete=models.PROTECT, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Transaction from {self.source_subsidiary} to {self.destination_subsidiary} for Batch Transfer {self.batch_transfer.id}"
```

#### 3.1.2 New Model: `operational.ShipTransportReport`
This model will serve as the digital replacement for the crew's Word template.

```python
# apps/operational/models.py

from django.db import models
from django.conf import settings
from apps.batch.models import BatchTransfer

class ShipTransportReport(models.Model):
    """
    A detailed report for the transport of fish via ship, typically for
    freshwater-to-sea transfers.
    """
    batch_transfer = models.OneToOneField(
        BatchTransfer,
        on_delete=models.CASCADE,
        related_name='transport_report'
    )
    ship_name = models.CharField(max_length=100)
    captain_name = models.CharField(max_length=100)
    crew_members = models.JSONField(default=list, help_text="List of crew member names")

    departure_datetime = models.DateTimeField()
    arrival_datetime = models.DateTimeField()

    # Environmental conditions in transport tanks
    avg_tank_temperature = models.DecimalField(max_digits=5, decimal_places=2, help_text="°C")
    avg_tank_oxygen_level = models.DecimalField(max_digits=5, decimal_places=2, help_text="mg/L")

    # Environmental conditions at sea destination
    sea_temperature = models.DecimalField(max_digits=5, decimal_places=2, help_text="°C")
    sea_current_speed = models.DecimalField(max_digits=5, decimal_places=2, help_text="knots", null=True, blank=True)
    weather_conditions = models.CharField(max_length=255)

    transport_mortality_count = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)

    completed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    completion_timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Transport Report for {self.ship_name} on {self.departure_datetime.date()}"
```

#### 3.1.3 Extending `batch.BatchTransfer`
The existing `BatchTransfer` model will be modified to link to these new models and include a new transfer type.

```python
# apps/batch/models/transfer.py (Illustrative changes)

class BatchTransfer(models.Model):
    TRANSFER_TYPE_CHOICES = [
        ('CONTAINER', 'Container Transfer'),
        ('LIFECYCLE', 'Lifecycle Stage Change'),
        ('SPLIT', 'Batch Split'),
        ('MERGE', 'Batch Merge'),
        ('MIXED_TRANSFER', 'Mixed Batch Transfer'),
        ('INTER_SUBSIDIARY', 'Inter-Subsidiary Transfer'), # New Type
    ]
    
    # ... existing fields ...
    
    # No new fields needed directly, as relations are defined on the new models
    # with OneToOneField pointing back to BatchTransfer.
```

### 3.2 API Endpoints

New API endpoints will be created to manage these resources.

-   **Create Inter-Subsidiary Transfer:**
    -   `POST /api/v1/batch/transfers/`
    -   The existing endpoint will be enhanced. If `transfer_type` is `'INTER_SUBSIDIARY'`, the serializer will accept nested data to create the `InterSubsidiaryTransaction`.
    -   **Payload:** `{ "transfer_type": "INTER_SUBSIDIARY", ..., "financial_transaction": { "price_per_kg": 12.50 } }`
    -   This action will create the `BatchTransfer` and a `PENDING` `InterSubsidiaryTransaction`.

-   **Manage Ship Transport Report:**
    -   `GET /api/v1/operational/transport-reports/{id}/`
    -   `PUT /api/v1/operational/transport-reports/{id}/`
    -   The ship crew will use this endpoint to retrieve the report structure and submit the completed data. The `PUT` method ensures all fields are provided for completion.

-   **Manage Transactions:**
    -   `GET /api/v1/transactions/` (List pending/completed transactions)
    -   `POST /api/v1/transactions/{id}/approve/`
    -   A custom action for the destination manager to approve the transaction, update the `actual_biomass_kg`, and move the status to `COMPLETED`.

### 3.3 User Workflow

1.  **Initiation (Freshwater Manager):**
    -   The Freshwater Manager navigates to the batch they want to transfer.
    -   They initiate a new "Inter-Subsidiary Transfer".
    -   The UI prompts for the destination (Farming subsidiary/area), estimated biomass, and price per kg.
    -   On submission, a `BatchTransfer` and a `PENDING` `InterSubsidiaryTransaction` are created. A placeholder `ShipTransportReport` is also created and linked.

2.  **Execution (Ship Captain/Crew):**
    -   The Logistics team (or Captain) is notified of a pending transport.
    -   They access the pending `ShipTransportReport` via a mobile-friendly UI.
    -   During and after the voyage, they fill in all required fields: ship details, crew, environmental readings, mortality, etc.
    -   Upon completion, they submit the report.

3.  **Completion (Farming Manager):**
    -   The Farming Manager is notified that a batch has arrived and a transaction is pending approval.
    -   They review the `ShipTransportReport` and the `InterSubsidiaryTransaction`.
    -   They confirm the `actual_biomass_kg` received.
    -   They approve the transaction, which updates the status to `COMPLETED` and calculates the `actual_total_value`. The financial record is now finalized.

---

## 4. Implementation Phases & Timeline

| Phase | Title | Key Tasks | Estimated Duration |
| :---- | :---- | :---- | :--- |
| **1** | **Backend Foundation** | - Create `transactions` app. <br>- Implement `InterSubsidiaryTransaction` and `ShipTransportReport` models. <br>- Create database migrations. <br>- Set up basic API ViewSets and Serializers (CRUD). | **2 Weeks** |
| **2** | **Backend Logic & Integration** | - Extend `BatchTransferSerializer` to handle nested creation. <br>- Implement the `approve` action on the transaction endpoint. <br>- Implement business logic for status changes and calculations. <br>- Set up permissions for all new endpoints. | **2 Weeks** |
| **3** | **Frontend UI/UX** | - Design and build the UI for initiating an inter-subsidiary transfer. <br>- Develop a mobile-first, responsive form for the `ShipTransportReport`. <br>- Create a dashboard/view for managers to see and approve pending transactions. | **3 Weeks** |
| **4** | **Testing & Deployment** | - Write unit and integration tests for backend logic. <br>- Conduct end-to-end testing of the entire workflow. <br>- User Acceptance Testing (UAT) with key personas. <br>- Deploy to production. | **1 Week** |
| **Total** | | | **8 Weeks** |

---

## 5. Technical Specifications

-   **Permissions:**
    -   **Initiation:** Only users with a `Manager` role in the `Freshwater` subsidiary can initiate a transfer.
    -   **Reporting:** Only users in the `Logistics` subsidiary can fill out the `ShipTransportReport`.
    -   **Approval:** Only users with a `Manager` role in the `Farming` subsidiary can approve the final transaction.
-   **Validation:**
    -   `price_per_kg` and `biomass_kg` must be positive numbers.
    -   A `ShipTransportReport` cannot be submitted unless all required fields are filled.
    -   A transaction cannot be approved until the associated `ShipTransportReport` is completed.
-   **Notifications:**
    -   A notification system (e.g., in-app or email) should be implemented to alert users of pending tasks (e.g., "Transport Report for Batch X is ready to be filled", "Transaction Y is pending your approval").

---

## 6. Success Metrics

-   **Adoption Rate:** >95% of all freshwater-to-sea transfers are processed through the new system within 3 months of launch.
-   **Time Reduction:** An average reduction of 75% in the administrative time required for a single transfer (compared to the manual process).
-   **Data Accuracy:** Reduction in financial reconciliation errors related to inter-subsidiary transfers by 90%.
-   **User Satisfaction:** Positive feedback from Freshwater Managers, Farming Managers, and Ship Crews regarding ease of use and efficiency.

