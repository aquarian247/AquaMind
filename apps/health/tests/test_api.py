from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model

from apps.batch.models import Batch, Species, LifeCycleStage
from apps.infrastructure.models import Container, ContainerType, Hall, FreshwaterStation, Geography
from apps.health.models import (
    JournalEntry, MortalityReason, MortalityRecord, LiceCount,
    VaccinationType, Treatment, SampleType,
    HealthParameter, HealthObservation
)

User = get_user_model()


def get_api_url(app_name, endpoint, detail=False, **kwargs):
    """Helper function to construct URLs for API endpoints"""
    if detail:
        pk = kwargs.get('pk')
        return f'/api/v1/{app_name}/{endpoint}/{pk}/'
    return f'/api/v1/{app_name}/{endpoint}/'


class HealthAPITestCase(APITestCase):
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

    def test_journal_entry_list(self):
        url = get_api_url('health', 'journal-entries')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Handle paginated response
        results = response.data.get('results', response.data)
        # Check if the specific entry exists and has expected nested data (if applicable)
        entry_found = False
        for item in results:
            if item.get('description') == 'Fish appear healthy.':
                entry_found = True
                # Add checks for nested health_observations if the setup created some
                # self.assertTrue('health_observations' in item)
                break
        self.assertTrue(entry_found)

    def test_journal_entry_create(self):
        url = get_api_url('health', 'journal-entries')
        # --- Test creating WITHOUT observations ---+
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

        # --- Test creating WITH observations ---+
        observations_input = [
            {'parameter_id': self.gill_health_param.id, 'score': 3},
            {'parameter_id': self.eye_condition_param.id, 'score': 2}
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
        # Check nested data (structure might vary based on serializer depth)
        obs_params = {obs['parameter']['name'] for obs in response_with_obs.data['health_observations']}
        obs_scores = {obs['parameter']['name']: obs['score'] for obs in response_with_obs.data['health_observations']}
        self.assertIn('Gill Health', obs_params)
        self.assertIn('Eye Condition', obs_params)
        self.assertEqual(obs_scores['Gill Health'], 3)
        self.assertEqual(obs_scores['Eye Condition'], 2)

        # Verify objects were created in DB
        entry_id = response_with_obs.data['id']
        self.assertEqual(JournalEntry.objects.get(id=entry_id).health_observations.count(), 2)

    def test_journal_entry_update_with_observations(self):
        # Create an entry first
        entry = JournalEntry.objects.create(
            batch=self.batch, user=self.user, category='issue', description='Initial issue'
        )
        # Add initial observations
        HealthObservation.objects.create(journal_entry=entry, parameter=self.gill_health_param, score=1)
        self.assertEqual(entry.health_observations.count(), 1)

        url = get_api_url('health', 'journal-entries', detail=True, pk=entry.pk)
        # New observations to replace existing
        new_observations = [
            {'parameter_id': self.eye_condition_param.id, 'score': 4}
        ]
        update_data = {
            'description': 'Updated issue, different obs',
            'health_observations_write': new_observations
        }
        response = self.client.patch(url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['description'], 'Updated issue, different obs')
        self.assertEqual(len(response.data['health_observations']), 1)
        self.assertEqual(response.data['health_observations'][0]['parameter']['name'], 'Eye Condition')
        self.assertEqual(response.data['health_observations'][0]['score'], 4)

        # Verify DB state
        entry.refresh_from_db()
        self.assertEqual(entry.health_observations.count(), 1)
        self.assertEqual(entry.health_observations.first().parameter.name, 'Eye Condition')
        self.assertEqual(entry.health_observations.first().score, 4)

    def test_journal_entry_detail_view(self):
        entry = JournalEntry.objects.create(
            batch=self.batch, user=self.user, category='observation', description='Detail check'
        )
        HealthObservation.objects.create(journal_entry=entry, parameter=self.gill_health_param, score=2)

        url = get_api_url('health', 'journal-entries', detail=True, pk=entry.pk)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('health_observations', response.data)
        self.assertEqual(len(response.data['health_observations']), 1)
        self.assertEqual(response.data['health_observations'][0]['parameter']['name'], 'Gill Health')
        self.assertEqual(response.data['health_observations'][0]['score'], 2)

    def test_health_parameter_api(self):
        list_url = get_api_url('health', 'health-parameters')

        # List
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data)
        self.assertEqual(len(results), 2) # Gill Health, Eye Condition from setup

        # Create
        create_data = {
            'name': 'Fin Condition',
            'description_score_1': 'Perfect fins',
            'description_score_2': 'Slight fraying',
            'description_score_3': 'Noticeable damage',
            'description_score_4': 'Severe erosion'
        }
        response = self.client.post(list_url, create_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Fin Condition')
        param_id = response.data['id']

        # Retrieve
        detail_url = get_api_url('health', 'health-parameters', detail=True, pk=param_id)
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Fin Condition')

        # Update
        update_data = {'description_score_1': 'Perfect fins, intact'}
        response = self.client.patch(detail_url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['description_score_1'], 'Perfect fins, intact')

        # Delete
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(HealthParameter.objects.filter(id=param_id).exists())

    def test_mortality_reason_list(self):
        url = get_api_url('health', 'mortality-reasons')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Handle paginated response
        results = response.data.get('results', response.data)
        self.assertEqual(len([item for item in results if item.get('name') == 'Disease']), 1)

    def test_mortality_record_list(self):
        url = get_api_url('health', 'mortality-records')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Handle paginated response
        results = response.data.get('results', response.data)
        self.assertEqual(len([item for item in results if item.get('count') == 50]), 1)

    def test_lice_count_list(self):
        url = get_api_url('health', 'lice-counts')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Handle paginated response
        results = response.data.get('results', response.data)
        self.assertEqual(len([item for item in results if item.get('adult_female_count') == 10]), 1)

    def test_vaccination_type_list(self):
        url = get_api_url('health', 'vaccination-types')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Handle paginated response
        results = response.data.get('results', response.data)
        self.assertEqual(len([item for item in results if item.get('name') == 'Vaccine A']), 1)

    def test_treatment_list(self):
        url = get_api_url('health', 'treatments')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Handle paginated response
        results = response.data.get('results', response.data)
        self.assertEqual(len([item for item in results if item.get('description') == 'Vaccination against disease']), 1)

    def test_sample_type_list(self):
        url = get_api_url('health', 'sample-types')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Handle paginated response
        results = response.data.get('results', response.data)
        self.assertEqual(len([item for item in results if item.get('name') == 'Water Sample']), 1)

    def test_unauthenticated_access(self):
        self.client.force_authenticate(user=None)
        url = get_api_url('health', 'journal-entries')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
