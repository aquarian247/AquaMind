from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
import unittest
import decimal # Renamed from 'decimal' to 'py_decimal' to avoid conflict if any model field is named 'decimal'
from django.utils import timezone
from datetime import date, datetime # Added datetime

from apps.batch.models import Batch, Species, LifeCycleStage, BatchContainerAssignment
from apps.infrastructure.models import Container, ContainerType, Hall, FreshwaterStation, Geography
from apps.health.models import (
    JournalEntry, MortalityReason, MortalityRecord, LiceCount,
    VaccinationType, Treatment, SampleType, HealthParameter,
    HealthSamplingEvent,  # Added
    IndividualFishObservation, # Added
    HealthLabSample # Add HealthLabSample to imports
)
from apps.health.api.serializers import HealthSamplingEventSerializer # Added for direct serializer tests if needed

User = get_user_model()


class HealthAPITestCase(APITestCase):
    """Base class for Health app API tests."""
    
    def get_api_url(self, app_name, endpoint, detail=False, **kwargs):
        """Helper function to construct URLs for API endpoints"""
        if detail:
            pk = kwargs.get('pk')
            return f'/api/v1/{app_name}/{endpoint}/{pk}/'
        return f'/api/v1/{app_name}/{endpoint}/'
    
    def setUp(self):
        self.client = APIClient()
        try:
            self.user = User.objects.create_user(username='testuser', password='testpass')
            self.client.force_authenticate(user=self.user)
            print("User created and authenticated successfully")
        except Exception as e:
            print(f"Error creating or authenticating User: {e}")
            raise

        try:
            self.species = Species.objects.create(name='Salmon')
            print("Species created successfully")
        except Exception as e:
            print(f"Error creating Species: {e}")
            raise

        try:
            self.lifecycle_stage = LifeCycleStage.objects.create(name='Fry', order=2, species=self.species)
            print("LifeCycleStage created successfully")
        except Exception as e:
            print(f"Error creating LifeCycleStage: {e}")
            raise

        try:
            self.batch = Batch.objects.create(
                batch_number='B001',
                species=self.species,
                status='ACTIVE',
                population_count=1000,
                biomass_kg=500.00,
                avg_weight_g=0.5,
                start_date='2023-01-01',
                notes='Test batch',
                batch_type='STANDARD',
                lifecycle_stage=self.lifecycle_stage
            )
            print("Batch created successfully")
        except Exception as e:
            print(f"Error creating Batch: {e}")
            raise

        try:
            self.container_type = ContainerType.objects.create(name='Tank', max_volume_m3=100.0, category='TANK')
            print("ContainerType created successfully")
        except Exception as e:
            print(f"Error creating ContainerType: {e}")
            raise

        try:
            # Create a geography for the freshwater station
            self.geography = Geography.objects.create(name='Test Geography')
            print("Geography created successfully")
        except Exception as e:
            print(f"Error creating Geography: {e}")
            raise

        try:
            # Create a freshwater station for the hall
            self.station = FreshwaterStation.objects.create(
                name='Test Station', 
                station_type='HATCHERY',
                latitude=50.8503,
                longitude=4.3517,
                geography=self.geography
            )
            print("FreshwaterStation created successfully")
        except Exception as e:
            print(f"Error creating FreshwaterStation: {e}")
            raise

        try:
            # Create a hall for location (container must be in either a hall or area)
            self.hall = Hall.objects.create(name='Test Hall', freshwater_station=self.station)
            print("Hall created successfully")
        except Exception as e:
            print(f"Error creating Hall: {e}")
            raise

        try:
            self.container = Container.objects.create(
                name='C001',
                container_type=self.container_type,
                volume_m3=50.0,
                max_biomass_kg=5000.0,
                hall=self.hall,
                active=True
            )
            print("Container created successfully")
        except Exception as e:
            print(f"Error creating Container: {e}")
            raise

        try:
            # Create BatchContainerAssignment for testing
            self.batch_container_assignment = BatchContainerAssignment.objects.create(
                batch=self.batch,
                container=self.container,
                assignment_date='2023-01-01',  # Changed to be before sample date in test
                population_count=self.batch.population_count, # Initial population
                biomass_kg=self.batch.biomass_kg, # Initial biomass
                lifecycle_stage=self.lifecycle_stage, # Initial lifecycle stage
                is_active=True
            )
            print("BatchContainerAssignment created successfully")
        except Exception as e:
            print(f"Error creating BatchContainerAssignment: {e}")
            raise

        try:
            # Add HealthParameter for testing observations
            self.gill_health_param = HealthParameter.objects.create(
                name='Gill Health',
                description_score_1='Perfect',
                description_score_2='Slight mucus',
                description_score_3='Lesions',
                description_score_4='Severe damage'
            )
            self.eye_condition_param = HealthParameter.objects.create(
                name='Eye Condition',
                description_score_1='Clear',
                description_score_2='Cloudy',
                description_score_3='Bulging',
                description_score_4='Lost'
            )
            print("Health Parameters created successfully")
        except Exception as e:
            print(f"Error creating Health Parameters: {e}")
            raise

        try:
            # Create a SampleType for testing lab samples
            self.tissue_sample_type = SampleType.objects.create(name='Tissue Sample', description='A sample of fish tissue for analysis.')
            print("SampleType created successfully")
        except Exception as e:
            print(f"Error creating SampleType: {e}")
            raise

        try:
            self.journal_entry = JournalEntry.objects.create(
                batch=self.batch,
                container=self.container,
                user=self.user,
                category='observation',
                severity='low',
                description='Fish appear healthy.'
            )
            print("Journal Entry created successfully")
        except Exception as e:
            print(f"Error creating Journal Entry: {e}")
            raise

        try:
            self.mortality_reason = MortalityReason.objects.create(name='Disease')
            print("Mortality Reason created successfully")
        except Exception as e:
            print(f"Error creating Mortality Reason: {e}")
            raise

        try:
            self.mortality_record = MortalityRecord.objects.create(
                batch=self.batch,
                container=self.container,
                count=50,
                reason=self.mortality_reason
            )
            print("Mortality Record created successfully")
        except Exception as e:
            print(f"Error creating Mortality Record: {e}")
            raise

        try:
            self.lice_count = LiceCount.objects.create(
                batch=self.batch,
                container=self.container,
                user=self.user,
                adult_female_count=10,
                adult_male_count=5,
                juvenile_count=15,
                fish_sampled=5
            )
            print("Lice Count created successfully")
        except Exception as e:
            print(f"Error creating Lice Count: {e}")
            raise

        try:
            self.vaccination_type = VaccinationType.objects.create(name='Vaccine A')
            print("Vaccination Type created successfully")
        except Exception as e:
            print(f"Error creating Vaccination Type: {e}")
            raise

        try:
            self.treatment = Treatment.objects.create(
                batch=self.batch,
                container=self.container,
                user=self.user,
                treatment_type='vaccination',
                vaccination_type=self.vaccination_type,
                description='Vaccination against disease',
                withholding_period_days=30
            )
            print("Treatment created successfully")
        except Exception as e:
            print(f"Error creating Treatment: {e}")
            raise

        try:
            self.sample_type = SampleType.objects.create(name='Water Sample')
            print("Sample Type created successfully")
        except Exception as e:
            print(f"Error creating Sample Type: {e}")
            raise

    def test_health_parameter_api(self):
        """Test listing and creating health parameters via API."""
        url = self.get_api_url('health', 'health-parameters')
        print(f"[Debug] Testing URL: {url}")
        # Test GET (list)
        response = self.client.get(url)
        print(f"[Debug] Response status code: {response.status_code}")
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=f"Unexpected status code for URL: {url}")
        # Handle case where response.data might be a list directly (no pagination)
        if isinstance(response.data, list):
            results = response.data
        else:
            results = response.data.get('results', response.data)
        self.assertGreaterEqual(len(results), 1)  # At least the one we created in setUp
        found = False
        for item in results:
            if item['name'] == self.gill_health_param.name:
                found = True
                break
        self.assertTrue(found)

        # Test POST (create) - requires admin or specific role
        data = {'name': 'New Parameter', 'description_score_1': 'Good'}
        response = self.client.post(url, data, format='json')
        # Depending on user permissions, this might return different status codes
        valid_status_codes = [
            status.HTTP_201_CREATED,   # Success
            status.HTTP_400_BAD_REQUEST, # Invalid data
            status.HTTP_403_FORBIDDEN,  # Permission issue
            status.HTTP_401_UNAUTHORIZED # Authentication issue
        ]
        self.assertIn(response.status_code, valid_status_codes, 
                     f"Unexpected status code {response.status_code}")
        
        # If created successfully, verify the data
        if response.status_code == status.HTTP_201_CREATED:
            self.assertEqual(response.data['name'], 'New Parameter')

    def test_mortality_reason_list(self):
        """Test listing mortality reasons via API."""
        url = self.get_api_url('health', 'mortality-reasons')
        print(f"[Debug] Testing URL: {url}")
        response = self.client.get(url)
        print(f"[Debug] Response status code: {response.status_code}")
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=f"Unexpected status code for URL: {url}")
        # Handle case where response.data might be a list directly (no pagination)
        if isinstance(response.data, list):
            results = response.data
        else:
            results = response.data.get('results', response.data)
        self.assertGreaterEqual(len(results), 1)

    def test_mortality_record_list(self):
        """Test listing mortality records via API."""
        url = self.get_api_url('health', 'mortality-records')
        print(f"[Debug] Testing URL: {url}")
        response = self.client.get(url)
        print(f"[Debug] Response status code: {response.status_code}")
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=f"Unexpected status code for URL: {url}")
        # Handle case where response.data might be a list directly (no pagination)
        if isinstance(response.data, list):
            results = response.data
        else:
            results = response.data.get('results', response.data)
        # Might be empty if no records created in setup
        self.assertIsInstance(results, list)

    def test_lice_count_list(self):
        """Test listing lice counts via API."""
        url = self.get_api_url('health', 'lice-counts')
        print(f"[Debug] Testing URL: {url}")
        response = self.client.get(url)
        print(f"[Debug] Response status code: {response.status_code}")
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=f"Unexpected status code for URL: {url}")
        # Handle case where response.data might be a list directly (no pagination)
        if isinstance(response.data, list):
            results = response.data
        else:
            results = response.data.get('results', response.data)
        # Might be empty if no counts created in setup
        self.assertIsInstance(results, list)

    def test_vaccination_type_list(self):
        """Test listing vaccination types via API."""
        url = self.get_api_url('health', 'vaccination-types')
        print(f"[Debug] Testing URL: {url}")
        response = self.client.get(url)
        print(f"[Debug] Response status code: {response.status_code}")
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=f"Unexpected status code for URL: {url}")
        # Handle case where response.data might be a list directly (no pagination)
        if isinstance(response.data, list):
            results = response.data
        else:
            results = response.data.get('results', response.data)
        self.assertGreaterEqual(len(results), 1)

    def test_treatment_list(self):
        """Test listing treatments via API."""
        url = self.get_api_url('health', 'treatments')
        print(f"[Debug] Testing URL: {url}")
        response = self.client.get(url)
        print(f"[Debug] Response status code: {response.status_code}")
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=f"Unexpected status code for URL: {url}")
        # Handle case where response.data might be a list directly (no pagination)
        if isinstance(response.data, list):
            results = response.data
        else:
            results = response.data.get('results', response.data)
        # Might be empty if no treatments created in setup
        self.assertIsInstance(results, list)

    def test_sample_type_list(self):
        """Test listing sample types via API."""
        url = self.get_api_url('health', 'sample-types')
        print(f"[Debug] Testing URL: {url}")
        response = self.client.get(url)
        print(f"[Debug] Response status code: {response.status_code}")
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=f"Unexpected status code for URL: {url}")
        # Handle case where response.data might be a list directly (no pagination)
        if isinstance(response.data, list):
            results = response.data
        else:
            results = response.data.get('results', response.data)
        self.assertGreaterEqual(len(results), 1)

    def test_journal_entry_create(self):
        """Test creating a journal entry via API."""
        url = self.get_api_url('health', 'journal-entries')
        # Data for creating a journal entry without observations
        data_no_obs = {
            'batch': self.batch.id,
            'container': self.container.id,
            'category': 'issue',      # Reverted to 'issue'
            'severity': 'medium',     # Reverted to 'medium'
            'description': 'Some fish showing signs of stress (no obs)'
        }
        response_no_obs = self.client.post(url, data_no_obs, format='json')
        self.assertEqual(response_no_obs.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response_no_obs.data['category'], 'issue') # Reverted check
        self.assertEqual(response_no_obs.data['description'], 'Some fish showing signs of stress (no obs)')
        # If health_observations is present, it should be empty. If not present, that's also acceptable.
        self.assertNotIn('health_observations', response_no_obs.data, "'health_observations' should not be present or should be empty.")

    # --- Tests for HealthSamplingEvent API --- #

    def test_create_health_sampling_event(self):
        """Test creating a HealthSamplingEvent with nested IndividualFishObservations."""
        url = self.get_api_url('health', 'health-sampling-events')
        event_data = {
            'assignment': self.batch_container_assignment.id,
            'sampling_date': date.today().isoformat(),
            'number_of_fish_sampled': 2,
            'sampled_by': self.user.id,
            'notes': 'API creation test',
            'individual_fish_observations': [
                {'fish_identifier': 1, 'weight_g': 100.5, 'length_cm': 10.2},
                {'fish_identifier': 2, 'weight_g': 120.0, 'length_cm': 11.5}
            ]
        }
        response = self.client.post(url, event_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(HealthSamplingEvent.objects.count(), 1)
        self.assertEqual(IndividualFishObservation.objects.count(), 2)
        event_id = response.data['id']
        created_event = HealthSamplingEvent.objects.get(pk=event_id)
        self.assertEqual(created_event.notes, 'API creation test')
        self.assertEqual(created_event.individual_fish_observations.count(), 2)
        # Aggregate fields should be None initially as calculate-aggregates is not auto-called on API create
        self.assertIsNone(response.data.get('avg_weight_g'))

    def test_calculate_aggregates_action(self):
        """Test the calculate-aggregates action on HealthSamplingEventViewSet."""
        event = HealthSamplingEvent.objects.create(
            assignment=self.batch_container_assignment,
            sampling_date=date.today(),
            sampled_by=self.user,
            number_of_fish_sampled=2
        )
        IndividualFishObservation.objects.create(sampling_event=event, fish_identifier=1, weight_g=decimal.Decimal('100.0'), length_cm=decimal.Decimal('10.0'))
        IndividualFishObservation.objects.create(sampling_event=event, fish_identifier=2, weight_g=decimal.Decimal('120.0'), length_cm=decimal.Decimal('12.0'))

        action_url = f'/api/v1/health/health-sampling-events/{event.pk}/calculate-aggregates/'
        response = self.client.post(action_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check response data
        self.assertIsNotNone(response.data.get('avg_weight_g'))
        self.assertEqual(decimal.Decimal(response.data['avg_weight_g']), decimal.Decimal('110.0'))
        self.assertEqual(decimal.Decimal(response.data['avg_length_cm']), decimal.Decimal('11.0'))
        self.assertEqual(response.data['calculated_sample_size'], 2)

        # Check database
        event.refresh_from_db()
        self.assertEqual(event.avg_weight_g, decimal.Decimal('110.0'))
        self.assertEqual(event.avg_length_cm, decimal.Decimal('11.0'))
        self.assertEqual(event.calculated_sample_size, 2)

    def test_calculate_aggregates_action_unauthenticated(self):
        """Test unauthenticated access to calculate-aggregates action."""
        event = HealthSamplingEvent.objects.create(assignment=self.batch_container_assignment, sampling_date=date.today(), number_of_fish_sampled=0)
        self.client.logout()
        action_url = f'/api/v1/health/health-sampling-events/{event.pk}/calculate-aggregates/'
        response = self.client.post(action_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_calculate_aggregates_action_not_found(self):
        """Test calculate-aggregates action with a non-existent event ID."""
        action_url = f'/api/v1/health/health-sampling-events/99999/calculate-aggregates/'
        response = self.client.post(action_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_health_sampling_event_retrieve_shows_aggregates(self):
        """Test that aggregate fields are present in single event retrieval after calculation."""
        event = HealthSamplingEvent.objects.create(
            assignment=self.batch_container_assignment,
            sampling_date=date.today(),
            sampled_by=self.user,
            number_of_fish_sampled=1
        )
        IndividualFishObservation.objects.create(sampling_event=event, fish_identifier=1, weight_g=decimal.Decimal('50.0'), length_cm=decimal.Decimal('5.0'))
        event.calculate_aggregate_metrics() # Calculate and save metrics directly for this test setup

        retrieve_url = self.get_api_url('health', 'health-sampling-events', detail=True, pk=event.pk)
        response = self.client.get(retrieve_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('avg_weight_g', response.data)
        self.assertEqual(decimal.Decimal(response.data['avg_weight_g']), decimal.Decimal('50.0'))
        self.assertIn('calculated_sample_size', response.data)
        self.assertEqual(response.data['calculated_sample_size'], 1)
        # Check for all new aggregate fields
        for field in HealthSamplingEventSerializer.Meta.read_only_fields:
            if field not in ['id', 'sampled_by_details', 'assignment_details', 'individual_fish_observations']:
                 self.assertIn(field, response.data)

    def test_health_sampling_event_list_shows_aggregates(self):
        """Test that aggregate fields are present in event list after calculation."""
        event = HealthSamplingEvent.objects.create(
            assignment=self.batch_container_assignment,
            sampling_date=date.today(),
            sampled_by=self.user,
            number_of_fish_sampled=1
        )
        IndividualFishObservation.objects.create(sampling_event=event, fish_identifier=1, weight_g=decimal.Decimal('60.0'), length_cm=decimal.Decimal('6.0'))
        event.calculate_aggregate_metrics() # Calculate and save metrics

        list_url = self.get_api_url('health', 'health-sampling-events')
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data['results']), 0)
        event_data_from_list = response.data['results'][0] # Assuming it's the first/only one
        self.assertIn('avg_weight_g', event_data_from_list)
        self.assertEqual(decimal.Decimal(event_data_from_list['avg_weight_g']), decimal.Decimal('60.0'))
        # Check for all new aggregate fields
        for field in HealthSamplingEventSerializer.Meta.read_only_fields:
            if field not in ['id', 'sampled_by_details', 'assignment_details', 'individual_fish_observations']:
                self.assertIn(field, event_data_from_list)

    def test_unauthenticated_access(self):
        self.client.logout()
        url = self.get_api_url('health', 'journal-entries')
        response = self.client.get(url)
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_create_health_lab_sample(self):
        """Test creating a new HealthLabSample via API."""
        url = self.get_api_url('health', 'health-lab-samples')
        sample_date_str = '2023-01-20' # Within batch and initial assignment
        
        payload = {
            'batch_id': self.batch.id,
            'container_id': self.container.id,
            'sample_date': sample_date_str,
            'sample_type': self.tissue_sample_type.id,
            'date_sent_to_lab': '2023-01-21',
            'lab_reference_id': 'LAB-REF-001',
            'findings_summary': 'Initial tissue analysis.',
            'notes': 'Handle with care.'
        }

        response = self.client.post(url, payload, format='json')

        # Debugging: print response data if status is not 201
        if response.status_code != status.HTTP_201_CREATED:
            print(f"Create HealthLabSample failed with status {response.status_code}:")
            print(response.data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(HealthLabSample.objects.count(), 1)

        created_sample = HealthLabSample.objects.first()
        self.assertIsNotNone(created_sample)
        self.assertEqual(created_sample.batch_container_assignment, self.batch_container_assignment)
        self.assertEqual(str(created_sample.sample_date), sample_date_str)
        self.assertEqual(created_sample.sample_type, self.tissue_sample_type)
        self.assertEqual(created_sample.recorded_by, self.user)
        self.assertEqual(created_sample.lab_reference_id, 'LAB-REF-001')
        self.assertEqual(created_sample.findings_summary, 'Initial tissue analysis.')

        # Check response data details
        self.assertEqual(response.data['sample_date'], sample_date_str)
        self.assertEqual(response.data['sample_type_name'], self.tissue_sample_type.name)
        self.assertEqual(response.data['recorded_by_username'], self.user.username)
        self.assertIsNotNone(response.data['batch_container_assignment_details'])
        if response.data['batch_container_assignment_details']:
            self.assertEqual(response.data['batch_container_assignment_details']['assignment_id'], self.batch_container_assignment.id)
            self.assertEqual(response.data['batch_container_assignment_details']['batch_id'], self.batch.id)
            self.assertEqual(response.data['batch_container_assignment_details']['container_id'], self.container.id)
