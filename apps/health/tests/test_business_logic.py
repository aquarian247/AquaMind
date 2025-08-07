"""
Tests for Health app business logic.

This module contains tests for the business logic in the Health app,
focusing on disease tracking, mortality calculation, treatment effectiveness,
health status transitions, and health observation aggregations.
"""

import unittest
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError
from django.core.exceptions import ValidationError
from django.db.models import Avg, StdDev, Min, Max, Count

from apps.batch.models import Batch, Species, LifeCycleStage
from apps.infrastructure.models import ContainerType, Geography, FreshwaterStation, Hall, Container
from apps.health.models import (
    MortalityReason, MortalityRecord, LiceCount,
    HealthParameter, HealthSamplingEvent, IndividualFishObservation, FishParameterScore,
    Treatment, VaccinationType, JournalEntry, SampleType, HealthLabSample
)

User = get_user_model()


class MortalityRecordTest(TestCase):
    """Test the MortalityRecord model and related business logic."""
    
    def setUp(self):
        """Set up test data for mortality records."""
        # Create minimal required objects
        self.species, _ = Species.objects.get_or_create(
            name="Atlantic Salmon",
            scientific_name="Salmo salar"
        )
        self.lifecycle_stage, _ = LifeCycleStage.objects.get_or_create(
            name="Smolt",
            description="Young salmon ready for transfer to seawater",
            defaults={
                "order": 1,
                "species": self.species,  # species_id is required (NOT NULL)
            }
        )
        self.batch, _ = Batch.objects.get_or_create(
            batch_number="TEST-BATCH-001",
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            start_date=timezone.now().date(),
            expected_end_date=timezone.now().date() + timezone.timedelta(days=90),
            status="ACTIVE",
            batch_type="PRODUCTION"
        )
        
        # Create container hierarchy
        self.geography, _ = Geography.objects.get_or_create(name="Test Geography")
        self.station, _ = FreshwaterStation.objects.get_or_create(
            name="Test Station",
            station_type="FRESHWATER",
            geography=self.geography
        )
        self.hall, _ = Hall.objects.get_or_create(
            name="Test Hall",
            station=self.station
        )
        self.container_type, _ = ContainerType.objects.get_or_create(
            name="Test Tank",
            max_volume_m3=100.0
        )
        self.container, _ = Container.objects.get_or_create(
            name="Test Container",
            container_type=self.container_type,
            hall=self.hall
        )
        
        # Create mortality reason
        self.mortality_reason, _ = MortalityReason.objects.get_or_create(
            name="Disease",
            description="Mortality due to disease"
        )
        
        # Create a mortality record
        self.mortality_record = MortalityRecord.objects.create(
            batch=self.batch,
            container=self.container,
            event_date=timezone.now(),
            count=50,
            reason=self.mortality_reason,
            notes="Test mortality record"
        )
    
    def test_mortality_record_creation(self):
        """Test that a mortality record can be created with required fields."""
        self.assertEqual(self.mortality_record.batch, self.batch)
        self.assertEqual(self.mortality_record.container, self.container)
        self.assertEqual(self.mortality_record.count, 50)
        self.assertEqual(self.mortality_record.reason, self.mortality_reason)
        self.assertEqual(self.mortality_record.notes, "Test mortality record")
    
    def test_mortality_record_str(self):
        """Test the string representation of a mortality record."""
        expected_str = f"Mortality of 50 on {self.mortality_record.event_date.strftime('%Y-%m-%d')}"
        self.assertEqual(str(self.mortality_record), expected_str)
    
    def test_mortality_record_without_container(self):
        """Test that a mortality record can be created without a container."""
        mortality_record = MortalityRecord.objects.create(
            batch=self.batch,
            event_date=timezone.now(),
            count=25,
            reason=self.mortality_reason
        )
        self.assertIsNone(mortality_record.container)
        self.assertEqual(mortality_record.count, 25)
    
    def test_mortality_reason_uniqueness(self):
        """Test that mortality reasons must have unique names."""
        # First creation should succeed
        MortalityReason.objects.create(name="Unique Reason")
        
        # Second creation with same name should fail
        with self.assertRaises(IntegrityError):
            MortalityReason.objects.create(name="Unique Reason")


class LiceCountTest(TestCase):
    """Test the LiceCount model and its business logic."""
    
    def setUp(self):
        """Set up test data for lice counts."""
        # Create minimal required objects
        self.species, _ = Species.objects.get_or_create(
            name="Atlantic Salmon",
            scientific_name="Salmo salar"
        )
        self.lifecycle_stage, _ = LifeCycleStage.objects.get_or_create(
            name="Smolt",
            description="Young salmon ready for transfer to seawater",
            defaults={
                "order": 1,
                "species": self.species,
            }
        )
        self.batch, _ = Batch.objects.get_or_create(
            batch_number="TEST-BATCH-002",
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            start_date=timezone.now().date(),
            expected_end_date=timezone.now().date() + timezone.timedelta(days=90),
            status="ACTIVE",
            batch_type="PRODUCTION"
        )
        
        # Create container hierarchy
        self.geography, _ = Geography.objects.get_or_create(name="Test Geography")
        self.station, _ = FreshwaterStation.objects.get_or_create(
            name="Test Station",
            station_type="FRESHWATER",
            geography=self.geography
        )
        self.hall, _ = Hall.objects.get_or_create(
            name="Test Hall",
            station=self.station
        )
        self.container_type, _ = ContainerType.objects.get_or_create(
            name="Test Tank",
            max_volume_m3=100.0
        )
        self.container, _ = Container.objects.get_or_create(
            name="Test Container",
            container_type=self.container_type,
            hall=self.hall
        )
        
        # Create user
        self.user, _ = User.objects.get_or_create(
            username="testuser",
            defaults={"email": "test@example.com"}
        )
        
        # Create a lice count record
        self.lice_count = LiceCount.objects.create(
            batch=self.batch,
            container=self.container,
            user=self.user,
            count_date=timezone.now(),
            adult_female_count=10,
            adult_male_count=15,
            juvenile_count=25,
            fish_sampled=20,
            notes="Test lice count"
        )
    
    def test_lice_count_creation(self):
        """Test that a lice count can be created with required fields."""
        self.assertEqual(self.lice_count.batch, self.batch)
        self.assertEqual(self.lice_count.container, self.container)
        self.assertEqual(self.lice_count.user, self.user)
        self.assertEqual(self.lice_count.adult_female_count, 10)
        self.assertEqual(self.lice_count.adult_male_count, 15)
        self.assertEqual(self.lice_count.juvenile_count, 25)
        self.assertEqual(self.lice_count.fish_sampled, 20)
    
    def test_lice_count_str(self):
        """Test the string representation of a lice count."""
        total_count = self.lice_count.adult_female_count + self.lice_count.adult_male_count + self.lice_count.juvenile_count
        expected_str = f"Lice Count: {total_count} on {self.lice_count.count_date.strftime('%Y-%m-%d')}"
        self.assertEqual(str(self.lice_count), expected_str)
    
    def test_average_per_fish_calculation(self):
        """Test the average_per_fish property calculation."""
        # Total lice: 10 + 15 + 25 = 50, Fish sampled: 20
        # Expected average: 50 / 20 = 2.5
        self.assertEqual(self.lice_count.average_per_fish, 2.5)
    
    def test_average_per_fish_with_zero_fish(self):
        """Test the average_per_fish property with zero fish sampled."""
        lice_count = LiceCount.objects.create(
            batch=self.batch,
            user=self.user,
            count_date=timezone.now(),
            adult_female_count=5,
            adult_male_count=5,
            juvenile_count=5,
            fish_sampled=0
        )
        # Should return 0 to avoid division by zero
        self.assertEqual(lice_count.average_per_fish, 0)
    
    def test_lice_count_without_container(self):
        """Test that a lice count can be created without a container."""
        lice_count = LiceCount.objects.create(
            batch=self.batch,
            user=self.user,
            count_date=timezone.now(),
            adult_female_count=5,
            adult_male_count=5,
            juvenile_count=5,
            fish_sampled=10
        )
        self.assertIsNone(lice_count.container)
        self.assertEqual(lice_count.average_per_fish, 1.5)


class HealthSamplingEventTest(TestCase):
    """Test the HealthSamplingEvent model and its business logic."""
    
    def setUp(self):
        """Set up test data for health sampling events."""
        # Create minimal required objects
        self.species, _ = Species.objects.get_or_create(
            name="Atlantic Salmon",
            scientific_name="Salmo salar"
        )
        self.lifecycle_stage, _ = LifeCycleStage.objects.get_or_create(
            name="Smolt",
            description="Young salmon ready for transfer to seawater",
            defaults={
                "order": 1,
                "species": self.species,
            }
        )
        self.batch, _ = Batch.objects.get_or_create(
            batch_number="TEST-BATCH-003",
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            start_date=timezone.now().date(),
            expected_end_date=timezone.now().date() + timezone.timedelta(days=90),
            status="ACTIVE",
            batch_type="PRODUCTION"
        )
        
        # Create container hierarchy
        self.geography, _ = Geography.objects.get_or_create(name="Test Geography")
        self.station, _ = FreshwaterStation.objects.get_or_create(
            name="Test Station",
            station_type="FRESHWATER",
            geography=self.geography
        )
        self.hall, _ = Hall.objects.get_or_create(
            name="Test Hall",
            station=self.station
        )
        self.container_type, _ = ContainerType.objects.get_or_create(
            name="Test Tank",
            max_volume_m3=100.0
        )
        self.container, _ = Container.objects.get_or_create(
            name="Test Container",
            container_type=self.container_type,
            hall=self.hall
        )
        
        # Create user
        self.user, _ = User.objects.get_or_create(
            username="testuser",
            defaults={"email": "test@example.com"}
        )
        
        # Create a health sampling event
        from apps.batch.models import BatchContainerAssignment
        self.assignment, _ = BatchContainerAssignment.objects.get_or_create(
            batch=self.batch,
            container=self.container,
            defaults={
                "start_date": timezone.now().date(),
                "population_count": 1000,
                "lifecycle_stage": self.lifecycle_stage
            }
        )
        
        self.health_sampling_event = HealthSamplingEvent.objects.create(
            assignment=self.assignment,
            sampling_date=timezone.now().date(),
            target_sample_size=30,
            sampled_by=self.user
        )
    
    def test_health_sampling_event_creation(self):
        """Test that a health sampling event can be created with required fields."""
        self.assertEqual(self.health_sampling_event.assignment, self.assignment)
        self.assertEqual(self.health_sampling_event.target_sample_size, 30)
        self.assertEqual(self.health_sampling_event.sampled_by, self.user)
        self.assertIsNone(self.health_sampling_event.avg_weight_g)  # Should be None initially
    
    def test_health_sampling_event_str(self):
        """Test the string representation of a health sampling event."""
        expected_str = f"Health Sample - {self.assignment} - {self.health_sampling_event.sampling_date}"
        self.assertEqual(str(self.health_sampling_event), expected_str)
    
    def test_calculate_aggregate_metrics_no_observations(self):
        """Test calculate_aggregate_metrics with no observations."""
        # Should set calculated_sample_size to 0 and not change other fields
        self.health_sampling_event.calculate_aggregate_metrics()
        self.assertEqual(self.health_sampling_event.calculated_sample_size, 0)
        self.assertIsNone(self.health_sampling_event.avg_weight_g)
        self.assertIsNone(self.health_sampling_event.avg_length_cm)
    
    def test_calculate_aggregate_metrics_with_observations(self):
        """Test calculate_aggregate_metrics with multiple observations."""
        # Create individual fish observations
        IndividualFishObservation.objects.create(
            sampling_event=self.health_sampling_event,
            fish_number=1,
            weight_g=Decimal('100'),
            length_cm=Decimal('20'),
        )
        IndividualFishObservation.objects.create(
            sampling_event=self.health_sampling_event,
            fish_number=2,
            weight_g=Decimal('110'),
            length_cm=Decimal('21'),
        )
        IndividualFishObservation.objects.create(
            sampling_event=self.health_sampling_event,
            fish_number=3,
            weight_g=Decimal('120'),
            length_cm=Decimal('22'),
        )
        
        # Calculate metrics
        self.health_sampling_event.calculate_aggregate_metrics()
        
        # Check results
        self.assertEqual(self.health_sampling_event.calculated_sample_size, 3)
        self.assertEqual(self.health_sampling_event.avg_weight_g, Decimal('110'))
        self.assertEqual(self.health_sampling_event.min_weight_g, Decimal('100'))
        self.assertEqual(self.health_sampling_event.max_weight_g, Decimal('120'))
        self.assertEqual(self.health_sampling_event.avg_length_cm, Decimal('21'))
        self.assertEqual(self.health_sampling_event.min_length_cm, Decimal('20'))
        self.assertEqual(self.health_sampling_event.max_length_cm, Decimal('22'))
    
    def test_calculate_aggregate_metrics_with_missing_data(self):
        """Test calculate_aggregate_metrics with some missing data."""
        # Create individual fish observations with some missing data
        IndividualFishObservation.objects.create(
            sampling_event=self.health_sampling_event,
            fish_number=1,
            weight_g=Decimal('100'),
            # Missing length
        )
        IndividualFishObservation.objects.create(
            sampling_event=self.health_sampling_event,
            fish_number=2,
            # Missing weight
            length_cm=Decimal('21'),
        )
        IndividualFishObservation.objects.create(
            sampling_event=self.health_sampling_event,
            fish_number=3,
            weight_g=Decimal('120'),
            length_cm=Decimal('22'),
        )
        
        # Calculate metrics
        self.health_sampling_event.calculate_aggregate_metrics()
        
        # Check results - should only include non-null values in calculations
        self.assertEqual(self.health_sampling_event.calculated_sample_size, 3)  # Total number of observations
        self.assertEqual(self.health_sampling_event.avg_weight_g, Decimal('110'))  # Average of 100 and 120
        self.assertEqual(self.health_sampling_event.avg_length_cm, Decimal('21.5'))  # Average of 21 and 22


class TreatmentTest(TestCase):
    """Test the Treatment model and related business logic."""
    
    def setUp(self):
        """Set up test data for treatments."""
        # Create minimal required objects
        self.species, _ = Species.objects.get_or_create(
            name="Atlantic Salmon",
            scientific_name="Salmo salar"
        )
        self.lifecycle_stage, _ = LifeCycleStage.objects.get_or_create(
            name="Smolt",
            description="Young salmon ready for transfer to seawater",
            defaults={
                "order": 1,
                "species": self.species,
            }
        )
        self.batch, _ = Batch.objects.get_or_create(
            batch_number="TEST-BATCH-004",
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            start_date=timezone.now().date(),
            expected_end_date=timezone.now().date() + timezone.timedelta(days=90),
            status="ACTIVE",
            batch_type="PRODUCTION"
        )
        
        # Create container hierarchy
        self.geography, _ = Geography.objects.get_or_create(name="Test Geography")
        self.station, _ = FreshwaterStation.objects.get_or_create(
            name="Test Station",
            station_type="FRESHWATER",
            geography=self.geography
        )
        self.hall, _ = Hall.objects.get_or_create(
            name="Test Hall",
            station=self.station
        )
        self.container_type, _ = ContainerType.objects.get_or_create(
            name="Test Tank",
            max_volume_m3=100.0
        )
        self.container, _ = Container.objects.get_or_create(
            name="Test Container",
            container_type=self.container_type,
            hall=self.hall
        )
        
        # Create user
        self.user, _ = User.objects.get_or_create(
            username="testuser",
            defaults={"email": "test@example.com"}
        )
        
        # Create a treatment
        self.treatment = Treatment.objects.create(
            batch=self.batch,
            container=self.container,
            treatment_type="MEDICATION",
            name="Test Treatment",
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timezone.timedelta(days=5),
            dosage="10mg/L",
            administered_by=self.user,
            notes="Test treatment notes"
        )
    
    def test_treatment_creation(self):
        """Test that a treatment can be created with required fields."""
        self.assertEqual(self.treatment.batch, self.batch)
        self.assertEqual(self.treatment.container, self.container)
        self.assertEqual(self.treatment.treatment_type, "MEDICATION")
        self.assertEqual(self.treatment.name, "Test Treatment")
        self.assertEqual(self.treatment.administered_by, self.user)
    
    def test_treatment_str(self):
        """Test the string representation of a treatment."""
        expected_str = f"Test Treatment for {self.batch} ({self.treatment.start_date})"
        self.assertEqual(str(self.treatment), expected_str)
    
    def test_treatment_without_end_date(self):
        """Test a treatment without an end date."""
        treatment = Treatment.objects.create(
            batch=self.batch,
            treatment_type="MEDICATION",
            name="Ongoing Treatment",
            start_date=timezone.now().date(),
            administered_by=self.user
        )
        # No assertions about duration since it doesn't exist


class VaccinationTest(TestCase):
    """Test the VaccinationType model."""
    
    def setUp(self):
        """Set up test data for vaccinations."""
        self.vaccination_type = VaccinationType.objects.create(
            name="Test Vaccine",
            description="Test vaccine description",
            manufacturer="Test Manufacturer"
        )
    
    def test_vaccination_type_creation(self):
        """Test that a vaccination type can be created."""
        self.assertEqual(self.vaccination_type.name, "Test Vaccine")
        self.assertEqual(self.vaccination_type.description, "Test vaccine description")
        self.assertEqual(self.vaccination_type.manufacturer, "Test Manufacturer")
    
    def test_vaccination_type_str(self):
        """Test the string representation of a vaccination type."""
        self.assertEqual(str(self.vaccination_type), "Test Vaccine")
    
    def test_vaccination_type_uniqueness(self):
        """Test that vaccination type names must be unique."""
        # First creation should succeed
        VaccinationType.objects.create(name="Unique Vaccine")
        
        # Second creation with same name should fail
        with self.assertRaises(IntegrityError):
            VaccinationType.objects.create(name="Unique Vaccine")


class JournalEntryTest(TestCase):
    """Test the JournalEntry model and related business logic."""
    
    def setUp(self):
        """Set up test data for journal entries."""
        # Create minimal required objects
        self.species, _ = Species.objects.get_or_create(
            name="Atlantic Salmon",
            scientific_name="Salmo salar"
        )
        self.lifecycle_stage, _ = LifeCycleStage.objects.get_or_create(
            name="Smolt",
            description="Young salmon ready for transfer to seawater",
            defaults={
                "order": 1,
                "species": self.species,
            }
        )
        self.batch, _ = Batch.objects.get_or_create(
            batch_number="TEST-BATCH-005",
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            start_date=timezone.now().date(),
            expected_end_date=timezone.now().date() + timezone.timedelta(days=90),
            status="ACTIVE",
            batch_type="PRODUCTION"
        )
        
        # Create container hierarchy
        self.geography, _ = Geography.objects.get_or_create(name="Test Geography")
        self.station, _ = FreshwaterStation.objects.get_or_create(
            name="Test Station",
            station_type="FRESHWATER",
            geography=self.geography
        )
        self.hall, _ = Hall.objects.get_or_create(
            name="Test Hall",
            station=self.station
        )
        self.container_type, _ = ContainerType.objects.get_or_create(
            name="Test Tank",
            max_volume_m3=100.0
        )
        self.container, _ = Container.objects.get_or_create(
            name="Test Container",
            container_type=self.container_type,
            hall=self.hall
        )
        
        # Create user
        self.user, _ = User.objects.get_or_create(
            username="testuser",
            defaults={"email": "test@example.com"}
        )
        
        # Create health parameters
        self.health_parameter, _ = HealthParameter.objects.get_or_create(
            name="Fin Condition",
            description="Condition of the fins"
        )
        
        # Create a journal entry
        self.journal_entry = JournalEntry.objects.create(
            batch=self.batch,
            container=self.container,
            entry_date=timezone.now(),
            entry_text="Test journal entry",
            user=self.user,
            health_status="GOOD"
        )
    
    def test_journal_entry_creation(self):
        """Test that a journal entry can be created with required fields."""
        self.assertEqual(self.journal_entry.batch, self.batch)
        self.assertEqual(self.journal_entry.container, self.container)
        self.assertEqual(self.journal_entry.entry_text, "Test journal entry")
        self.assertEqual(self.journal_entry.user, self.user)
        self.assertEqual(self.journal_entry.health_status, "GOOD")
    
    def test_journal_entry_str(self):
        """Test the string representation of a journal entry."""
        expected_date = self.journal_entry.entry_date.strftime("%Y-%m-%d")
        expected_str = f"Journal Entry - {self.batch} - {expected_date}"
        self.assertEqual(str(self.journal_entry), expected_str)
    
    def test_journal_entry_without_container(self):
        """Test that a journal entry can be created without a container."""
        journal_entry = JournalEntry.objects.create(
            batch=self.batch,
            entry_date=timezone.now(),
            entry_text="Journal entry without container",
            user=self.user
        )
        self.assertIsNone(journal_entry.container)
        self.assertEqual(journal_entry.entry_text, "Journal entry without container")
    
    def test_health_parameter_creation(self):
        """Test that a health parameter can be created."""
        health_parameter = HealthParameter.objects.create(
            name="Test Parameter",
            description="Test parameter description"
        )
        self.assertEqual(health_parameter.name, "Test Parameter")
        self.assertEqual(health_parameter.description, "Test parameter description")
    
    def test_health_parameter_str(self):
        """Test the string representation of a health parameter."""
        self.assertEqual(str(self.health_parameter), "Fin Condition")


class HealthLabSampleTest(TestCase):
    """Test the HealthLabSample model and related business logic."""
    
    def setUp(self):
        """Set up test data for health lab samples."""
        # Create minimal required objects
        self.species, _ = Species.objects.get_or_create(
            name="Atlantic Salmon",
            scientific_name="Salmo salar"
        )
        self.lifecycle_stage, _ = LifeCycleStage.objects.get_or_create(
            name="Smolt",
            description="Young salmon ready for transfer to seawater",
            defaults={
                "order": 1,
                "species": self.species,
            }
        )
        self.batch, _ = Batch.objects.get_or_create(
            batch_number="TEST-BATCH-006",
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            start_date=timezone.now().date(),
            expected_end_date=timezone.now().date() + timezone.timedelta(days=90),
            status="ACTIVE",
            batch_type="PRODUCTION"
        )
        
        # Create container hierarchy
        self.geography, _ = Geography.objects.get_or_create(name="Test Geography")
        self.station, _ = FreshwaterStation.objects.get_or_create(
            name="Test Station",
            station_type="FRESHWATER",
            geography=self.geography
        )
        self.hall, _ = Hall.objects.get_or_create(
            name="Test Hall",
            station=self.station
        )
        self.container_type, _ = ContainerType.objects.get_or_create(
            name="Test Tank",
            max_volume_m3=100.0
        )
        self.container, _ = Container.objects.get_or_create(
            name="Test Container",
            container_type=self.container_type,
            hall=self.hall
        )
        
        # Create user
        self.user, _ = User.objects.get_or_create(
            username="testuser",
            defaults={"email": "test@example.com"}
        )
        
        # Create sample type
        self.sample_type, _ = SampleType.objects.get_or_create(
            name="PCR",
            description="Polymerase Chain Reaction"
        )
        
        # Create a health lab sample
        self.lab_sample = HealthLabSample.objects.create(
            batch=self.batch,
            container=self.container,
            sample_date=timezone.now().date(),
            sample_type=self.sample_type,
            collected_by=self.user,
            lab_name="Test Lab",
            result_status="PENDING"
        )
    
    def test_lab_sample_creation(self):
        """Test that a lab sample can be created with required fields."""
        self.assertEqual(self.lab_sample.batch, self.batch)
        self.assertEqual(self.lab_sample.container, self.container)
        self.assertEqual(self.lab_sample.sample_type, self.sample_type)
        self.assertEqual(self.lab_sample.collected_by, self.user)
        self.assertEqual(self.lab_sample.lab_name, "Test Lab")
        self.assertEqual(self.lab_sample.result_status, "PENDING")
    
    def test_lab_sample_str(self):
        """Test the string representation of a lab sample."""
        expected_str = f"PCR - {self.batch} - {self.lab_sample.sample_date}"
        self.assertEqual(str(self.lab_sample), expected_str)
    
    def test_lab_sample_status_transition(self):
        """Test lab sample status transitions."""
        # Initial status should be PENDING
        self.assertEqual(self.lab_sample.result_status, "PENDING")
        
        # Update to RECEIVED
        self.lab_sample.result_status = "RECEIVED"
        self.lab_sample.save()
        self.assertEqual(self.lab_sample.result_status, "RECEIVED")
        
        # Update to COMPLETED
        self.lab_sample.result_status = "COMPLETED"
        self.lab_sample.result_value = "Negative"
        self.lab_sample.result_date = timezone.now().date()
        self.lab_sample.save()
        self.assertEqual(self.lab_sample.result_status, "COMPLETED")
    
    def test_sample_type_str(self):
        """Test the string representation of a sample type."""
        self.assertEqual(str(self.sample_type), "PCR")
