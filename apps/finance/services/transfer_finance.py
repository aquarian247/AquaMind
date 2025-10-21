"""
Transfer finance service for intercompany transaction creation.

Handles the creation of IntercompanyTransaction records when batch transfers
complete, including pricing calculation and policy lookup.
"""

from decimal import Decimal
from typing import Optional
import logging

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.finance.models import (
    DimCompany,
    IntercompanyPolicy,
    IntercompanyTransaction,
)
from apps.finance.services.dimension_mapping import DimensionMappingService


logger = logging.getLogger(__name__)


class TransferFinanceError(Exception):
    """Base exception for transfer finance errors."""
    pass


class PricingPolicyNotFoundError(TransferFinanceError):
    """Raised when no pricing policy exists for the transfer."""
    pass


class InvalidTransferDataError(TransferFinanceError):
    """Raised when transfer data is invalid or incomplete."""
    pass


class TransferFinanceService:
    """
    Service for creating intercompany transactions from batch transfers.
    
    Handles:
    - Pricing policy lookup
    - Transfer value calculation
    - Transaction creation
    - Validation
    """

    def __init__(self, workflow):
        """
        Initialize service for a specific workflow.
        
        Args:
            workflow: BatchTransferWorkflow instance
        """
        self.workflow = workflow
        self.source_company: Optional[DimCompany] = None
        self.dest_company: Optional[DimCompany] = None
        self.pricing_policy: Optional[IntercompanyPolicy] = None

    def create_transaction(self) -> IntercompanyTransaction:
        """
        Create an IntercompanyTransaction for this workflow.
        
        Returns:
            Created IntercompanyTransaction instance
        
        Raises:
            InvalidTransferDataError: If transfer data is invalid
            PricingPolicyNotFoundError: If no pricing policy found
            TransferFinanceError: For other errors
        
        Steps:
            1. Validate workflow is intercompany
            2. Get source/dest companies
            3. Lookup pricing policy
            4. Calculate transfer value
            5. Create transaction in PENDING state
        """
        with transaction.atomic():
            # Step 1: Validate
            self._validate_workflow()
            
            # Step 2: Get companies
            self._determine_companies()
            
            # Step 3: Get pricing policy
            self.pricing_policy = self._get_pricing_policy()
            
            # Step 4: Calculate value
            amount = self._calculate_transfer_value()
            
            # Step 5: Create transaction
            tx = self._create_transaction_record(amount)
            
            logger.info(
                f"Created intercompany transaction {tx.tx_id} for "
                f"workflow {self.workflow.workflow_number}: "
                f"{self.source_company.display_name} → "
                f"{self.dest_company.display_name}, "
                f"{amount} {tx.currency}"
            )
            
            return tx

    def _validate_workflow(self) -> None:
        """Validate that workflow can have a transaction created."""
        if not self.workflow.is_intercompany:
            raise InvalidTransferDataError(
                f"Workflow {self.workflow.workflow_number} is not "
                "marked as intercompany"
            )
        
        if self.workflow.status != 'COMPLETED':
            raise InvalidTransferDataError(
                f"Workflow {self.workflow.workflow_number} is not "
                f"completed (status: {self.workflow.status})"
            )
        
        if self.workflow.total_transferred_count == 0:
            raise InvalidTransferDataError(
                f"Workflow {self.workflow.workflow_number} has no "
                "transferred fish"
            )
        
        if self.workflow.total_biomass_kg == 0:
            raise InvalidTransferDataError(
                f"Workflow {self.workflow.workflow_number} has no "
                "biomass transferred"
            )

    def _determine_companies(self) -> None:
        """Determine source and destination companies from workflow actions."""
        actions = self.workflow.actions.select_related(
            'source_assignment__container__hall__freshwater_station',
            'source_assignment__container__area',
            'dest_assignment__container__hall__freshwater_station',
            'dest_assignment__container__area',
        ).all()
        
        source_company, dest_company = (
            DimensionMappingService.get_companies_for_workflow_actions(
                actions
            )
        )
        
        if not source_company:
            raise InvalidTransferDataError(
                f"Could not determine source company for workflow "
                f"{self.workflow.workflow_number}"
            )
        
        if not dest_company:
            raise InvalidTransferDataError(
                f"Could not determine destination company for workflow "
                f"{self.workflow.workflow_number}"
            )
        
        self.source_company = source_company
        self.dest_company = dest_company

    def _get_pricing_policy(self) -> IntercompanyPolicy:
        """
        Lookup the pricing policy for this transfer.
        
        Returns:
            IntercompanyPolicy instance
        
        Raises:
            PricingPolicyNotFoundError: If no policy found
        
        Lookup criteria:
            - pricing_basis = LIFECYCLE
            - from_company = source_company
            - to_company = dest_company
            - lifecycle_stage = SOURCE lifecycle stage (what's being sold)
        
        Note: We use source_lifecycle_stage because that's what's being
        transferred/sold. E.g., Post-Smolt pricing for Post-Smolt fish,
        even though they'll become Adult in the destination.
        """
        if not self.workflow.source_lifecycle_stage:
            raise InvalidTransferDataError(
                f"Workflow {self.workflow.workflow_number} has no "
                "source lifecycle stage"
            )
        
        policy = IntercompanyPolicy.objects.filter(
            from_company=self.source_company,
            to_company=self.dest_company,
            pricing_basis=IntercompanyPolicy.PricingBasis.LIFECYCLE,
            lifecycle_stage=self.workflow.source_lifecycle_stage,
        ).first()
        
        if not policy:
            raise PricingPolicyNotFoundError(
                f"No pricing policy found for transfer: "
                f"{self.source_company.display_name} → "
                f"{self.dest_company.display_name} "
                f"(lifecycle: {self.workflow.source_lifecycle_stage.name})"
            )
        
        return policy

    def _calculate_transfer_value(self) -> Decimal:
        """
        Calculate the monetary value of the transfer.
        
        Returns:
            Transfer value as Decimal
        
        Calculation:
            For STANDARD pricing: total_biomass_kg × price_per_kg
            For COST_PLUS: Not yet implemented
            For MARKET: Not yet implemented
        """
        if self.pricing_policy.method == IntercompanyPolicy.Method.STANDARD:
            if not self.pricing_policy.price_per_kg:
                raise InvalidTransferDataError(
                    f"Policy {self.pricing_policy.policy_id} has "
                    "STANDARD method but no price_per_kg"
                )
            
            value = (
                self.workflow.total_biomass_kg *
                self.pricing_policy.price_per_kg
            )
            
            # Round to 2 decimal places
            return value.quantize(Decimal('0.01'))
        
        else:
            # MARKET and COST_PLUS methods not yet implemented
            raise NotImplementedError(
                f"Pricing method {self.pricing_policy.method} not yet "
                "implemented for transfer workflows"
            )

    def _create_transaction_record(
        self,
        amount: Decimal
    ) -> IntercompanyTransaction:
        """
        Create the IntercompanyTransaction database record.
        
        Args:
            amount: Calculated transaction amount
        
        Returns:
            Created IntercompanyTransaction instance
        """
        workflow_ct = ContentType.objects.get_for_model(
            self.workflow.__class__
        )
        
        # Determine currency from destination company
        currency = self.dest_company.currency or 'EUR'
        
        # Use actual completion date or today
        posting_date = (
            self.workflow.actual_completion_date or
            timezone.now().date()
        )
        
        tx = IntercompanyTransaction.objects.create(
            content_type=workflow_ct,
            object_id=self.workflow.id,
            policy=self.pricing_policy,
            posting_date=posting_date,
            amount=amount,
            currency=currency,
            state=IntercompanyTransaction.State.PENDING,
        )
        
        return tx

