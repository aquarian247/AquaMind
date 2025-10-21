"""
Tests for transfer finance service layer.

Tests the complete integration of:
- DimensionMappingService
- TransferFinanceService  
- BatchTransferWorkflow finance integration
"""

from decimal import Decimal

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.utils import timezone

from apps.batch.models import (
    Batch,
    BatchContainerAssignment,
    BatchTransferWorkflow,
    LifeCycleStage,
    TransferAction,
)
from apps.finance.models import (
    DimCompany,
    DimSite,
    IntercompanyPolicy,
    IntercompanyTransaction,
)
from apps.finance.services.dimension_mapping import DimensionMappingService
from apps.finance.services.transfer_finance import (
    InvalidTransferDataError,
    PricingPolicyNotFoundError,
    TransferFinanceService,
)
from apps.infrastructure.models import (
    Container,
    ContainerType,
    FreshwaterStation,
    Geography,
    Hall,
)
from apps.users.models import Subsidiary


class TransferFinanceServiceTest(TestCase):
    """
    Test transfer finance service integration.
    
    Scenario: Post-Smolt transfer from Freshwater to Farming
    """

    @classmethod
    def setUpTestData(cls):
        """Set up test data for all tests."""
        # Create user
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create geography
        cls.geography = Geography.objects.create(
            name='Test Norway',
            description='Test geography for Norway',
        )
        
        # Create companies
        cls.freshwater_company = DimCompany.objects.create(
            geography=cls.geography,
            subsidiary=Subsidiary.FRESHWATER,
            display_name='Test Freshwater Norway',
            currency='NOK',
        )
        
        cls.farming_company = DimCompany.objects.create(
            geography=cls.geography,
            subsidiary=Subsidiary.FARMING,
            display_name='Test Farming Norway',
            currency='NOK',
        )
        
        # Create freshwater station and site
        cls.station = FreshwaterStation.objects.create(
            geography=cls.geography,
            name='Test Station',
            station_type='FRESHWATER',
            latitude=Decimal('60.0'),
            longitude=Decimal('10.0'),
            description='Test freshwater station',
        )
        
        cls.freshwater_site = DimSite.objects.create(
            source_model=DimSite.SourceModel.STATION,
            source_pk=cls.station.id,
            company=cls.freshwater_company,
            site_name=cls.station.name,
        )
        
        # Create farming area and site for destination
        from apps.infrastructure.models import Area
        cls.farming_area = Area.objects.create(
            geography=cls.geography,
            name='Test Farming Area',
            latitude=Decimal('61.0'),
            longitude=Decimal('11.0'),
            max_biomass=Decimal('10000.00'),
        )
        
        cls.farming_site = DimSite.objects.create(
            source_model=DimSite.SourceModel.AREA,
            source_pk=cls.farming_area.id,
            company=cls.farming_company,
            site_name=cls.farming_area.name,
        )
        
        # Create container type
        cls.container_type = ContainerType.objects.create(
            name='Test Tank',
            category='TANK',
            max_volume_m3=Decimal('100.00'),
            description='Test tank type',
        )
        
        # Create hall and containers
        cls.hall = Hall.objects.create(
            freshwater_station=cls.station,
            name='Test Hall H1',
            description='Test hall for transfer tests',
            area_sqm=Decimal('1000.00'),
        )
        
        cls.source_container = Container.objects.create(
            name='Source Tank 1',
            container_type=cls.container_type,
            hall=cls.hall,
            volume_m3=Decimal('100.00'),
            max_biomass_kg=Decimal('500.00'),
        )
        
        # Destination container in farming area (different company for intercompany transfer)
        cls.dest_container = Container.objects.create(
            name='Dest Tank 1',
            container_type=cls.container_type,
            area=cls.farming_area,  # Different location → different company
            volume_m3=Decimal('100.00'),
            max_biomass_kg=Decimal('500.00'),
        )
        
        # Create lifecycle stages with correct field names
        from apps.batch.models import Species
        cls.species = Species.objects.create(
            name='Test Salmon',
            scientific_name='Salmo test'
        )
        
        cls.post_smolt_stage = LifeCycleStage.objects.create(
            name='Post-Smolt',
            species=cls.species,
            order=5,
        )
        
        cls.adult_stage = LifeCycleStage.objects.create(
            name='Adult',
            species=cls.species,
            order=6,
        )
        
        # Create pricing policy
        cls.policy = IntercompanyPolicy.objects.create(
            from_company=cls.freshwater_company,
            to_company=cls.farming_company,
            pricing_basis=IntercompanyPolicy.PricingBasis.LIFECYCLE,
            lifecycle_stage=cls.post_smolt_stage,
            method=IntercompanyPolicy.Method.STANDARD,
            price_per_kg=Decimal('168.00'),  # NOK
        )
        
        # Create batch with correct FK references
        cls.batch = Batch.objects.create(
            batch_number='TEST-2024-001',
            species=cls.species,
            lifecycle_stage=cls.post_smolt_stage,
            status='ACTIVE',
            batch_type='STANDARD',
            start_date=timezone.now().date(),
        )
        
        # Create workflow
        cls.workflow = BatchTransferWorkflow.objects.create(
            workflow_number='TRF-2024-TEST',
            batch=cls.batch,
            workflow_type='LIFECYCLE_TRANSITION',
            source_lifecycle_stage=cls.post_smolt_stage,
            dest_lifecycle_stage=cls.adult_stage,
            planned_start_date='2024-10-20',
            initiated_by=cls.user,
            status='IN_PROGRESS',
            is_intercompany=True,
            total_actions_planned=1,
        )
        
        # Create assignments with correct field name
        cls.source_assignment = BatchContainerAssignment.objects.create(
            batch=cls.batch,
            container=cls.source_container,
            lifecycle_stage=cls.post_smolt_stage,
            population_count=1000,
            biomass_kg=Decimal('50.00'),
            assignment_date='2024-10-15',
            is_active=True,
        )
        
        cls.dest_assignment = BatchContainerAssignment.objects.create(
            batch=cls.batch,
            container=cls.dest_container,
            lifecycle_stage=cls.adult_stage,
            population_count=0,
            biomass_kg=Decimal('0.00'),
            assignment_date='2024-10-20',
            is_active=True,
        )
        
        # Create transfer action
        cls.action = TransferAction.objects.create(
            workflow=cls.workflow,
            action_number=1,
            source_assignment=cls.source_assignment,
            dest_assignment=cls.dest_assignment,
            source_population_before=1000,
            transferred_count=1000,
            transferred_biomass_kg=Decimal('50.00'),
            status='PENDING',
        )

    def test_dimension_mapping_service_gets_company_from_container(self):
        """Test that DimensionMappingService correctly maps container to company."""
        company = DimensionMappingService.get_company_for_container(
            self.source_container
        )
        
        self.assertEqual(company.company_id, self.freshwater_company.company_id)
        self.assertEqual(company.subsidiary, Subsidiary.FRESHWATER)

    def test_dimension_mapping_service_gets_companies_from_actions(self):
        """Test getting source and dest companies from workflow actions."""
        actions = self.workflow.actions.all()
        
        source_company, dest_company = (
            DimensionMappingService.get_companies_for_workflow_actions(actions)
        )
        
        self.assertEqual(source_company.company_id, self.freshwater_company.company_id)
        self.assertEqual(dest_company.company_id, self.farming_company.company_id)

    def test_validate_intercompany_transfer_returns_false_for_same_company(self):
        """Test that same-company transfers are not marked intercompany."""
        is_intercompany = DimensionMappingService.validate_intercompany_transfer(
            self.freshwater_company,
            self.freshwater_company,
        )
        
        self.assertFalse(is_intercompany)

    def test_validate_intercompany_transfer_returns_true_for_different_companies(self):
        """Test that different-company transfers are marked intercompany."""
        is_intercompany = DimensionMappingService.validate_intercompany_transfer(
            self.freshwater_company,
            self.farming_company,
        )
        
        self.assertTrue(is_intercompany)

    def test_transfer_finance_service_validates_workflow_status(self):
        """Test that service validates workflow is COMPLETED."""
        # Workflow is IN_PROGRESS
        service = TransferFinanceService(self.workflow)
        
        with self.assertRaises(InvalidTransferDataError) as cm:
            service.create_transaction()
        
        self.assertIn('not completed', str(cm.exception))

    def test_transfer_finance_service_requires_biomass(self):
        """Test that service requires non-zero biomass."""
        self.workflow.status = 'COMPLETED'
        self.workflow.total_biomass_kg = Decimal('0.00')
        self.workflow.save()
        
        service = TransferFinanceService(self.workflow)
        
        with self.assertRaises(InvalidTransferDataError) as cm:
            service.create_transaction()
        
        # Error message changed - check for either variant
        error_msg = str(cm.exception).lower()
        self.assertTrue('no biomass' in error_msg or 'no transferred fish' in error_msg)

    def test_transfer_finance_service_creates_transaction(self):
        """Test successful transaction creation from completed workflow."""
        # Complete the workflow
        self.workflow.status = 'COMPLETED'
        self.workflow.total_transferred_count = 1000
        self.workflow.total_biomass_kg = Decimal('50.00')
        self.workflow.actual_completion_date = '2024-10-20'
        self.workflow.save()
        
        # Create transaction
        service = TransferFinanceService(self.workflow)
        tx = service.create_transaction()
        
        # Verify transaction created
        self.assertIsNotNone(tx.tx_id)
        self.assertEqual(tx.state, IntercompanyTransaction.State.PENDING)
        
        # Verify polymorphic source
        workflow_ct = ContentType.objects.get_for_model(BatchTransferWorkflow)
        self.assertEqual(tx.content_type, workflow_ct)
        self.assertEqual(tx.object_id, self.workflow.id)
        
        # Verify amount calculation
        expected_amount = Decimal('50.00') * Decimal('168.00')  # biomass * price
        self.assertEqual(tx.amount, expected_amount.quantize(Decimal('0.01')))
        
        # Verify currency
        self.assertEqual(tx.currency, 'NOK')
        
        # Verify policy
        self.assertEqual(tx.policy, self.policy)

    def test_transfer_finance_service_requires_pricing_policy(self):
        """Test that service requires a pricing policy to exist."""
        # Delete the policy
        self.policy.delete()
        
        # Complete workflow
        self.workflow.status = 'COMPLETED'
        self.workflow.total_transferred_count = 1000
        self.workflow.total_biomass_kg = Decimal('50.00')
        self.workflow.save()
        
        service = TransferFinanceService(self.workflow)
        
        with self.assertRaises(PricingPolicyNotFoundError) as cm:
            service.create_transaction()
        
        self.assertIn('No pricing policy found', str(cm.exception))

    def test_intercompany_transaction_approve_method(self):
        """Test the approve method on IntercompanyTransaction."""
        # Create a transaction
        workflow_ct = ContentType.objects.get_for_model(BatchTransferWorkflow)
        
        tx = IntercompanyTransaction.objects.create(
            content_type=workflow_ct,
            object_id=self.workflow.id,
            policy=self.policy,
            posting_date='2024-10-20',
            amount=Decimal('8400.00'),
            currency='NOK',
            state=IntercompanyTransaction.State.PENDING,
        )
        
        # Approve it
        tx.approve(user=self.user)
        
        # Verify state changed
        self.assertEqual(tx.state, IntercompanyTransaction.State.POSTED)
        self.assertEqual(tx.approved_by, self.user)
        self.assertIsNotNone(tx.approval_date)

    def test_workflow_auto_creates_transaction_on_completion(self):
        """Test that workflow automatically creates transaction when completed."""
        # Update workflow totals
        self.workflow.total_transferred_count = 1000
        self.workflow.total_biomass_kg = Decimal('50.00')
        self.workflow.save()
        
        # Execute action (triggers workflow completion)
        self.action.execute(executed_by=self.user, mortality_count=0)
        
        # Refresh workflow
        self.workflow.refresh_from_db()
        
        # Verify workflow is COMPLETED
        self.assertEqual(self.workflow.status, 'COMPLETED')
        
        # Verify transaction was created
        self.assertIsNotNone(self.workflow.finance_transaction)
        
        # Verify transaction details
        tx = self.workflow.finance_transaction
        self.assertEqual(tx.state, IntercompanyTransaction.State.PENDING)
        self.assertEqual(tx.currency, 'NOK')
        expected_amount = Decimal('50.00') * Decimal('168.00')
        self.assertEqual(tx.amount, expected_amount.quantize(Decimal('0.01')))

