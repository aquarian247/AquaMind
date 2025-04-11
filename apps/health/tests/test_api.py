from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model

from apps.batch.models import Batch, Species, LifeCycleStage
from apps.infrastructure.models import Container, ContainerType, Hall, FreshwaterStation, Geography
from apps.health.models import (
    JournalEntry, MortalityReason, MortalityRecord, LiceCount,
    VaccinationType, Treatment, SampleType
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
        self.assertEqual(len([item for item in results if item.get('description') == 'Fish appear healthy.']), 1)

    def test_journal_entry_create(self):
        url = get_api_url('health', 'journal-entries')
        data = {
            'batch': self.batch.id,
            'container': self.container.id,
            'category': 'issue',
            'severity': 'medium',
            'description': 'Some fish showing signs of stress'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['category'], 'issue')

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
