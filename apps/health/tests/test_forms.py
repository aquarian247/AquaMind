from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from apps.health.admin import HealthLabSampleForm # Path to the form
from apps.health.models import SampleType, HealthLabSample
from apps.batch.models import (
    Species, LifeCycleStage, Batch, BatchContainerAssignment
)
from apps.infrastructure.models import (
    Container, Geography, FreshwaterStation, Hall, ContainerType
)

class HealthLabSampleFormTests(TestCase):
    """Tests for the HealthLabSampleForm used in the admin."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='formtestuser', password='password')
        
        cls.species = Species.objects.create(name='Test Species Form')
        cls.lc_stage = LifeCycleStage.objects.create(species=cls.species, name='Fry Form', order=1)
        
        cls.geography = Geography.objects.create(name="Form Test Geo")
        cls.station = FreshwaterStation.objects.create(name="Form Test Station", geography=cls.geography, station_type='FRESHWATER', latitude=10.0, longitude=10.0)
        cls.hall = Hall.objects.create(name="Form Test Hall", freshwater_station=cls.station)
        cls.container_type = ContainerType.objects.create(name="Form Test Tank Type", category='TANK', max_volume_m3=100)
        
        cls.container1 = Container.objects.create(name='FormC1', hall=cls.hall, container_type=cls.container_type, volume_m3=90, max_biomass_kg=500)
        cls.container2 = Container.objects.create(name='FormC2', hall=cls.hall, container_type=cls.container_type, volume_m3=90, max_biomass_kg=500)

        cls.batch1 = Batch.objects.create(
            batch_number='FORMB001', species=cls.species, lifecycle_stage=cls.lc_stage,
            start_date=date(2023, 1, 1),
            population_count=1500, # Initial population for the batch
            avg_weight_g=Decimal('5'), # Initial average weight for the batch
            biomass_kg=Decimal('7.5') # Initial biomass for the batch (1500 * 5 / 1000)
        )

        # Assignment active from 2023-01-10 to 2023-01-31
        cls.assignment_active_in_jan = BatchContainerAssignment.objects.create(
            batch=cls.batch1, container=cls.container1, lifecycle_stage=cls.lc_stage,
            assignment_date=date(2023, 1, 10), departure_date=date(2023, 1, 31),
            population_count=1000, avg_weight_g=Decimal('10'), biomass_kg=Decimal('10'), is_active=True
        )

        # Assignment active from 2023-02-05 (no departure date)
        cls.assignment_active_from_feb = BatchContainerAssignment.objects.create(
            batch=cls.batch1, container=cls.container2, lifecycle_stage=cls.lc_stage,
            assignment_date=date(2023, 2, 5),
            population_count=500, avg_weight_g=Decimal('20'), biomass_kg=Decimal('10'), is_active=True
        )
        
        cls.sample_type_tissue = SampleType.objects.create(name='Tissue Sample Form', description='Tissue for lab analysis')

    def test_form_valid_assignment_for_sample_date(self):
        """Test form is valid when batch_container_assignment is active on sample_date."""
        form_data = {
            'batch_container_assignment': self.assignment_active_in_jan.pk,
            'sample_type': self.sample_type_tissue.pk,
            'sample_date': date(2023, 1, 15), # Date within assignment_active_in_jan range
            # 'recorded_by' is excluded from form
        }
        form = HealthLabSampleForm(data=form_data)
        self.assertTrue(form.is_valid(), msg=f"Form errors: {form.errors.as_json()}")

    def test_form_invalid_assignment_sample_date_before_assignment(self):
        """Test form is invalid if sample_date is before assignment's active period."""
        form_data = {
            'batch_container_assignment': self.assignment_active_in_jan.pk,
            'sample_type': self.sample_type_tissue.pk,
            'sample_date': date(2023, 1, 1), # Date BEFORE assignment_active_in_jan.assignment_date (2023-01-10)
            # 'recorded_by' is excluded from form
        }
        form = HealthLabSampleForm(data=form_data)
        self.assertFalse(form.is_valid(), msg="Form should be invalid when sample_date is before assignment_date.")
        self.assertIn('sample_date', form.errors, msg="Error should be on sample_date field.")

    def test_form_invalid_assignment_sample_date_after_departure(self):
        """Test form is invalid if sample_date is after assignment's departure_date."""
        form_data = {
            'batch_container_assignment': self.assignment_active_in_jan.pk,
            'sample_type': self.sample_type_tissue.pk,
            'sample_date': date(2023, 2, 1), # Date AFTER assignment_active_in_jan.departure_date (2023-01-31)
            # 'recorded_by' is excluded from form
        }
        form = HealthLabSampleForm(data=form_data)
        self.assertFalse(form.is_valid(), msg="Form should be invalid if sample_date is after assignment's departure_date.")
        self.assertIn('sample_date', form.errors, msg="Error should be on sample_date field.")

    def test_form_valid_assignment_no_departure_date(self):
        """Test form is valid if assignment has no departure_date and sample_date is after assignment_date."""
        form_data = {
            'batch_container_assignment': self.assignment_active_from_feb.pk,
            'sample_type': self.sample_type_tissue.pk,
            'sample_date': date(2023, 3, 1), # Date after assignment_active_from_feb.assignment_date
            # 'recorded_by' is excluded from form
        }
        form = HealthLabSampleForm(data=form_data)
        self.assertTrue(form.is_valid(), msg=f"Form errors: {form.errors.as_json()}")

    def test_form_invalid_sample_date_greater_than_date_sent_to_lab(self):
        """Test existing validation: sample_date > date_sent_to_lab."""
        form_data = {
            'batch_container_assignment': self.assignment_active_in_jan.pk,
            'sample_type': self.sample_type_tissue.pk,
            'sample_date': date(2023, 1, 15),
            'date_sent_to_lab': date(2023, 1, 14), # sample_date is AFTER date_sent_to_lab
            # 'recorded_by' is excluded from form
        }
        form = HealthLabSampleForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('sample_date', form.errors) # Error should be on sample_date as per form's clean method

    def test_form_invalid_date_results_received_less_than_date_sent_to_lab(self):
        """Test existing validation: date_results_received < date_sent_to_lab."""
        form_data = {
            'batch_container_assignment': self.assignment_active_in_jan.pk,
            'sample_type': self.sample_type_tissue.pk,
            'sample_date': date(2023, 1, 15),
            'date_sent_to_lab': date(2023, 1, 20),
            'date_results_received': date(2023, 1, 19), # date_results_received is BEFORE date_sent_to_lab
            # 'recorded_by' is excluded from form
        }
        form = HealthLabSampleForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('date_results_received', form.errors) # Error should be on date_results_received
