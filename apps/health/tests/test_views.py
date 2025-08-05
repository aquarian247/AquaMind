from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse
from decimal import Decimal

from apps.batch.models import (
    Species, LifeCycleStage, Batch, BatchContainerAssignment
)
from apps.infrastructure.models import (
    Container, Geography, FreshwaterStation, Hall, ContainerType
)

class LoadBatchAssignmentsViewTests(TestCase):
    """Tests for the load_batch_assignments AJAX view."""

    @classmethod
    def setUpTestData(cls):
        """Set up data for the whole TestCase."""
        # User for login
        cls.username = 'testuser'
        cls.password = 'testpass123'
        cls.user = User.objects.create_user(username=cls.username, password=cls.password)

        # Common infrastructure and batch setup
        cls.species = Species.objects.create(name='Test Species Health View')
        cls.lifecycle_stage_fry = LifeCycleStage.objects.create(species=cls.species, name='Fry Health View', order=1)
        cls.lifecycle_stage_smolt = LifeCycleStage.objects.create(species=cls.species, name='Smolt Health View', order=2)
        
        cls.geography = Geography.objects.create(name="Health View Test Geography")
        cls.station = FreshwaterStation.objects.create(
            name="Health View Test Station", 
            geography=cls.geography, 
            station_type='FRESHWATER',
            latitude=12.0,
            longitude=12.0
        )
        cls.hall = Hall.objects.create(name="Health View Test Hall", freshwater_station=cls.station)
        cls.container_type = ContainerType.objects.create(
            name="Health View Test Tank Type", category='TANK', max_volume_m3=Decimal('200.0')
        )
        
        cls.container1 = Container.objects.create(
            name="HV Container 1", hall=cls.hall, container_type=cls.container_type,
            volume_m3=Decimal('180.0'), max_biomass_kg=Decimal('800.0')
        )
        cls.container2 = Container.objects.create(
            name="HV Container 2", hall=cls.hall, container_type=cls.container_type,
            volume_m3=Decimal('180.0'), max_biomass_kg=Decimal('800.0')
        )

        cls.batch1 = Batch.objects.create(
            batch_number='HVB001', species=cls.species, lifecycle_stage=cls.lifecycle_stage_fry,
            status='ACTIVE', start_date=date(2023, 1, 1),
        )
        cls.batch2 = Batch.objects.create(
            batch_number='HVB002', species=cls.species, lifecycle_stage=cls.lifecycle_stage_smolt,
            status='ACTIVE', start_date=date(2023, 3, 1),
        )

        # BatchContainerAssignments
        # Active assignment, no departure date (active indefinitely from assignment_date)
        cls.assignment1 = BatchContainerAssignment.objects.create(
            batch=cls.batch1, container=cls.container1, lifecycle_stage=cls.lifecycle_stage_fry,
            population_count=2000, avg_weight_g=Decimal('10.0'), biomass_kg=Decimal('20.0'),
            assignment_date=date(2023, 1, 10), is_active=True
        )

        # Assignment with a specific active range
        cls.assignment2 = BatchContainerAssignment.objects.create(
            batch=cls.batch1, container=cls.container2, lifecycle_stage=cls.lifecycle_stage_fry,
            population_count=1500, avg_weight_g=Decimal('15.0'), biomass_kg=Decimal('22.5'),
            assignment_date=date(2023, 2, 1), departure_date=date(2023, 2, 28), is_active=True 
            # Note: is_active might be set to False by other logic if departure_date is in past, but for testing filter, we set it True
        )
        
        # Assignment that is not yet active for a future sample date
        cls.assignment3 = BatchContainerAssignment.objects.create(
            batch=cls.batch2, container=cls.container1, lifecycle_stage=cls.lifecycle_stage_smolt,
            population_count=1000, avg_weight_g=Decimal('50.0'), biomass_kg=Decimal('50.0'),
            assignment_date=date(2023, 3, 15), is_active=True
        )

        # Inactive assignment (is_active=False)
        cls.assignment4_inactive = BatchContainerAssignment.objects.create(
            batch=cls.batch2, container=cls.container2, lifecycle_stage=cls.lifecycle_stage_smolt,
            population_count=500, avg_weight_g=Decimal('55.0'), biomass_kg=Decimal('27.5'),
            assignment_date=date(2023, 1, 1), departure_date=date(2023, 1, 31), is_active=False
        )

        cls.client = Client()
        cls.url = reverse('ajax_load_batch_assignments')

    def setUp(self):
        """Login the user for each test."""
        self.client.login(username=self.username, password=self.password)

    def test_load_assignments_authenticated_no_date(self):
        """Test view returns empty list if no date is provided."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['assignments'], [])

    def test_load_assignments_authenticated_invalid_date_format(self):
        """Test view returns empty list for invalid date format."""
        response = self.client.get(self.url, {'sample_date': 'invalid-date'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['assignments'], [])

    def test_load_assignments_unauthenticated(self):
        """Test view redirects to login if user is not authenticated."""
        self.client.logout()
        response = self.client.get(self.url, {'sample_date': '2023-01-15'})
        # AJAX views often return 403 or empty for unauthenticated if not redirecting to login page
        # Or, if it's part of admin, it might redirect. Check actual behavior or expected.
        # Assuming it might be protected by login_required or similar, which redirects.
        # If it's an API endpoint, it should be 401/403.
        # Given it's used in admin forms, redirect to login is common.
        # For now, let's assume it's protected by @login_required or similar decorator on the view itself or URL inclusion
        # If the view is not decorated, this test might fail. We'll adjust if needed.
        self.assertEqual(response.status_code, 302) # Expect a redirect to login
        # Check if the redirect URL contains the standard login path
        # This is more robust than hardcoding reverse('login') or settings.LOGIN_URL
        self.assertIn('/accounts/login/', response.url)

    def test_load_assignments_active_on_sample_date(self):
        """Test assignments active on the sample_date are returned."""
        sample_date_str = '2023-01-15'
        response = self.client.get(self.url, {'sample_date': sample_date_str})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        returned_ids = {item['id'] for item in data['assignments']}
        
        # assignment1 (assigned 2023-01-10, no departure) should be active
        self.assertIn(self.assignment1.pk, returned_ids)
        # assignment2 (2023-02-01 to 2023-02-28) should NOT be active
        self.assertNotIn(self.assignment2.pk, returned_ids)
        # assignment3 (assigned 2023-03-15) should NOT be active
        self.assertNotIn(self.assignment3.pk, returned_ids)
        # assignment4_inactive (is_active=False) should NOT be returned
        self.assertNotIn(self.assignment4_inactive.pk, returned_ids)
        self.assertEqual(len(returned_ids), 1)

    def test_load_assignments_within_specific_range(self):
        """Test assignments active within a specific date range."""
        sample_date_str = '2023-02-15'
        response = self.client.get(self.url, {'sample_date': sample_date_str})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        returned_ids = {item['id'] for item in data['assignments']}

        # assignment1 (assigned 2023-01-10, no departure) should be active
        self.assertIn(self.assignment1.pk, returned_ids)
        # assignment2 (2023-02-01 to 2023-02-28) should be active
        self.assertIn(self.assignment2.pk, returned_ids)
        # assignment3 (assigned 2023-03-15) should NOT be active
        self.assertNotIn(self.assignment3.pk, returned_ids)
        self.assertEqual(len(returned_ids), 2)

    def test_load_assignments_no_active_assignments_for_date(self):
        """Test returns empty list if no assignments are active on sample_date."""
        sample_date_str = '2022-12-31' # Before any assignments
        response = self.client.get(self.url, {'sample_date': sample_date_str})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['assignments'], [])

        sample_date_str_far_future = '2099-12-31' # After all specific departures (only assignment1 and assignment3 could be active)
        response_future = self.client.get(self.url, {'sample_date': sample_date_str_far_future})
        self.assertEqual(response_future.status_code, 200)
        data_future = response_future.json()
        returned_ids_future = {item['id'] for item in data_future['assignments']}
        self.assertIn(self.assignment1.pk, returned_ids_future) # Active indefinitely
        self.assertIn(self.assignment3.pk, returned_ids_future) # Active indefinitely from its assignment date
        self.assertNotIn(self.assignment2.pk, returned_ids_future) # Has departure date
        self.assertEqual(len(returned_ids_future), 2)

    def test_load_assignments_includes_correct_text_representation(self):
        """Test that the 'text' field is the string representation of the assignment."""
        sample_date_str = '2023-01-15'
        response = self.client.get(self.url, {'sample_date': sample_date_str})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['assignments']), 1)
        returned_assignment_data = data['assignments'][0]
        self.assertEqual(returned_assignment_data['id'], self.assignment1.pk)
        self.assertEqual(returned_assignment_data['text'], str(self.assignment1))

    def test_load_assignments_edge_case_sample_date_equals_assignment_date(self):
        """Test when sample_date is exactly assignment_date."""
        sample_date_str = self.assignment1.assignment_date.strftime('%Y-%m-%d') # 2023-01-10
        response = self.client.get(self.url, {'sample_date': sample_date_str})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        returned_ids = {item['id'] for item in data['assignments']}
        self.assertIn(self.assignment1.pk, returned_ids)

    def test_load_assignments_edge_case_sample_date_equals_departure_date(self):
        """Test when sample_date is exactly departure_date."""
        sample_date_str = self.assignment2.departure_date.strftime('%Y-%m-%d') # 2023-02-28
        response = self.client.get(self.url, {'sample_date': sample_date_str})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        returned_ids = {item['id'] for item in data['assignments']}
        self.assertIn(self.assignment2.pk, returned_ids)
        # assignment1 should also be active here as it has no departure date
        self.assertIn(self.assignment1.pk, returned_ids) 

    # Add more tests as needed, e.g., for assignments that become inactive due to population count = 0 if that logic is in the filter
    # The current filter in views.py only checks is_active=True, assignment_date, and departure_date.
