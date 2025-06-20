from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import IntegrityError # Import for testing constraints
from django.conf import settings
import unittest
from decimal import Decimal # Added for biomass/weight consistency
from datetime import date # Added for dates
import statistics # For calculating standard deviation

from apps.batch.models import Batch, Species, LifeCycleStage, BatchContainerAssignment # Added BatchContainerAssignment
from apps.infrastructure.models import Container, ContainerType, Hall, FreshwaterStation, Geography
from apps.health.models import (
    JournalEntry, MortalityReason, MortalityRecord, LiceCount,
    Treatment, SampleType,
    HealthParameter,
    # New health models
    HealthSamplingEvent,
    IndividualFishObservation,
    FishParameterScore,
    HealthLabSample, # Added HealthLabSample
    VaccinationType # Moved from treatment to vaccination module
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
            # Ensure BatchContainerAssignment is created for tests that need it
            self.batch_container_assignment = BatchContainerAssignment.objects.create(
                batch=self.batch,
                container=self.container,
                lifecycle_stage=self.lifecycle_stage, # Use the correct stage
                population_count=1000, # Corrected field name
                biomass_kg=Decimal('50.00'), # Example biomass
                assignment_date=date(2023, 1, 1),
                is_active=True
            )
            # print("BatchContainerAssignment created successfully")
        except Exception as e:
            print(f"Error creating BatchContainerAssignment: {e}")
            # If it fails, it might be because it's created elsewhere or a unique constraint issue if run multiple times
            # Try to fetch it if it already exists
            self.batch_container_assignment = BatchContainerAssignment.objects.filter(batch=self.batch, container=self.container).first()
            if not self.batch_container_assignment:
                print("Failed to create or fetch BatchContainerAssignment in setUp")
                raise

        try:
            self.sample_type = SampleType.objects.create(name='Test Histopathology', description='For histopathological analysis')
            # print("SampleType created successfully")
        except IntegrityError: # If it already exists from a previous run within the same test session
            self.sample_type = SampleType.objects.get(name='Test Histopathology')
        except Exception as e:
            print(f"Error creating SampleType: {e}")
            raise

        try:
            self.health_parameter = HealthParameter.objects.create(name='Skin Lesions', description_score_1='No lesions')
            # print("HealthParameter created successfully")
        except Exception as e:
            print(f"Error creating HealthParameter: {e}")
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
        self.assertEqual(retrieved_fish_obs.fish_identifier, '1')
        self.assertEqual(retrieved_fish_obs.parameter_scores.count(), 1)
        
        retrieved_score = retrieved_fish_obs.parameter_scores.first()
        self.assertEqual(retrieved_score.parameter, self.gill_health_param)
        self.assertEqual(retrieved_score.score, 1)

    # --- Tests for calculate_aggregate_metrics --- #

    def test_calculate_metrics_no_observations(self):
        """Test metrics calculation when there are no fish observations."""
        event = HealthSamplingEvent.objects.create(
            assignment=self.batch_container_assignment,
            sampling_date=date(2023, 4, 1),
            sampled_by=self.user,
            number_of_fish_sampled=0 # Intentionally 0 or could be >0 but no actual observations
        )
        event.calculate_aggregate_metrics()

        self.assertIsNone(event.avg_weight_g)
        self.assertIsNone(event.avg_length_cm)
        self.assertIsNone(event.std_dev_weight_g)
        self.assertIsNone(event.std_dev_length_cm)
        self.assertIsNone(event.min_weight_g)
        self.assertIsNone(event.max_weight_g)
        self.assertIsNone(event.min_length_cm)
        self.assertIsNone(event.max_length_cm)
        self.assertIsNone(event.avg_k_factor)
        self.assertEqual(event.calculated_sample_size, 0)

    def test_calculate_metrics_single_observation(self):
        """Test metrics calculation with a single fish observation."""
        event = HealthSamplingEvent.objects.create(
            assignment=self.batch_container_assignment,
            sampling_date=date(2023, 4, 2),
            sampled_by=self.user,
            number_of_fish_sampled=1
        )
        IndividualFishObservation.objects.create(
            sampling_event=event, fish_identifier=1, weight_g=Decimal('100.0'), length_cm=Decimal('10.0')
        )
        event.calculate_aggregate_metrics()

        self.assertEqual(event.avg_weight_g, Decimal('100.0'))
        self.assertEqual(event.avg_length_cm, Decimal('10.0'))
        self.assertIsNone(event.std_dev_weight_g) # Std dev is None for a single observation
        self.assertIsNone(event.std_dev_length_cm)
        self.assertEqual(event.min_weight_g, Decimal('100.0'))
        self.assertEqual(event.max_weight_g, Decimal('100.0'))
        self.assertEqual(event.min_length_cm, Decimal('10.0'))
        self.assertEqual(event.max_length_cm, Decimal('10.0'))
        expected_k_factor = (Decimal('100.0') / (Decimal('10.0') ** 3)) * 100
        self.assertAlmostEqual(event.avg_k_factor, expected_k_factor, places=2)
        self.assertEqual(event.calculated_sample_size, 1)

    def test_calculate_metrics_multiple_observations(self):
        """Test metrics calculation with multiple fish observations."""
        event = HealthSamplingEvent.objects.create(
            assignment=self.batch_container_assignment,
            sampling_date=date(2023, 4, 3),
            sampled_by=self.user,
            number_of_fish_sampled=3
        )
        obs_data = [
            {'id': 1, 'w': Decimal('100.0'), 'l': Decimal('10.0')},
            {'id': 2, 'w': Decimal('120.0'), 'l': Decimal('11.0')},
            {'id': 3, 'w': Decimal('110.0'), 'l': Decimal('10.5')},
        ]
        weights = [d['w'] for d in obs_data]
        lengths = [d['l'] for d in obs_data]
        k_factors = []

        for d in obs_data:
            IndividualFishObservation.objects.create(
                sampling_event=event, fish_identifier=d['id'], weight_g=d['w'], length_cm=d['l']
            )
            if d['w'] is not None and d['l'] is not None and d['l'] > 0:
                k_factors.append((d['w'] / (d['l'] ** 3)) * 100)
        
        event.calculate_aggregate_metrics()

        self.assertAlmostEqual(event.avg_weight_g, sum(weights) / len(weights), places=2)
        self.assertAlmostEqual(event.avg_length_cm, sum(lengths) / len(lengths), places=2)
        self.assertAlmostEqual(event.std_dev_weight_g, Decimal(statistics.stdev(weights)), places=2)
        self.assertAlmostEqual(event.std_dev_length_cm, Decimal(statistics.stdev(lengths)), places=2)
        self.assertEqual(event.min_weight_g, min(weights))
        self.assertEqual(event.max_weight_g, max(weights))
        self.assertEqual(event.min_length_cm, min(lengths))
        self.assertEqual(event.max_length_cm, max(lengths))
        if k_factors:
            self.assertAlmostEqual(event.avg_k_factor, sum(k_factors) / len(k_factors), places=2)
        else:
            self.assertIsNone(event.avg_k_factor)
        self.assertEqual(event.calculated_sample_size, len(obs_data))

    def test_calculate_metrics_with_missing_data(self):
        """Test metrics with some observations missing weight or length."""
        event = HealthSamplingEvent.objects.create(
            assignment=self.batch_container_assignment,
            sampling_date=date(2023, 4, 4),
            sampled_by=self.user,
            number_of_fish_sampled=4
        )
        # Fish 1: Full data
        obs1_w, obs1_l = Decimal('100.0'), Decimal('10.0')
        IndividualFishObservation.objects.create(sampling_event=event, fish_identifier=1, weight_g=obs1_w, length_cm=obs1_l)
        # Fish 2: Missing weight
        obs2_l = Decimal('11.0')
        IndividualFishObservation.objects.create(sampling_event=event, fish_identifier=2, weight_g=None, length_cm=obs2_l)
        # Fish 3: Missing length
        obs3_w = Decimal('120.0')
        IndividualFishObservation.objects.create(sampling_event=event, fish_identifier=3, weight_g=obs3_w, length_cm=None)
        # Fish 4: Full data
        obs4_w, obs4_l = Decimal('115.0'), Decimal('10.5')
        IndividualFishObservation.objects.create(sampling_event=event, fish_identifier=4, weight_g=obs4_w, length_cm=obs4_l)

        event.calculate_aggregate_metrics()

        valid_weights = [obs1_w, obs3_w, obs4_w]
        valid_lengths = [obs1_l, obs2_l, obs4_l]
        
        self.assertAlmostEqual(event.avg_weight_g, sum(valid_weights) / len(valid_weights), places=2)
        self.assertAlmostEqual(event.avg_length_cm, sum(valid_lengths) / len(valid_lengths), places=2)
        self.assertAlmostEqual(event.std_dev_weight_g, Decimal(statistics.stdev(valid_weights)), places=2)
        self.assertAlmostEqual(event.std_dev_length_cm, Decimal(statistics.stdev(valid_lengths)), places=2)
        self.assertEqual(event.min_weight_g, min(valid_weights))
        self.assertEqual(event.max_weight_g, max(valid_weights))
        self.assertEqual(event.min_length_cm, min(valid_lengths))
        self.assertEqual(event.max_length_cm, max(valid_lengths))

        k_factors = [
            (obs1_w / (obs1_l**3)) * 100,
            (obs4_w / (obs4_l**3)) * 100,
        ]
        self.assertAlmostEqual(event.avg_k_factor, sum(k_factors) / len(k_factors), places=2)
        # calculated_sample_size should count all observations passed in `number_of_fish_sampled`
        # or based on actual observation records if that's the logic. The current model logic
        # bases calculated_sample_size on actual observations with weight AND length for K-factor.
        # Let's assume it's based on observations that contribute to any metric.
        # The model's `calculate_aggregate_metrics` uses len(observations_with_weight_and_length) for k_factor sample size.
        # And len(weights_for_avg) or len(lengths_for_avg) for those respective sample sizes for std_dev.
        # The `calculated_sample_size` field in the model is defined as PositiveIntegerField
        # and the model code sets it to `len(observations_with_weight_and_length)`.
        self.assertEqual(event.calculated_sample_size, 2) # Only 2 fish have both W and L for K-factor

    def test_calculate_metrics_single_observation_no_length(self):
        """Test single observation missing length (K-factor should be None)."""
        event = HealthSamplingEvent.objects.create(
            assignment=self.batch_container_assignment,
            sampling_date=date(2023, 4, 5),
            sampled_by=self.user,
            number_of_fish_sampled=1
        )
        IndividualFishObservation.objects.create(
            sampling_event=event, fish_identifier=1, weight_g=Decimal('100.0'), length_cm=None
        )
        event.calculate_aggregate_metrics()
        self.assertEqual(event.avg_weight_g, Decimal('100.0'))
        self.assertIsNone(event.avg_length_cm)
        self.assertIsNone(event.avg_k_factor)
        self.assertEqual(event.calculated_sample_size, 0) # No obs for K-factor

    def test_calculate_metrics_single_observation_zero_length(self):
        """Test single observation with zero length (K-factor should be None to avoid ZeroDivisionError)."""
        event = HealthSamplingEvent.objects.create(
            assignment=self.batch_container_assignment,
            sampling_date=date(2023, 4, 6),
            sampled_by=self.user,
            number_of_fish_sampled=1
        )
        IndividualFishObservation.objects.create(
            sampling_event=event, fish_identifier=1, weight_g=Decimal('100.0'), length_cm=Decimal('0.0')
        )
        event.calculate_aggregate_metrics()
        self.assertEqual(event.avg_weight_g, Decimal('100.0'))
        self.assertEqual(event.avg_length_cm, Decimal('0.0'))
        self.assertIsNone(event.avg_k_factor) # K-factor calculation should handle L=0 gracefully
        self.assertEqual(event.calculated_sample_size, 0) # No valid obs for K-factor

    def test_health_lab_sample_creation(self):
        """Test creating a HealthLabSample instance."""
        sample_data = {
            'batch_container_assignment': self.batch_container_assignment,
            'sample_type': self.sample_type,
            'sample_date': date(2023, 5, 10),
            'date_sent_to_lab': date(2023, 5, 11),
            'date_results_received': date(2023, 5, 15),
            'lab_reference_id': 'LAB-REF-001',
            'findings_summary': 'No significant findings.',
            'quantitative_results': {'param1': 10.5, 'param2': 'positive'},
            'notes': 'Sample processed normally.',
            'recorded_by': self.user
            # 'attachment' field is tested separately or in API tests due to file handling
        }
        lab_sample = HealthLabSample.objects.create(**sample_data)

        self.assertEqual(lab_sample.batch_container_assignment, self.batch_container_assignment)
        self.assertEqual(lab_sample.sample_type, self.sample_type)
        self.assertEqual(lab_sample.sample_date, date(2023, 5, 10))
        self.assertEqual(lab_sample.date_sent_to_lab, date(2023, 5, 11))
        self.assertEqual(lab_sample.date_results_received, date(2023, 5, 15))
        self.assertEqual(lab_sample.lab_reference_id, 'LAB-REF-001')
        self.assertEqual(lab_sample.findings_summary, 'No significant findings.')
        self.assertEqual(lab_sample.quantitative_results['param1'], 10.5)
        self.assertEqual(lab_sample.quantitative_results['param2'], 'positive')
        self.assertEqual(lab_sample.notes, 'Sample processed normally.')
        self.assertEqual(lab_sample.recorded_by, self.user)
        self.assertIsNotNone(lab_sample.created_at)
        self.assertIsNotNone(lab_sample.updated_at)

        expected_str = f"Sample {lab_sample.lab_reference_id or lab_sample.id} for Batch {self.batch.batch_number} in Container {self.container.name} on {lab_sample.sample_date}"
        self.assertEqual(str(lab_sample), expected_str)

    def test_health_lab_sample_attachment_path(self):
        """Test assigning a path to the attachment field."""
        # This test only checks if the model can store a path-like string.
        # Actual file upload is typically handled and tested at the form/API level.
        attachment_path = 'uploads/health_lab_samples/sample_attachments/test_report.pdf'
        lab_sample = HealthLabSample.objects.create(
            batch_container_assignment=self.batch_container_assignment,
            sample_type=self.sample_type,
            sample_date=date(2023, 5, 12),
            lab_reference_id='LAB-REF-002',
            recorded_by=self.user,
            attachment=attachment_path # Assigning a string path
        )
        self.assertEqual(lab_sample.attachment.name, attachment_path)

        # Test __str__ when lab_reference_id is None (should use ID)
        lab_sample_no_ref = HealthLabSample.objects.create(
            batch_container_assignment=self.batch_container_assignment,
            sample_type=self.sample_type,
            sample_date=date(2023, 5, 13),
            recorded_by=self.user
        )
        expected_str_no_ref = f"Sample {lab_sample_no_ref.id} for Batch {self.batch.batch_number} in Container {self.container.name} on {lab_sample_no_ref.sample_date}"
        self.assertEqual(str(lab_sample_no_ref), expected_str_no_ref)
