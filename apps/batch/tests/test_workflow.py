"""
Tests for BatchTransferWorkflow and TransferAction models.

This module tests the workflow state machine, action execution,
and progress tracking functionality.
"""
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from apps.batch.models import (
    BatchTransferWorkflow,
    TransferAction,
)
from apps.batch.tests.models.test_utils import (
    create_test_species,
    create_test_lifecycle_stage,
    create_test_batch,
    create_test_container,
    create_test_batch_container_assignment,
)


class TestBatchTransferWorkflow(TestCase):
    """Test BatchTransferWorkflow model and state machine."""

    @classmethod
    def setUpTestData(cls):
        """Create test data for workflows."""
        # Create user
        cls.user = User.objects.create_user(username='testuser')
        
        # Create species and lifecycle stages
        cls.species = create_test_species(name='Atlantic Salmon')
        cls.fry_stage = create_test_lifecycle_stage(
            name='Fry',
            species=cls.species,
            order=1
        )
        cls.parr_stage = create_test_lifecycle_stage(
            name='Parr',
            species=cls.species,
            order=2
        )
        
        # Create batch
        cls.batch = create_test_batch(
            batch_number='TEST-001',
            species=cls.species,
            lifecycle_stage=cls.fry_stage
        )
        
        # Create containers
        cls.source_container = create_test_container(name='Tank-A1')
        cls.dest_container = create_test_container(name='Tank-B1')
    
    def setUp(self):
        """Set up test assignments for each test."""
        # Create source assignment
        self.source_assignment = create_test_batch_container_assignment(
            batch=self.batch,
            container=self.source_container,
            lifecycle_stage=self.fry_stage,
            population_count=1000,
            avg_weight_g=Decimal('5.0')
        )

        # Create dest assignment
        self.dest_assignment = create_test_batch_container_assignment(
            batch=self.batch,
            container=self.dest_container,
            lifecycle_stage=self.parr_stage,
            population_count=0,
            avg_weight_g=Decimal('5.0')
        )

    def test_workflow_creation(self):
        """Test creating a workflow in DRAFT status."""
        workflow = BatchTransferWorkflow.objects.create(
            workflow_number='TRF-2024-001',
            batch=self.batch,
            workflow_type='LIFECYCLE_TRANSITION',
            source_lifecycle_stage=self.fry_stage,
            dest_lifecycle_stage=self.parr_stage,
            planned_start_date=timezone.now().date(),
            initiated_by=self.user
        )

        self.assertEqual(workflow.status, 'DRAFT')
        self.assertEqual(workflow.completion_percentage, Decimal('0.00'))
        self.assertEqual(workflow.total_actions_planned, 0)
        self.assertEqual(workflow.actions_completed, 0)

    def test_add_action_to_workflow(self):
        """Test adding an action to a workflow."""
        workflow = BatchTransferWorkflow.objects.create(
            workflow_number='TRF-2024-002',
            batch=self.batch,
            workflow_type='LIFECYCLE_TRANSITION',
            source_lifecycle_stage=self.fry_stage,
            dest_lifecycle_stage=self.parr_stage,
            planned_start_date=timezone.now().date(),
            initiated_by=self.user
        )

        action = TransferAction.objects.create(
            workflow=workflow,
            action_number=1,
            source_assignment=self.source_assignment,
            dest_assignment=self.dest_assignment,
            source_population_before=1000,
            transferred_count=500,
            transferred_biomass_kg=Decimal('2.5')
        )

        # Refresh workflow
        workflow.refresh_from_db()

        self.assertEqual(workflow.total_actions_planned, 1)
        self.assertEqual(action.status, 'PENDING')

    def test_workflow_plan_transition(self):
        """Test transitioning workflow from DRAFT to PLANNED."""
        workflow = BatchTransferWorkflow.objects.create(
            workflow_number='TRF-2024-003',
            batch=self.batch,
            workflow_type='LIFECYCLE_TRANSITION',
            source_lifecycle_stage=self.fry_stage,
            dest_lifecycle_stage=self.parr_stage,
            planned_start_date=timezone.now().date(),
            initiated_by=self.user
        )

        # Add an action
        TransferAction.objects.create(
            workflow=workflow,
            action_number=1,
            source_assignment=self.source_assignment,
            dest_assignment=self.dest_assignment,
            source_population_before=1000,
            transferred_count=500,
            transferred_biomass_kg=Decimal('2.5')
        )

        # Plan the workflow
        workflow.plan_workflow()

        self.assertEqual(workflow.status, 'PLANNED')

    def test_workflow_cannot_plan_without_actions(self):
        """Test that workflow cannot be planned without actions."""
        workflow = BatchTransferWorkflow.objects.create(
            workflow_number='TRF-2024-004',
            batch=self.batch,
            workflow_type='LIFECYCLE_TRANSITION',
            source_lifecycle_stage=self.fry_stage,
            dest_lifecycle_stage=self.parr_stage,
            planned_start_date=timezone.now().date(),
            initiated_by=self.user
        )

        with self.assertRaises(ValidationError):
            workflow.plan_workflow()

    def test_action_execution(self):
        """Test executing a transfer action."""
        workflow = BatchTransferWorkflow.objects.create(
            workflow_number='TRF-2024-005',
            batch=self.batch,
            workflow_type='LIFECYCLE_TRANSITION',
            source_lifecycle_stage=self.fry_stage,
            dest_lifecycle_stage=self.parr_stage,
            planned_start_date=timezone.now().date(),
            initiated_by=self.user,
            status='PLANNED'  # Start in PLANNED
        )

        action = TransferAction.objects.create(
            workflow=workflow,
            action_number=1,
            source_assignment=self.source_assignment,
            dest_assignment=self.dest_assignment,
            source_population_before=1000,
            transferred_count=500,
            transferred_biomass_kg=Decimal('2.5')
        )

        # Execute the action
        action.execute(
            executed_by=self.user,
            mortality_count=10,
            transfer_method='NET'
        )

        # Verify action status
        action.refresh_from_db()
        self.assertEqual(action.status, 'COMPLETED')
        self.assertEqual(action.mortality_during_transfer, 10)

        # Verify workflow auto-completed (only 1 action, so 100% done)
        workflow.refresh_from_db()
        self.assertEqual(workflow.status, 'COMPLETED')
        self.assertEqual(workflow.actions_completed, 1)
        self.assertEqual(workflow.completion_percentage, Decimal('100.00'))

        # Verify source population reduced
        self.source_assignment.refresh_from_db()
        # 1000 - 500 - 10 = 490
        self.assertEqual(self.source_assignment.population_count, 490)

        # Verify dest population increased
        self.dest_assignment.refresh_from_db()
        self.assertEqual(self.dest_assignment.population_count, 500)

    def test_workflow_auto_completion(self):
        """Test workflow auto-completes when all actions done."""
        workflow = BatchTransferWorkflow.objects.create(
            workflow_number='TRF-2024-006',
            batch=self.batch,
            workflow_type='LIFECYCLE_TRANSITION',
            source_lifecycle_stage=self.fry_stage,
            dest_lifecycle_stage=self.parr_stage,
            planned_start_date=timezone.now().date(),
            initiated_by=self.user,
            status='PLANNED'
        )

        action = TransferAction.objects.create(
            workflow=workflow,
            action_number=1,
            source_assignment=self.source_assignment,
            dest_assignment=self.dest_assignment,
            source_population_before=1000,
            transferred_count=500,
            transferred_biomass_kg=Decimal('2.5')
        )

        # Execute the action
        action.execute(executed_by=self.user)

        # Workflow should auto-complete
        workflow.refresh_from_db()
        self.assertEqual(workflow.status, 'COMPLETED')
        self.assertIsNotNone(workflow.actual_completion_date)
