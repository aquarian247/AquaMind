"""
Unit tests for planning app models.

Tests critical model methods that could break functionality:
- is_overdue property calculation
- mark_completed workflow
- spawn_transfer_workflow integration

Compatible with both SQLite (GitHub CI) and PostgreSQL (production).
"""
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from apps.planning.models import PlannedActivity, ActivityTemplate
from apps.scenario.models import Scenario, TemperatureProfile, TGCModel, FCRModel, FCRModelStage, MortalityModel
from apps.batch.models import Batch, Species, LifeCycleStage


class PlannedActivityModelTest(TestCase):
    """Test PlannedActivity model critical methods."""
    
    def setUp(self):
        """Set up minimal test data."""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        
        # Create minimal species/stage
        self.species, _ = Species.objects.get_or_create(
            name='Atlantic Salmon',
            defaults={'scientific_name': 'Salmo salar'}
        )
        self.fry_stage, _ = LifeCycleStage.objects.get_or_create(
            name='Fry',
            species=self.species,
            defaults={'order': 1}
        )
        self.parr_stage, _ = LifeCycleStage.objects.get_or_create(
            name='Parr',
            species=self.species,
            defaults={'order': 2}
        )
        
        # Create minimal batch
        self.batch, _ = Batch.objects.get_or_create(
            batch_number='TEST-001',
            defaults={
                'species': self.species,
                'lifecycle_stage': self.fry_stage,
                'start_date': timezone.now().date(),
                'status': 'ACTIVE',
                'batch_type': 'PRODUCTION'
            }
        )
        
        # Create minimal models for scenario
        temp_profile = TemperatureProfile.objects.create(name='Test Profile')
        tgc_model = TGCModel.objects.create(
            name='Test TGC',
            location='Test',
            release_period='Spring',
            tgc_value=Decimal('0.025'),
            profile=temp_profile
        )
        fcr_model = FCRModel.objects.create(name='Test FCR')
        FCRModelStage.objects.create(
            model=fcr_model,
            stage=self.fry_stage,
            fcr_value=Decimal('1.2'),
            duration_days=90
        )
        mortality_model = MortalityModel.objects.create(
            name='Test Mortality',
            frequency='daily',
            rate=Decimal('0.05')
        )
        
        # Create scenario
        self.scenario = Scenario.objects.create(
            name='Test Scenario',
            start_date=timezone.now().date(),
            duration_days=365,
            initial_count=10000,
            initial_weight=Decimal('5.0'),
            genotype='Standard',
            supplier='Test Supplier',
            tgc_model=tgc_model,
            fcr_model=fcr_model,
            mortality_model=mortality_model,
            created_by=self.user
        )
    
    def test_is_overdue_property_returns_true_when_past_due(self):
        """CRITICAL: is_overdue must correctly identify overdue activities."""
        activity = PlannedActivity.objects.create(
            scenario=self.scenario,
            batch=self.batch,
            activity_type='VACCINATION',
            due_date=timezone.now().date() - timedelta(days=1),
            status='PENDING',
            created_by=self.user
        )
        
        self.assertTrue(activity.is_overdue)
    
    def test_is_overdue_property_returns_false_when_completed(self):
        """CRITICAL: is_overdue must return False for completed activities."""
        activity = PlannedActivity.objects.create(
            scenario=self.scenario,
            batch=self.batch,
            activity_type='VACCINATION',
            due_date=timezone.now().date() - timedelta(days=1),
            status='COMPLETED',
            created_by=self.user
        )
        
        self.assertFalse(activity.is_overdue)
    
    def test_mark_completed_updates_all_fields(self):
        """CRITICAL: mark_completed must update status, timestamp, and user."""
        activity = PlannedActivity.objects.create(
            scenario=self.scenario,
            batch=self.batch,
            activity_type='VACCINATION',
            due_date=timezone.now().date(),
            status='PENDING',
            created_by=self.user
        )
        
        activity.mark_completed(user=self.user)
        
        self.assertEqual(activity.status, 'COMPLETED')
        self.assertIsNotNone(activity.completed_at)
        self.assertEqual(activity.completed_by, self.user)
    
    def test_spawn_transfer_workflow_creates_workflow_and_links(self):
        """CRITICAL: spawn_transfer_workflow must create workflow and update status."""
        activity = PlannedActivity.objects.create(
            scenario=self.scenario,
            batch=self.batch,
            activity_type='TRANSFER',
            due_date=timezone.now().date(),
            status='PENDING',
            created_by=self.user
        )
        
        workflow = activity.spawn_transfer_workflow(
            workflow_type='LIFECYCLE_TRANSITION',
            source_lifecycle_stage=self.fry_stage,
            dest_lifecycle_stage=self.parr_stage
        )
        
        # Verify workflow created and linked
        self.assertIsNotNone(workflow)
        self.assertEqual(activity.transfer_workflow, workflow)
        self.assertEqual(activity.status, 'IN_PROGRESS')
        self.assertEqual(workflow.planned_activity, activity)
    
    def test_spawn_transfer_workflow_raises_error_for_non_transfer(self):
        """CRITICAL: spawn_transfer_workflow must reject non-TRANSFER activities."""
        activity = PlannedActivity.objects.create(
            scenario=self.scenario,
            batch=self.batch,
            activity_type='VACCINATION',  # Not TRANSFER
            due_date=timezone.now().date(),
            created_by=self.user
        )
        
        with self.assertRaises(ValueError) as context:
            activity.spawn_transfer_workflow(
                workflow_type='LIFECYCLE_TRANSITION',
                source_lifecycle_stage=self.fry_stage,
                dest_lifecycle_stage=self.parr_stage
            )
        
        self.assertIn('Can only spawn workflows from TRANSFER activities', str(context.exception))
    
    def test_spawn_transfer_workflow_raises_error_for_completed_activity(self):
        """CRITICAL: Cannot spawn workflow from completed or cancelled activities."""
        activity = PlannedActivity.objects.create(
            scenario=self.scenario,
            batch=self.batch,
            activity_type='TRANSFER',
            due_date=timezone.now().date(),
            status='COMPLETED',  # Already completed
            created_by=self.user,
            completed_by=self.user,
            completed_at=timezone.now()
        )
        
        with self.assertRaises(ValueError) as context:
            activity.spawn_transfer_workflow(
                workflow_type='LIFECYCLE_TRANSITION',
                source_lifecycle_stage=self.fry_stage,
                dest_lifecycle_stage=self.parr_stage
            )
        
        self.assertIn('Cannot spawn workflow for activity with status', str(context.exception))
    
    def test_spawn_transfer_workflow_raises_error_for_cancelled_activity(self):
        """CRITICAL: Cannot spawn workflow from cancelled activities."""
        activity = PlannedActivity.objects.create(
            scenario=self.scenario,
            batch=self.batch,
            activity_type='TRANSFER',
            due_date=timezone.now().date(),
            status='CANCELLED',  # Cancelled
            created_by=self.user
        )
        
        with self.assertRaises(ValueError) as context:
            activity.spawn_transfer_workflow(
                workflow_type='LIFECYCLE_TRANSITION',
                source_lifecycle_stage=self.fry_stage,
                dest_lifecycle_stage=self.parr_stage
            )
        
        self.assertIn('Cannot spawn workflow for activity with status', str(context.exception))


class ActivityTemplateModelTest(TestCase):
    """Test ActivityTemplate generation logic."""
    
    def setUp(self):
        """Set up minimal test data."""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        
        # Minimal species/stage/batch
        self.species, _ = Species.objects.get_or_create(
            name='Atlantic Salmon',
            defaults={'scientific_name': 'Salmo salar'}
        )
        self.fry_stage, _ = LifeCycleStage.objects.get_or_create(
            name='Fry',
            species=self.species,
            defaults={'order': 1}
        )
        self.batch, _ = Batch.objects.get_or_create(
            batch_number='TEST-002',
            defaults={
                'species': self.species,
                'lifecycle_stage': self.fry_stage,
                'start_date': timezone.now().date(),
                'status': 'ACTIVE',
                'batch_type': 'PRODUCTION'
            }
        )
        
        # Minimal scenario models
        temp_profile = TemperatureProfile.objects.create(name='Test Profile')
        tgc_model = TGCModel.objects.create(
            name='Test TGC',
            location='Test',
            release_period='Spring',
            tgc_value=Decimal('0.025'),
            profile=temp_profile
        )
        fcr_model = FCRModel.objects.create(name='Test FCR')
        FCRModelStage.objects.create(
            model=fcr_model,
            stage=self.fry_stage,
            fcr_value=Decimal('1.2'),
            duration_days=90
        )
        mortality_model = MortalityModel.objects.create(
            name='Test Mortality',
            frequency='daily',
            rate=Decimal('0.05')
        )
        
        self.scenario = Scenario.objects.create(
            name='Test Scenario',
            start_date=timezone.now().date(),
            duration_days=365,
            initial_count=10000,
            initial_weight=Decimal('5.0'),
            genotype='Standard',
            supplier='Test Supplier',
            tgc_model=tgc_model,
            fcr_model=fcr_model,
            mortality_model=mortality_model,
            created_by=self.user
        )
    
    def test_generate_activity_calculates_due_date_from_day_offset(self):
        """CRITICAL: Template generation must calculate correct due date."""
        template = ActivityTemplate.objects.create(
            name='First Vaccination',
            activity_type='VACCINATION',
            trigger_type='DAY_OFFSET',
            day_offset=30,
            notes_template='Test vaccination',
            is_active=True
        )
        
        activity = template.generate_activity(
            scenario=self.scenario,
            batch=self.batch
        )
        
        # Verify due date is 30 days after batch creation
        expected_due_date = self.batch.created_at.date() + timedelta(days=30)
        self.assertEqual(activity.due_date, expected_due_date)
        self.assertEqual(activity.activity_type, 'VACCINATION')
        self.assertEqual(activity.notes, 'Test vaccination')
    
    def test_generate_activity_raises_error_for_missing_day_offset(self):
        """CRITICAL: Template must validate day_offset when trigger_type is DAY_OFFSET."""
        template = ActivityTemplate.objects.create(
            name='Invalid Template',
            activity_type='VACCINATION',
            trigger_type='DAY_OFFSET',
            day_offset=None,  # Missing required field
            is_active=True
        )
        
        with self.assertRaises(ValueError) as context:
            template.generate_activity(
                scenario=self.scenario,
                batch=self.batch
            )
        
        self.assertIn('day_offset is required', str(context.exception))
