"""
Tests for batch growth assimilation schema enhancements - Issue #112 Phase 1.

Tests migrations, field validation, and model behavior for:
- TransferAction measured weight fields
- Batch pinned_scenario field
"""
from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.batch.models import (
    Batch, Species, LifeCycleStage, BatchContainerAssignment,
    BatchTransferWorkflow, TransferAction
)
from apps.infrastructure.models import Area, Container, Geography
from apps.scenario.models import Scenario

User = get_user_model()


class TransferActionMeasuredFieldsTestCase(TestCase):
    """Test TransferAction measured weight fields for growth assimilation."""
    
    def setUp(self):
        """Set up test data."""
        # Create user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create geography and area
        self.geography = Geography.objects.create(
            name='Test Geography',
            code='TG'
        )
        self.area = Area.objects.create(
            name='Test Area',
            code='TA',
            geography=self.geography
        )
        
        # Create containers
        self.container_source = Container.objects.create(
            name='Source Tank',
            area=self.area,
            capacity=1000
        )
        self.container_dest = Container.objects.create(
            name='Dest Tank',
            area=self.area,
            capacity=1000
        )
        
        # Create species and lifecycle stages
        self.species = Species.objects.create(
            name='Test Species',
            scientific_name='Testus speciesus'
        )
        self.stage_fry = LifeCycleStage.objects.create(
            species=self.species,
            name='Fry',
            stage_number=1
        )
        self.stage_parr = LifeCycleStage.objects.create(
            species=self.species,
            name='Parr',
            stage_number=2
        )
        
        # Create batch
        self.batch = Batch.objects.create(
            batch_number='TEST-001',
            species=self.species,
            lifecycle_stage=self.stage_fry,
            start_date=timezone.now().date(),
            status='ACTIVE'
        )
        
        # Create source assignment
        self.source_assignment = BatchContainerAssignment.objects.create(
            batch=self.batch,
            container=self.container_source,
            lifecycle_stage=self.stage_fry,
            population_count=1000,
            avg_weight_g=Decimal('50.00'),
            biomass_kg=Decimal('50.00'),
            assignment_date=timezone.now().date()
        )
        
        # Create transfer workflow
        self.workflow = BatchTransferWorkflow.objects.create(
            batch=self.batch,
            workflow_type='LIFECYCLE_TRANSITION',
            source_lifecycle_stage=self.stage_fry,
            dest_lifecycle_stage=self.stage_parr,
            status='IN_PROGRESS'
        )
        
        # Create transfer action
        self.action = TransferAction.objects.create(
            workflow=self.workflow,
            action_number=1,
            source_assignment=self.source_assignment,
            source_population_before=1000,
            transferred_count=500,
            transferred_biomass_kg=Decimal('25.00'),
            status='PENDING'
        )
    
    def test_measured_avg_weight_field_exists(self):
        """Test that measured_avg_weight_g field exists and can be set."""
        self.action.measured_avg_weight_g = Decimal('52.50')
        self.action.save()
        self.action.refresh_from_db()
        self.assertEqual(self.action.measured_avg_weight_g, Decimal('52.50'))
    
    def test_measured_std_dev_field_exists(self):
        """Test that measured_std_dev_weight_g field exists."""
        self.action.measured_std_dev_weight_g = Decimal('2.50')
        self.action.save()
        self.action.refresh_from_db()
        self.assertEqual(self.action.measured_std_dev_weight_g, Decimal('2.50'))
    
    def test_measured_sample_size_field_exists(self):
        """Test that measured_sample_size field exists."""
        self.action.measured_sample_size = 30
        self.action.save()
        self.action.refresh_from_db()
        self.assertEqual(self.action.measured_sample_size, 30)
    
    def test_measured_avg_length_field_exists(self):
        """Test that measured_avg_length_cm field exists."""
        self.action.measured_avg_length_cm = Decimal('12.5')
        self.action.save()
        self.action.refresh_from_db()
        self.assertEqual(self.action.measured_avg_length_cm, Decimal('12.5'))
    
    def test_measured_notes_field_exists(self):
        """Test that measured_notes field exists."""
        notes = "Sample taken from middle of net. Weather: sunny, calm."
        self.action.measured_notes = notes
        self.action.save()
        self.action.refresh_from_db()
        self.assertEqual(self.action.measured_notes, notes)
    
    def test_selection_method_field_exists(self):
        """Test that selection_method field exists with choices."""
        # Default should be AVERAGE
        self.assertEqual(self.action.selection_method, 'AVERAGE')
        
        # Test LARGEST
        self.action.selection_method = 'LARGEST'
        self.action.save()
        self.action.refresh_from_db()
        self.assertEqual(self.action.selection_method, 'LARGEST')
        
        # Test SMALLEST
        self.action.selection_method = 'SMALLEST'
        self.action.save()
        self.action.refresh_from_db()
        self.assertEqual(self.action.selection_method, 'SMALLEST')
    
    def test_complete_measurement_record(self):
        """Test creating a complete measurement record."""
        self.action.measured_avg_weight_g = Decimal('55.75')
        self.action.measured_std_dev_weight_g = Decimal('3.20')
        self.action.measured_sample_size = 50
        self.action.measured_avg_length_cm = Decimal('13.2')
        self.action.measured_notes = "Healthy sample, good distribution"
        self.action.selection_method = 'AVERAGE'
        self.action.save()
        
        self.action.refresh_from_db()
        self.assertEqual(self.action.measured_avg_weight_g, Decimal('55.75'))
        self.assertEqual(self.action.measured_std_dev_weight_g, Decimal('3.20'))
        self.assertEqual(self.action.measured_sample_size, 50)
        self.assertEqual(self.action.measured_avg_length_cm, Decimal('13.2'))
        self.assertIn("Healthy sample", self.action.measured_notes)
        self.assertEqual(self.action.selection_method, 'AVERAGE')
    
    def test_fields_are_nullable(self):
        """Test that all measured fields are nullable (backward compatible)."""
        # Action should save without any measured fields
        action = TransferAction.objects.create(
            workflow=self.workflow,
            action_number=2,
            source_assignment=self.source_assignment,
            source_population_before=500,
            transferred_count=250,
            transferred_biomass_kg=Decimal('12.50'),
            status='PENDING'
        )
        action.refresh_from_db()
        self.assertIsNone(action.measured_avg_weight_g)
        self.assertIsNone(action.measured_std_dev_weight_g)
        self.assertIsNone(action.measured_sample_size)
        self.assertIsNone(action.measured_avg_length_cm)
        self.assertEqual(action.measured_notes, '')


class BatchPinnedScenarioTestCase(TestCase):
    """Test Batch pinned_scenario field for growth assimilation."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.species = Species.objects.create(
            name='Test Species',
            scientific_name='Testus speciesus'
        )
        self.stage = LifeCycleStage.objects.create(
            species=self.species,
            name='Fry',
            stage_number=1
        )
        
        self.batch = Batch.objects.create(
            batch_number='TEST-001',
            species=self.species,
            lifecycle_stage=self.stage,
            start_date=timezone.now().date(),
            status='ACTIVE'
        )
        
        self.scenario = Scenario.objects.create(
            name='Test Scenario',
            description='Test scenario for growth assimilation',
            created_by=self.user
        )
    
    def test_pinned_scenario_field_exists(self):
        """Test that pinned_scenario field exists and can be set."""
        self.batch.pinned_scenario = self.scenario
        self.batch.save()
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.pinned_scenario, self.scenario)
    
    def test_pinned_scenario_is_nullable(self):
        """Test that pinned_scenario is nullable (backward compatible)."""
        self.assertIsNone(self.batch.pinned_scenario)
    
    def test_pinned_scenario_set_null_on_delete(self):
        """Test that pinned_scenario is set to NULL when scenario is deleted."""
        self.batch.pinned_scenario = self.scenario
        self.batch.save()
        
        scenario_id = self.scenario.id
        self.scenario.delete()
        
        self.batch.refresh_from_db()
        self.assertIsNone(self.batch.pinned_scenario)
    
    def test_multiple_batches_can_pin_same_scenario(self):
        """Test that multiple batches can pin the same scenario."""
        batch2 = Batch.objects.create(
            batch_number='TEST-002',
            species=self.species,
            lifecycle_stage=self.stage,
            start_date=timezone.now().date(),
            status='ACTIVE'
        )
        
        self.batch.pinned_scenario = self.scenario
        batch2.pinned_scenario = self.scenario
        self.batch.save()
        batch2.save()
        
        self.batch.refresh_from_db()
        batch2.refresh_from_db()
        
        self.assertEqual(self.batch.pinned_scenario, self.scenario)
        self.assertEqual(batch2.pinned_scenario, self.scenario)
        
        # Check reverse relation
        self.assertEqual(self.scenario.pinned_batches.count(), 2)


class MigrationBackwardCompatibilityTestCase(TestCase):
    """Test that migrations are backward compatible."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.geography = Geography.objects.create(
            name='Test Geography',
            code='TG'
        )
        self.area = Area.objects.create(
            name='Test Area',
            code='TA',
            geography=self.geography
        )
        self.container = Container.objects.create(
            name='Test Tank',
            area=self.area,
            capacity=1000
        )
        
        self.species = Species.objects.create(
            name='Test Species',
            scientific_name='Testus speciesus'
        )
        self.stage = LifeCycleStage.objects.create(
            species=self.species,
            name='Fry',
            stage_number=1
        )
    
    def test_create_batch_without_pinned_scenario(self):
        """Test that batches can be created without pinned_scenario (backward compatible)."""
        batch = Batch.objects.create(
            batch_number='TEST-001',
            species=self.species,
            lifecycle_stage=self.stage,
            start_date=timezone.now().date(),
            status='ACTIVE'
        )
        self.assertIsNone(batch.pinned_scenario)
    
    def test_create_transfer_action_without_measurements(self):
        """Test that transfer actions can be created without measurements (backward compatible)."""
        batch = Batch.objects.create(
            batch_number='TEST-001',
            species=self.species,
            lifecycle_stage=self.stage,
            start_date=timezone.now().date(),
            status='ACTIVE'
        )
        
        assignment = BatchContainerAssignment.objects.create(
            batch=batch,
            container=self.container,
            lifecycle_stage=self.stage,
            population_count=1000,
            avg_weight_g=Decimal('50.00'),
            biomass_kg=Decimal('50.00'),
            assignment_date=timezone.now().date()
        )
        
        workflow = BatchTransferWorkflow.objects.create(
            batch=batch,
            workflow_type='LIFECYCLE_TRANSITION',
            source_lifecycle_stage=self.stage,
            dest_lifecycle_stage=self.stage,
            status='IN_PROGRESS'
        )
        
        action = TransferAction.objects.create(
            workflow=workflow,
            action_number=1,
            source_assignment=assignment,
            source_population_before=1000,
            transferred_count=500,
            transferred_biomass_kg=Decimal('25.00'),
            status='PENDING'
        )
        
        # All measurement fields should be null/empty by default
        self.assertIsNone(action.measured_avg_weight_g)
        self.assertIsNone(action.measured_std_dev_weight_g)
        self.assertIsNone(action.measured_sample_size)
        self.assertIsNone(action.measured_avg_length_cm)
        self.assertEqual(action.measured_notes, '')
        self.assertEqual(action.selection_method, 'AVERAGE')

