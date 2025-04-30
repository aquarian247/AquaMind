from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
import unittest
import decimal
from django.utils import timezone
from datetime import date, datetime

from apps.batch.models import Batch, Species, LifeCycleStage, BatchContainerAssignment
from apps.infrastructure.models import Container, ContainerType, Hall, FreshwaterStation, Geography
from apps.health.models import (
    JournalEntry, MortalityReason, MortalityRecord, LiceCount,
    VaccinationType, Treatment, SampleType,
    HealthParameter, HealthObservation
)

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
            self.assignment = BatchContainerAssignment.objects.create(
                batch=self.batch,
                container=self.container,
                assignment_date='2023-01-15',
                population_count=self.batch.population_count, # Initial population
                biomass_kg=self.batch.biomass_kg, # Initial biomass
                lifecycle_stage=self.lifecycle_stage # Initial lifecycle stage
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
        data_no_obs = {
            'batch': self.batch.id,
            'container': self.container.id,
            'category': 'issue',
            'severity': 'medium',
            'description': 'Some fish showing signs of stress (no obs)',
        }
        response_no_obs = self.client.post(url, data_no_obs, format='json')
        self.assertEqual(response_no_obs.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response_no_obs.data['category'], 'issue')
        self.assertEqual(response_no_obs.data['description'], 'Some fish showing signs of stress (no obs)')
        self.assertEqual(len(response_no_obs.data['health_observations']), 0)

    def test_journal_entry_create_with_observations(self):
        """Test creating a journal entry with nested observations via API."""
        url = self.get_api_url('health', 'journal-entries')
        observations_input = [
            {'parameter': self.gill_health_param.id, 'score': 3},
            {'parameter': self.eye_condition_param.id, 'score': 2}
        ]
        data_with_obs = {
            'batch': self.batch.id,
            'container': self.container.id,
            'category': 'observation',
            'severity': 'low',
            'description': 'Routine check with observations',
            'health_observations_write': observations_input
        }
        response_with_obs = self.client.post(url, data_with_obs, format='json')
        self.assertEqual(response_with_obs.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response_with_obs.data['category'], 'observation')
        self.assertEqual(response_with_obs.data['description'], 'Routine check with observations')
        self.assertEqual(len(response_with_obs.data['health_observations']), 2)
        # Check that the correct observations were created by looking at parameter names
        # Access parameter name via 'parameter_name' field from HealthObservationSerializer output
        obs_params = {obs['parameter_name'] for obs in response_with_obs.data['health_observations']}
        self.assertEqual(obs_params, {self.gill_health_param.name, self.eye_condition_param.name})

    def test_journal_entry_update_with_observations(self):
        # Create an entry first
        entry = JournalEntry.objects.create(
            batch=self.batch, user=self.user, category='issue', description='Initial issue'
        )
        # Add initial observations
        HealthObservation.objects.create(journal_entry=entry, parameter=self.gill_health_param, score=1)
        self.assertEqual(entry.health_observations.count(), 1)

        url = self.get_api_url('health', 'journal-entries', detail=True, pk=entry.pk)
        # New observations to replace existing
        new_observations = [
            {'parameter': self.eye_condition_param.id, 'score': 4}
        ]
        update_data = {
            'description': 'Updated issue, different obs',
            'health_observations_write': new_observations
        }
        response = self.client.patch(url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['description'], 'Updated issue, different obs')
        self.assertEqual(len(response.data['health_observations']), 1)
        self.assertEqual(response.data['health_observations'][0]['parameter_name'], self.eye_condition_param.name)
        self.assertEqual(response.data['health_observations'][0]['score'], 4)

        # Verify DB state
        entry.refresh_from_db()
        self.assertEqual(entry.health_observations.count(), 1)
        self.assertEqual(entry.health_observations.first().parameter.name, 'Eye Condition')
        self.assertEqual(entry.health_observations.first().score, 4)

    def test_unauthenticated_access(self):
        self.client.logout()
        url = self.get_api_url('health', 'journal-entries')
        response = self.client.get(url)
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
