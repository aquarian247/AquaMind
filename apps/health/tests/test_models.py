from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import IntegrityError # Import for testing constraints
from django.conf import settings
import unittest
from decimal import Decimal # Added for biomass/weight consistency
from datetime import date # Added for dates

from apps.batch.models import Batch, Species, LifeCycleStage, BatchContainerAssignment # Added BatchContainerAssignment
from apps.infrastructure.models import Container, ContainerType, Hall, FreshwaterStation, Geography
from apps.health.models import (
    JournalEntry, MortalityReason, MortalityRecord, LiceCount,
    VaccinationType, Treatment, SampleType,
    HealthParameter,
    # New health models
    HealthSamplingEvent,
    IndividualFishObservation,
    FishParameterScore
)

User = get_user_model()


class HealthModelsTestCase(TestCase):
    def setUp(self):
        try:
            self.user = User.objects.create_user(username='testuser', password='testpass')
            # print("User created successfully")
        except Exception as e:
            print(f"Error creating User: {e}")
            raise

        try:
            self.species = Species.objects.create(name='Salmon')
            # print("Species created successfully")
        except Exception as e:
            print(f"Error creating Species: {e}")
            raise

        try:
            self.lifecycle_stage = LifeCycleStage.objects.create(name='Fry', order=2, species=self.species)
            # print("LifeCycleStage created successfully")
        except Exception as e:
            print(f"Error creating LifeCycleStage: {e}")
            raise

        try:
            self.batch = Batch.objects.create(
                batch_number='B001',
                species=self.species,
                status='ACTIVE',
                population_count=1000,
                biomass_kg=Decimal('500.00'),
                avg_weight_g=Decimal('0.5'),
                start_date='2023-01-01',
                notes='Test batch',
                batch_type='STANDARD',
                lifecycle_stage=self.lifecycle_stage
            )
            # print("Batch created successfully")
        except Exception as e:
            print(f"Error creating Batch: {e}")
            raise

        try:
            self.container_type = ContainerType.objects.create(name='Tank', max_volume_m3=Decimal('100.0'), category='TANK')
            # print("ContainerType created successfully")
        except Exception as e:
            print(f"Error creating ContainerType: {e}")
            raise

        try:
            self.geography = Geography.objects.create(name='Test Geography')
            # print("Geography created successfully")
        except Exception as e:
            print(f"Error creating Geography: {e}")
            raise

        try:
            self.station = FreshwaterStation.objects.create(
                name='Test Station', 
                station_type='HATCHERY',
                latitude=Decimal('50.8503'),
                longitude=Decimal('4.3517'),
                geography=self.geography
            )
            # print("FreshwaterStation created successfully")
        except Exception as e:
            print(f"Error creating FreshwaterStation: {e}")
            raise

        try:
            self.hall = Hall.objects.create(name='Test Hall', freshwater_station=self.station)
            # print("Hall created successfully")
        except Exception as e:
            print(f"Error creating Hall: {e}")
            raise

        try:
            self.container = Container.objects.create(
                name='C001',
                container_type=self.container_type,
                volume_m3=Decimal('50.0'),
                max_biomass_kg=Decimal('5000.0'),
                hall=self.hall,
                active=True
            )
            # print("Container created successfully")
        except Exception as e:
            print(f"Error creating Container: {e}")
            raise

        try:
            self.batch_container_assignment = BatchContainerAssignment.objects.create(
                batch=self.batch,
                container=self.container,
                assignment_date=date(2023, 1, 10),
                population_count=self.batch.population_count,
                biomass_kg=self.batch.biomass_kg,
                lifecycle_stage=self.batch.lifecycle_stage
            )
            # print("BatchContainerAssignment created successfully")
        except Exception as e:
            print(f"Error creating BatchContainerAssignment: {e}")
            raise

        try:
            self.gill_health_param = HealthParameter.objects.create(
                name='Gill Health',
                description_score_1='Perfect gills, pink and healthy.',
                description_score_2='Slight paleness or minor mucus.',
                description_score_3='Noticeable lesions or heavy mucus.',
                description_score_4='Severe damage, necrosis.'
            )
            # print("HealthParameter created successfully")
        except Exception as e:
            print(f"Error creating HealthParameter: {e}")
            raise

    def test_journal_entry_creation(self):
        entry = JournalEntry.objects.create(
            batch=self.batch,
            container=self.container,
            user=self.user,
            category='observation',
            severity='low',
            description='Fish appear healthy.'
        )
        self.assertEqual(entry.category, 'observation')
        self.assertEqual(entry.severity, 'low')
        self.assertEqual(entry.description, 'Fish appear healthy.')
        self.assertFalse(entry.resolution_status)
        self.assertEqual(str(entry), f"Observation - {entry.entry_date.strftime('%Y-%m-%d')}")

    def test_health_parameter_creation(self):
        param = HealthParameter.objects.create(
            name='Eye Condition',
            description_score_1='Clear, bright eyes.',
            description_score_2='Slight cloudiness.',
            description_score_3='Significant cloudiness or bulging.',
            description_score_4='Severe damage or loss of eye.'
        )
        self.assertEqual(param.name, 'Eye Condition')
        self.assertTrue(param.is_active)
        self.assertEqual(str(param), 'Eye Condition')

    def test_mortality_reason_creation(self):
        reason = MortalityReason.objects.create(name='Disease', description='Infectious disease outbreak')
        self.assertEqual(reason.name, 'Disease')
        self.assertEqual(reason.description, 'Infectious disease outbreak')
        self.assertEqual(str(reason), 'Disease')

    def test_mortality_record_creation(self):
        reason = MortalityReason.objects.create(name='Disease')
        record = MortalityRecord.objects.create(
            batch=self.batch,
            container=self.container,
            count=50,
            reason=reason,
            notes='Significant loss due to disease'
        )
        self.assertEqual(record.count, 50)
        self.assertEqual(record.reason, reason)
        self.assertEqual(record.notes, 'Significant loss due to disease')
        self.assertEqual(str(record), f"Mortality of 50 on {record.event_date.strftime('%Y-%m-%d')}")

    def test_lice_count_creation(self):
        count = LiceCount.objects.create(
            batch=self.batch,
            container=self.container,
            user=self.user,
            adult_female_count=10,
            adult_male_count=5,
            juvenile_count=15,
            fish_sampled=5
        )
        self.assertEqual(count.adult_female_count, 10)
        self.assertEqual(count.adult_male_count, 5)
        self.assertEqual(count.juvenile_count, 15)
        self.assertEqual(count.fish_sampled, 5)
        self.assertEqual(count.average_per_fish, 6.0)  # (10+5+15)/5
        self.assertEqual(str(count), f"Lice Count: 30 on {count.count_date.strftime('%Y-%m-%d')}")

    def test_vaccination_type_creation(self):
        vtype = VaccinationType.objects.create(
            name='Vaccine A',
            manufacturer='PharmaCorp',
            dosage='0.5ml',
            description='Protects against common diseases'
        )
        self.assertEqual(vtype.name, 'Vaccine A')
        self.assertEqual(vtype.manufacturer, 'PharmaCorp')
        self.assertEqual(vtype.dosage, '0.5ml')
        self.assertEqual(str(vtype), 'Vaccine A')

    def test_treatment_creation(self):
        vtype = VaccinationType.objects.create(name='Vaccine A')
        treatment = Treatment.objects.create(
            batch=self.batch,
            container=self.container,
            user=self.user,
            treatment_type='vaccination',
            vaccination_type=vtype,
            description='Vaccination against disease',
            dosage='0.5ml',
            duration_days=1,
            withholding_period_days=30
        )
        self.assertEqual(treatment.treatment_type, 'vaccination')
        self.assertEqual(treatment.vaccination_type, vtype)
        self.assertEqual(treatment.dosage, '0.5ml')
        self.assertEqual(treatment.withholding_period_days, 30)
        self.assertEqual(str(treatment), f"Vaccination on {treatment.treatment_date.strftime('%Y-%m-%d')}")

    def test_sample_type_creation(self):
        stype = SampleType.objects.create(name='Water Sample', description='Sample for water quality testing')
        self.assertEqual(stype.name, 'Water Sample')
        self.assertEqual(stype.description, 'Sample for water quality testing')
        self.assertEqual(str(stype), 'Water Sample')

    def test_health_sampling_event_creation(self):
        """Test creating a HealthSamplingEvent instance."""
        sampling_event = HealthSamplingEvent.objects.create(
            assignment=self.batch_container_assignment,
            sampling_date=date(2023, 2, 1),
            sampled_by=self.user,
            number_of_fish_sampled=10,
            notes='Routine health check.'
        )
        self.assertEqual(sampling_event.assignment, self.batch_container_assignment)
        self.assertEqual(sampling_event.sampling_date, date(2023, 2, 1))
        self.assertEqual(sampling_event.sampled_by, self.user)
        self.assertEqual(sampling_event.number_of_fish_sampled, 10)
        self.assertEqual(str(sampling_event), f"Health Sample - {self.batch_container_assignment} - 2023-02-01")

    def test_individual_fish_observation_creation(self):
        """Test creating an IndividualFishObservation instance."""
        sampling_event = HealthSamplingEvent.objects.create(
            assignment=self.batch_container_assignment,
            sampling_date=date(2023, 2, 15),
            sampled_by=self.user,
            number_of_fish_sampled=5
        )
        fish_observation = IndividualFishObservation.objects.create(
            sampling_event=sampling_event,
            fish_identifier=1,
            length_cm=Decimal('10.5'),
            weight_g=Decimal('150.2')
        )
        self.assertEqual(fish_observation.sampling_event, sampling_event)
        self.assertEqual(fish_observation.fish_identifier, 1)
        self.assertEqual(fish_observation.length_cm, Decimal('10.5'))
        self.assertEqual(fish_observation.weight_g, Decimal('150.2'))
        self.assertEqual(str(fish_observation), f"Fish #{fish_observation.fish_identifier} (Event: {sampling_event.id})")

    def test_fish_parameter_score_creation(self):
        """Test creating a FishParameterScore instance."""
        sampling_event = HealthSamplingEvent.objects.create(
            assignment=self.batch_container_assignment,
            sampling_date=date(2023, 3, 1),
            sampled_by=self.user,
            number_of_fish_sampled=3
        )
        fish_observation = IndividualFishObservation.objects.create(
            sampling_event=sampling_event,
            fish_identifier=1
        )
        param_score = FishParameterScore.objects.create(
            individual_fish_observation=fish_observation,
            parameter=self.gill_health_param,
            score=2
        )
        self.assertEqual(param_score.individual_fish_observation, fish_observation)
        self.assertEqual(param_score.parameter, self.gill_health_param)
        self.assertEqual(param_score.score, 2)
        self.assertEqual(str(param_score), f"{fish_observation} - {self.gill_health_param.name}: {param_score.score}")

    def test_health_sampling_relationships(self):
        """Test relationships between health sampling models."""
        sampling_event = HealthSamplingEvent.objects.create(
            assignment=self.batch_container_assignment,
            sampling_date=date(2023, 3, 10),
            sampled_by=self.user,
            number_of_fish_sampled=1
        )
        fish_obs1 = IndividualFishObservation.objects.create(
            sampling_event=sampling_event, fish_identifier=1
        )
        FishParameterScore.objects.create(
            individual_fish_observation=fish_obs1,
            parameter=self.gill_health_param,
            score=1
        )
        # Retrieve the event and check related objects
        retrieved_event = HealthSamplingEvent.objects.get(pk=sampling_event.pk)
        self.assertEqual(retrieved_event.individual_fish_observations.count(), 1)
        
        retrieved_fish_obs = retrieved_event.individual_fish_observations.first()
        self.assertEqual(retrieved_fish_obs.fish_identifier, 1)
        self.assertEqual(retrieved_fish_obs.parameter_scores.count(), 1)
        
        retrieved_score = retrieved_fish_obs.parameter_scores.first()
        self.assertEqual(retrieved_score.parameter, self.gill_health_param)
        self.assertEqual(retrieved_score.score, 1)
