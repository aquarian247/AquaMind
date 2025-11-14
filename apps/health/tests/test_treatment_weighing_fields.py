"""
Tests for health Treatment weighing fields - Issue #112 Phase 1.

Tests migrations and field behavior for:
- Treatment includes_weighing field
- Treatment sampling_event link
- Treatment journal_entry link
"""
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.health.models import Treatment, HealthSamplingEvent, JournalEntry
from apps.batch.models import Batch, Species, LifeCycleStage, BatchContainerAssignment
from apps.infrastructure.models import Area, Container, Geography

User = get_user_model()


class TreatmentWeighingFieldsTestCase(TestCase):
    """Test Treatment weighing fields for growth assimilation anchors."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create geography, area, container
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
        
        # Create species and lifecycle stage
        self.species = Species.objects.create(
            name='Test Species',
            scientific_name='Testus speciesus'
        )
        self.stage = LifeCycleStage.objects.create(
            species=self.species,
            name='Fry',
            stage_number=1
        )
        
        # Create batch and assignment
        self.batch = Batch.objects.create(
            batch_number='TEST-001',
            species=self.species,
            lifecycle_stage=self.stage,
            start_date=timezone.now().date(),
            status='ACTIVE'
        )
        
        self.assignment = BatchContainerAssignment.objects.create(
            batch=self.batch,
            container=self.container,
            lifecycle_stage=self.stage,
            population_count=1000,
            avg_weight_g=50.00,
            biomass_kg=50.00,
            assignment_date=timezone.now().date()
        )
        
        # Create treatment
        self.treatment = Treatment.objects.create(
            batch=self.batch,
            container=self.container,
            batch_assignment=self.assignment,
            user=self.user,
            treatment_date=timezone.now(),
            treatment_type='vaccination',
            description='Test vaccination'
        )
    
    def test_includes_weighing_field_exists(self):
        """Test that includes_weighing field exists and defaults to False."""
        self.assertEqual(self.treatment.includes_weighing, False)
    
    def test_includes_weighing_can_be_set(self):
        """Test that includes_weighing can be set to True."""
        self.treatment.includes_weighing = True
        self.treatment.save()
        self.treatment.refresh_from_db()
        self.assertTrue(self.treatment.includes_weighing)
    
    def test_sampling_event_field_exists(self):
        """Test that sampling_event field exists and is nullable."""
        self.assertIsNone(self.treatment.sampling_event)
    
    def test_sampling_event_can_be_linked(self):
        """Test that sampling_event can be linked to a HealthSamplingEvent."""
        sampling_event = HealthSamplingEvent.objects.create(
            batch=self.batch,
            container=self.container,
            batch_assignment=self.assignment,
            sampling_date=timezone.now().date(),
            purpose='growth_monitoring',
            sampled_by=self.user
        )
        
        self.treatment.sampling_event = sampling_event
        self.treatment.save()
        self.treatment.refresh_from_db()
        
        self.assertEqual(self.treatment.sampling_event, sampling_event)
    
    def test_journal_entry_field_exists(self):
        """Test that journal_entry field exists and is nullable."""
        self.assertIsNone(self.treatment.journal_entry)
    
    def test_journal_entry_can_be_linked(self):
        """Test that journal_entry can be linked to a JournalEntry."""
        journal_entry = JournalEntry.objects.create(
            batch=self.batch,
            user=self.user,
            entry_date=timezone.now(),
            title='Vaccination Record',
            content='Administered IPN vaccine'
        )
        
        self.treatment.journal_entry = journal_entry
        self.treatment.save()
        self.treatment.refresh_from_db()
        
        self.assertEqual(self.treatment.journal_entry, journal_entry)
    
    def test_complete_weighing_record(self):
        """Test creating a complete weighing record with all fields."""
        sampling_event = HealthSamplingEvent.objects.create(
            batch=self.batch,
            container=self.container,
            batch_assignment=self.assignment,
            sampling_date=timezone.now().date(),
            purpose='growth_monitoring',
            sampled_by=self.user
        )
        
        journal_entry = JournalEntry.objects.create(
            batch=self.batch,
            user=self.user,
            entry_date=timezone.now(),
            title='Vaccination with Weighing',
            content='Vaccinated and weighed 50 fish'
        )
        
        self.treatment.includes_weighing = True
        self.treatment.sampling_event = sampling_event
        self.treatment.journal_entry = journal_entry
        self.treatment.save()
        
        self.treatment.refresh_from_db()
        self.assertTrue(self.treatment.includes_weighing)
        self.assertEqual(self.treatment.sampling_event, sampling_event)
        self.assertEqual(self.treatment.journal_entry, journal_entry)
    
    def test_sampling_event_set_null_on_delete(self):
        """Test that sampling_event is set to NULL when deleted."""
        sampling_event = HealthSamplingEvent.objects.create(
            batch=self.batch,
            container=self.container,
            batch_assignment=self.assignment,
            sampling_date=timezone.now().date(),
            purpose='growth_monitoring',
            sampled_by=self.user
        )
        
        self.treatment.sampling_event = sampling_event
        self.treatment.save()
        
        sampling_event.delete()
        self.treatment.refresh_from_db()
        
        self.assertIsNone(self.treatment.sampling_event)
    
    def test_journal_entry_set_null_on_delete(self):
        """Test that journal_entry is set to NULL when deleted."""
        journal_entry = JournalEntry.objects.create(
            batch=self.batch,
            user=self.user,
            entry_date=timezone.now(),
            title='Test Entry',
            content='Test content'
        )
        
        self.treatment.journal_entry = journal_entry
        self.treatment.save()
        
        journal_entry.delete()
        self.treatment.refresh_from_db()
        
        self.assertIsNone(self.treatment.journal_entry)


class TreatmentBackwardCompatibilityTestCase(TestCase):
    """Test that Treatment model changes are backward compatible."""
    
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
        
        self.batch = Batch.objects.create(
            batch_number='TEST-001',
            species=self.species,
            lifecycle_stage=self.stage,
            start_date=timezone.now().date(),
            status='ACTIVE'
        )
    
    def test_create_treatment_without_weighing_fields(self):
        """Test that treatments can be created without weighing fields (backward compatible)."""
        treatment = Treatment.objects.create(
            batch=self.batch,
            container=self.container,
            user=self.user,
            treatment_date=timezone.now(),
            treatment_type='medication',
            description='Parasite treatment'
        )
        
        # Fields should have safe defaults
        self.assertFalse(treatment.includes_weighing)
        self.assertIsNone(treatment.sampling_event)
        self.assertIsNone(treatment.journal_entry)

