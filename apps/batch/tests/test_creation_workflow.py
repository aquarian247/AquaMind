"""
Tests for Batch Creation Workflows.

Tests the complete lifecycle of batch creation from egg delivery.
"""
from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from apps.infrastructure.models import Geography, Area, ContainerType, Container
from apps.batch.models import (
    Species,
    LifeCycleStage,
    Batch,
    BatchContainerAssignment,
    BatchCreationWorkflow,
    CreationAction,
)
from apps.broodstock.models import EggProduction, EggSupplier, BreedingPlan

User = get_user_model()


class BatchCreationWorkflowTestCase(TestCase):
    """Test cases for batch creation workflow functionality."""
    
    def setUp(self):
        """Set up test data."""
        # Create user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        
        # Create geography and area
        self.geography = Geography.objects.create(
            name='Test Faroe Islands',
            description='Test geography'
        )
        self.area = Area.objects.create(
            name='Test Station',
            geography=self.geography,
            latitude=Decimal('62.0'),
            longitude=Decimal('-6.7'),
            max_biomass=Decimal('500000.0')
        )
        
        # Create container type and containers
        self.container_type = ContainerType.objects.create(
            name='TRAY',
            category='TRAY',
            max_volume_m3=Decimal('5.0'),
            description='Incubation Tray'
        )
        
        self.tray1 = Container.objects.create(
            name='TRAY-01',
            container_type=self.container_type,
            area=self.area,
            volume_m3=Decimal('2.5'),
            max_biomass_kg=Decimal('50.0'),
            active=True
        )
        
        self.tray2 = Container.objects.create(
            name='TRAY-02',
            container_type=self.container_type,
            area=self.area,
            volume_m3=Decimal('2.5'),
            max_biomass_kg=Decimal('50.0'),
            active=True
        )
        
        # Create species and lifecycle stage
        self.species = Species.objects.create(
            name='Atlantic Salmon',
            scientific_name='Salmo salar'
        )
        self.egg_stage = LifeCycleStage.objects.create(
            name='Egg&Alevin',
            species=self.species,
            order=1,
            typical_duration_days=90
        )
        
        # Create external supplier
        self.external_supplier = EggSupplier.objects.create(
            name='Test Egg Supplier',
            contact_details='Test Contact Info'
        )
    
    def test_create_workflow_with_batch(self):
        """Test that creating workflow also creates batch."""
        workflow = BatchCreationWorkflow.objects.create(
            workflow_number='CRT-2025-001',
            batch=Batch.objects.create(
                batch_number='TEST-2025-001',
                species=self.species,
                lifecycle_stage=self.egg_stage,
                status='PLANNED',
                start_date=date.today()
            ),
            status='DRAFT',
            egg_source_type='EXTERNAL',
            external_supplier=self.external_supplier,
            external_cost_per_thousand=Decimal('120.00'),
            total_eggs_planned=500000,
            planned_start_date=date.today(),
            planned_completion_date=date.today() + timedelta(days=7),
            created_by=self.user
        )
        
        self.assertIsNotNone(workflow.id)
        self.assertIsNotNone(workflow.batch)
        self.assertEqual(workflow.batch.status, 'PLANNED')
        self.assertEqual(workflow.status, 'DRAFT')
        self.assertEqual(workflow.total_actions, 0)
        self.assertEqual(workflow.actions_completed, 0)
    
    def test_workflow_validation_internal_source(self):
        """Test validation for internal egg source (simplified)."""
        # For simplicity, just test that we can create a workflow
        # with egg_source_type='INTERNAL' and it validates
        # (full broodstock setup is complex and not critical for this test)
        workflow = self._create_test_workflow()
        workflow.egg_source_type = 'INTERNAL'
        workflow.external_supplier = None
        
        # This will fail validation without egg_production
        with self.assertRaises(ValidationError):
            workflow.full_clean()
    
    def test_workflow_validation_external_source_missing_supplier(self):
        """Test that external source requires supplier."""
        batch = Batch.objects.create(
            batch_number='TEST-2025-003',
            species=self.species,
            lifecycle_stage=self.egg_stage,
            status='PLANNED',
            start_date=date.today()
        )
        
        workflow = BatchCreationWorkflow(
            workflow_number='CRT-2025-003',
            batch=batch,
            status='DRAFT',
            egg_source_type='EXTERNAL',
            # Missing external_supplier!
            total_eggs_planned=500000,
            planned_start_date=date.today(),
            planned_completion_date=date.today() + timedelta(days=7),
        )
        
        with self.assertRaises(ValidationError) as cm:
            workflow.full_clean()
        
        self.assertIn('external_supplier', cm.exception.message_dict)
    
    def test_can_add_actions(self):
        """Test can_add_actions() method."""
        workflow = self._create_test_workflow()
        
        # DRAFT status - can add
        workflow.status = 'DRAFT'
        workflow.save()
        self.assertTrue(workflow.can_add_actions())
        
        # PLANNED status - can add
        workflow.status = 'PLANNED'
        workflow.save()
        self.assertTrue(workflow.can_add_actions())
        
        # IN_PROGRESS status - cannot add
        workflow.status = 'IN_PROGRESS'
        workflow.save()
        self.assertFalse(workflow.can_add_actions())
        
        # COMPLETED status - cannot add
        workflow.status = 'COMPLETED'
        workflow.save()
        self.assertFalse(workflow.can_add_actions())
    
    def test_can_plan(self):
        """Test can_plan() method."""
        workflow = self._create_test_workflow()
        
        # DRAFT with no actions - cannot plan
        self.assertFalse(workflow.can_plan())
        
        # Add an action
        self._add_action(workflow, self.tray1, 100000)
        workflow.refresh_from_db()
        
        # DRAFT with actions - can plan
        self.assertTrue(workflow.can_plan())
        
        # PLANNED - cannot plan again
        workflow.status = 'PLANNED'
        workflow.save()
        self.assertFalse(workflow.can_plan())
    
    def test_can_cancel(self):
        """Test can_cancel() method."""
        workflow = self._create_test_workflow()
        action = self._add_action(workflow, self.tray1, 100000)
        
        # DRAFT with no executed actions - can cancel
        self.assertTrue(workflow.can_cancel())
        
        # Execute an action
        action.execute(
            mortality_on_arrival=1000,
            executed_by=self.user
        )
        workflow.refresh_from_db()
        
        # After action executed - cannot cancel
        self.assertFalse(workflow.can_cancel())
    
    def test_cancel_workflow(self):
        """Test cancelling a workflow."""
        workflow = self._create_test_workflow()
        self._add_action(workflow, self.tray1, 100000)
        
        # Cancel the workflow
        workflow.cancel(reason='Test cancellation', user=self.user)
        
        self.assertEqual(workflow.status, 'CANCELLED')
        self.assertEqual(workflow.cancellation_reason, 'Test cancellation')
        self.assertEqual(workflow.cancelled_by, self.user)
        self.assertIsNotNone(workflow.cancelled_at)
        
        # Batch should also be cancelled
        self.assertEqual(workflow.batch.status, 'CANCELLED')
    
    def test_cancel_after_execution_fails(self):
        """Test that cancellation fails after action execution."""
        workflow = self._create_test_workflow()
        action = self._add_action(workflow, self.tray1, 100000)
        
        # Execute the action
        action.execute(mortality_on_arrival=1000, executed_by=self.user)
        workflow.refresh_from_db()
        
        # Try to cancel - should fail
        with self.assertRaises(ValidationError):
            workflow.cancel(reason='Cannot cancel', user=self.user)
    
    def test_update_progress(self):
        """Test progress calculation."""
        workflow = self._create_test_workflow()
        self._add_action(workflow, self.tray1, 100000)
        self._add_action(workflow, self.tray2, 150000)
        workflow.refresh_from_db()
        
        # 0 / 2 = 0%
        workflow.update_progress()
        self.assertEqual(workflow.progress_percentage, Decimal('0.00'))
        
        # Execute one action
        action1 = workflow.actions.first()
        action1.execute(mortality_on_arrival=1000, executed_by=self.user)
        workflow.refresh_from_db()
        
        # 1 / 2 = 50%
        self.assertEqual(workflow.progress_percentage, Decimal('50.00'))
    
    def test_workflow_completion(self):
        """Test workflow completion triggers batch status change."""
        workflow = self._create_test_workflow()
        action1 = self._add_action(workflow, self.tray1, 100000)
        action2 = self._add_action(workflow, self.tray2, 150000)
        workflow.refresh_from_db()
        
        # Execute first action
        action1.execute(mortality_on_arrival=1000, executed_by=self.user)
        workflow.refresh_from_db()
        
        # Workflow in progress, batch receiving
        self.assertEqual(workflow.status, 'IN_PROGRESS')
        self.assertEqual(workflow.batch.status, 'RECEIVING')
        
        # Execute second action
        action2.execute(mortality_on_arrival=2000, executed_by=self.user)
        workflow.refresh_from_db()
        
        # Workflow completed, batch active
        self.assertEqual(workflow.status, 'COMPLETED')
        self.assertEqual(workflow.batch.status, 'ACTIVE')
        self.assertIsNotNone(workflow.actual_completion_date)
        
        # Check totals
        self.assertEqual(workflow.total_eggs_received, 247000)  # 100k + 150k - 3k mortality
        self.assertEqual(workflow.total_mortality_on_arrival, 3000)
    
    def test_action_execution_updates_container(self):
        """Test that executing action updates destination container."""
        workflow = self._create_test_workflow()
        action = self._add_action(workflow, self.tray1, 100000)
        
        # Before execution
        assignment = action.dest_assignment
        self.assertEqual(assignment.population_count, 0)
        self.assertFalse(assignment.is_active)
        
        # Execute action
        action.execute(mortality_on_arrival=1000, executed_by=self.user)
        assignment.refresh_from_db()
        
        # After execution
        self.assertEqual(assignment.population_count, 99000)  # 100k - 1k
        self.assertTrue(assignment.is_active)
    
    def test_multiple_actions_same_container(self):
        """Test multiple deliveries to same container (Action 8 & 13 to Tray 08 pattern)."""
        workflow = self._create_test_workflow()
        
        # Add two actions to same container
        action1 = self._add_action(workflow, self.tray1, 80000)
        action2 = self._add_action(workflow, self.tray1, 70000)
        
        # They should share the same assignment
        self.assertEqual(action1.dest_assignment, action2.dest_assignment)
        
        # Execute both
        action1.execute(mortality_on_arrival=800, executed_by=self.user)
        action2.execute(mortality_on_arrival=700, executed_by=self.user)
        
        # Check total population in container
        assignment = action1.dest_assignment
        assignment.refresh_from_db()
        self.assertEqual(assignment.population_count, 148500)  # 79200 + 69300
    
    def _create_test_workflow(self):
        """Helper to create a test workflow."""
        batch = Batch.objects.create(
            batch_number=f'TEST-{date.today().year}-{Batch.objects.count()+1:03d}',
            species=self.species,
            lifecycle_stage=self.egg_stage,
            status='PLANNED',
            start_date=date.today()
        )
        
        workflow = BatchCreationWorkflow.objects.create(
            workflow_number=f'CRT-{date.today().year}-{BatchCreationWorkflow.objects.count()+1:03d}',
            batch=batch,
            status='DRAFT',
            egg_source_type='EXTERNAL',
            external_supplier=self.external_supplier,
            external_cost_per_thousand=Decimal('120.00'),
            total_eggs_planned=500000,
            planned_start_date=date.today(),
            planned_completion_date=date.today() + timedelta(days=7),
            created_by=self.user
        )
        
        return workflow
    
    def _add_action(self, workflow, container, egg_count):
        """Helper to add an action to a workflow."""
        # Get or create assignment
        assignment, created = BatchContainerAssignment.objects.get_or_create(
            batch=workflow.batch,
            container=container,
            lifecycle_stage=workflow.batch.lifecycle_stage,
            defaults={
                'population_count': 0,
                'biomass_kg': Decimal('0.00'),
                'assignment_date': workflow.planned_start_date,
                'is_active': False,
            }
        )
        
        action = CreationAction.objects.create(
            workflow=workflow,
            action_number=workflow.total_actions + 1,
            dest_assignment=assignment,
            egg_count_planned=egg_count,
            expected_delivery_date=date.today() + timedelta(days=workflow.total_actions),
        )
        
        workflow.total_actions += 1
        workflow.save(update_fields=['total_actions'])
        
        return action

