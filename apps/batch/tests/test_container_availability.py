"""
Tests for Container Availability ViewSet.

Tests timeline-aware container selection with occupancy forecasting.
"""
from datetime import date, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from apps.infrastructure.models import Geography, Area, ContainerType, Container
from apps.batch.models import Species, LifeCycleStage, Batch, BatchContainerAssignment

User = get_user_model()


class ContainerAvailabilityTestCase(TestCase):
    """Test cases for container availability forecasting."""
    
    def setUp(self):
        """Set up test data."""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # Create geography and area
        self.geography = Geography.objects.create(
            name='Test Faroe Islands',
            description='Test geography'
        )
        self.area = Area.objects.create(
            name='Test Station',
            geography=self.geography,
            latitude=62.0,
            longitude=-6.7,
            max_biomass=500000.0
        )
        
        # Create container type
        self.container_type = ContainerType.objects.create(
            name='TRAY',
            category='TRAY',
            max_volume_m3=5.0,
            description='Incubation Tray'
        )
        
        # Create species and lifecycle stage
        self.species = Species.objects.create(
            name='Atlantic Salmon',
            scientific_name='Salmo salar'
        )
        self.egg_stage = LifeCycleStage.objects.create(
            name='Egg&Alevin',
            species=self.species,
            order=1,
            typical_duration_days=90
        )
        
        # Create test containers
        self.empty_container = Container.objects.create(
            name='TRAY-01-EMPTY',
            container_type=self.container_type,
            area=self.area,
            volume_m3=2.5,
            max_biomass_kg=50.0,
            active=True
        )
        
        self.occupied_container_available = Container.objects.create(
            name='TRAY-02-AVAILABLE',
            container_type=self.container_type,
            area=self.area,
            volume_m3=2.5,
            max_biomass_kg=50.0,
            active=True
        )
        
        self.occupied_container_conflict = Container.objects.create(
            name='TRAY-03-CONFLICT',
            container_type=self.container_type,
            area=self.area,
            volume_m3=2.5,
            max_biomass_kg=50.0,
            active=True
        )
        
        # Create batch
        self.batch = Batch.objects.create(
            batch_number='TEST-2024-001',
            species=self.species,
            lifecycle_stage=self.egg_stage,
            status='ACTIVE',
            start_date=date(2025, 9, 1)
        )
        
        # Create assignments with different expected departure dates
        # Assignment that will be empty well before delivery date
        self.assignment_available = BatchContainerAssignment.objects.create(
            batch=self.batch,
            container=self.occupied_container_available,
            lifecycle_stage=self.egg_stage,
            population_count=100000,
            biomass_kg=5.0,
            assignment_date=date(2025, 9, 1),  # Expected departure: 2025-11-30 (90 days)
            is_active=True
        )
        
        # Assignment that will still be occupied on delivery date
        self.assignment_conflict = BatchContainerAssignment.objects.create(
            batch=self.batch,
            container=self.occupied_container_conflict,
            lifecycle_stage=self.egg_stage,
            population_count=120000,
            biomass_kg=6.0,
            assignment_date=date(2025, 12, 1),  # Expected departure: 2026-03-01 (90 days)
            is_active=True
        )
    
    def test_requires_geography_parameter(self):
        """Test that geography parameter is required."""
        response = self.client.get('/api/v1/batch/containers/availability/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('geography parameter is required', response.data['error'])
    
    def test_invalid_date_format(self):
        """Test that invalid date format returns error."""
        response = self.client.get(
            '/api/v1/batch/containers/availability/',
            {'geography': self.geography.id, 'delivery_date': 'invalid-date'}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Invalid date format', response.data['error'])
    
    def test_empty_container_status(self):
        """Test that empty containers are correctly identified."""
        delivery_date = date(2026, 1, 31)
        response = self.client.get(
            '/api/v1/batch/containers/availability/',
            {
                'geography': self.geography.id,
                'delivery_date': delivery_date.isoformat()
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)
        
        # Find empty container in results
        empty_result = next(
            (r for r in response.data['results'] if r['id'] == self.empty_container.id),
            None
        )
        self.assertIsNotNone(empty_result)
        self.assertEqual(empty_result['current_status'], 'EMPTY')
        self.assertEqual(empty_result['availability_status'], 'EMPTY')
        self.assertIsNone(empty_result['days_until_available'])
        self.assertEqual(empty_result['availability_message'], 'Empty and ready')
        self.assertEqual(len(empty_result['current_assignments']), 0)
    
    def test_occupied_container_available_status(self):
        """Test that occupied containers with future availability are correctly identified."""
        delivery_date = date(2026, 1, 31)  # After expected departure (2025-11-30)
        response = self.client.get(
            '/api/v1/batch/containers/availability/',
            {
                'geography': self.geography.id,
                'delivery_date': delivery_date.isoformat()
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Find available container in results
        available_result = next(
            (r for r in response.data['results'] if r['id'] == self.occupied_container_available.id),
            None
        )
        self.assertIsNotNone(available_result)
        self.assertEqual(available_result['current_status'], 'OCCUPIED')
        self.assertEqual(available_result['availability_status'], 'AVAILABLE')
        self.assertIsNotNone(available_result['days_until_available'])
        self.assertGreater(available_result['days_until_available'], 0)
        self.assertIn('Available from', available_result['availability_message'])
        self.assertEqual(len(available_result['current_assignments']), 1)
        
        # Check assignment data
        assignment_data = available_result['current_assignments'][0]
        self.assertEqual(assignment_data['batch_id'], self.batch.id)
        self.assertEqual(assignment_data['batch_number'], self.batch.batch_number)
        self.assertEqual(assignment_data['population_count'], 100000)
        self.assertEqual(assignment_data['lifecycle_stage'], 'Egg&Alevin')
        self.assertEqual(assignment_data['assignment_date'], '2025-09-01')
        self.assertEqual(assignment_data['expected_departure_date'], '2025-11-30')
    
    def test_occupied_container_conflict_status(self):
        """Test that occupied containers with conflicts are correctly identified."""
        delivery_date = date(2026, 1, 31)  # Before expected departure (2026-03-01)
        response = self.client.get(
            '/api/v1/batch/containers/availability/',
            {
                'geography': self.geography.id,
                'delivery_date': delivery_date.isoformat()
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Find conflict container in results
        conflict_result = next(
            (r for r in response.data['results'] if r['id'] == self.occupied_container_conflict.id),
            None
        )
        self.assertIsNotNone(conflict_result)
        self.assertEqual(conflict_result['current_status'], 'OCCUPIED')
        self.assertEqual(conflict_result['availability_status'], 'CONFLICT')
        self.assertIsNotNone(conflict_result['days_until_available'])
        self.assertLess(conflict_result['days_until_available'], 0)  # Negative = conflict
        self.assertIn('⚠️ Conflict', conflict_result['availability_message'])
        self.assertIn('Occupied until', conflict_result['availability_message'])
    
    def test_sorting_by_availability_priority(self):
        """Test that containers are sorted by availability priority."""
        delivery_date = date(2026, 1, 31)
        response = self.client.get(
            '/api/v1/batch/containers/availability/',
            {
                'geography': self.geography.id,
                'delivery_date': delivery_date.isoformat()
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        results = response.data['results']
        statuses = [r['availability_status'] for r in results]
        
        # Priority order: EMPTY > AVAILABLE > CONFLICT
        # Empty should come first
        first_status = statuses[0]
        self.assertIn(first_status, ['EMPTY', 'AVAILABLE'])
        
        # Conflict should come last
        last_status = statuses[-1]
        self.assertEqual(last_status, 'CONFLICT')
    
    def test_capacity_calculation(self):
        """Test that available capacity is correctly calculated."""
        delivery_date = date(2026, 1, 31)
        response = self.client.get(
            '/api/v1/batch/containers/availability/',
            {
                'geography': self.geography.id,
                'delivery_date': delivery_date.isoformat()
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check empty container capacity
        empty_result = next(
            (r for r in response.data['results'] if r['id'] == self.empty_container.id),
            None
        )
        self.assertEqual(empty_result['available_capacity_kg'], 50.0)
        self.assertEqual(empty_result['available_capacity_percent'], 100.0)
        
        # Check occupied container capacity
        occupied_result = next(
            (r for r in response.data['results'] if r['id'] == self.occupied_container_available.id),
            None
        )
        # Max 50kg - 5kg used = 45kg available
        self.assertAlmostEqual(occupied_result['available_capacity_kg'], 45.0, places=2)
        self.assertAlmostEqual(occupied_result['available_capacity_percent'], 90.0, places=1)
    
    def test_container_type_filter(self):
        """Test filtering by container type."""
        # Create a different container type
        tank_type = ContainerType.objects.create(
            name='TANK',
            category='TANK',
            max_volume_m3=20.0,
            description='Fry Tank'
        )
        tank_container = Container.objects.create(
            name='TANK-01',
            container_type=tank_type,
            area=self.area,
            volume_m3=10.0,
            max_biomass_kg=200.0,
            active=True
        )
        
        delivery_date = date(2026, 1, 31)
        response = self.client.get(
            '/api/v1/batch/containers/availability/',
            {
                'geography': self.geography.id,
                'delivery_date': delivery_date.isoformat(),
                'container_type': 'TRAY'
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should only return TRAY containers
        for result in response.data['results']:
            self.assertEqual(result['container_type'], 'TRAY')
    
    def test_multiple_assignments_in_one_container(self):
        """Test handling of multiple active assignments in one container."""
        # Create second batch and assignment in same container
        batch2 = Batch.objects.create(
            batch_number='TEST-2024-002',
            species=self.species,
            lifecycle_stage=self.egg_stage,
            status='ACTIVE',
            start_date=date(2026, 1, 1)
        )
        
        # Add second assignment to conflict container (later expected departure)
        assignment2 = BatchContainerAssignment.objects.create(
            batch=batch2,
            container=self.occupied_container_conflict,
            lifecycle_stage=self.egg_stage,
            population_count=80000,
            biomass_kg=4.0,
            assignment_date=date(2026, 1, 1),  # Expected departure: 2026-04-01 (90 days)
            is_active=True
        )
        
        delivery_date = date(2026, 2, 15)
        response = self.client.get(
            '/api/v1/batch/containers/availability/',
            {
                'geography': self.geography.id,
                'delivery_date': delivery_date.isoformat()
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Find conflict container
        conflict_result = next(
            (r for r in response.data['results'] if r['id'] == self.occupied_container_conflict.id),
            None
        )
        self.assertIsNotNone(conflict_result)
        
        # Should have 2 assignments
        self.assertEqual(len(conflict_result['current_assignments']), 2)
        
        # Should use latest expected departure date (2026-04-01) for availability calc
        self.assertEqual(conflict_result['availability_status'], 'CONFLICT')
    
    def test_same_day_delivery(self):
        """Test edge case where delivery date equals expected departure."""
        # Create container with assignment ending exactly on delivery date
        same_day_container = Container.objects.create(
            name='TRAY-04-SAMEDAY',
            container_type=self.container_type,
            area=self.area,
            volume_m3=2.5,
            max_biomass_kg=50.0,
            active=True
        )
        
        delivery_date = date(2026, 1, 31)
        # Assignment date such that expected departure is exactly delivery_date
        assignment_date = delivery_date - timedelta(days=90)  # 2025-11-02
        
        BatchContainerAssignment.objects.create(
            batch=self.batch,
            container=same_day_container,
            lifecycle_stage=self.egg_stage,
            population_count=100000,
            biomass_kg=5.0,
            assignment_date=assignment_date,
            is_active=True
        )
        
        response = self.client.get(
            '/api/v1/batch/containers/availability/',
            {
                'geography': self.geography.id,
                'delivery_date': delivery_date.isoformat()
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        same_day_result = next(
            (r for r in response.data['results'] if r['id'] == same_day_container.id),
            None
        )
        self.assertIsNotNone(same_day_result)
        self.assertEqual(same_day_result['availability_status'], 'OCCUPIED_BUT_OK')
        self.assertEqual(same_day_result['days_until_available'], 0)
        self.assertIn('no buffer - risky', same_day_result['availability_message'])
    
    def test_actual_departure_date_overrides_expected(self):
        """Test that actual departure_date takes precedence over calculated expected."""
        # Create assignment with actual departure date set
        departed_container = Container.objects.create(
            name='TRAY-05-DEPARTED',
            container_type=self.container_type,
            area=self.area,
            volume_m3=2.5,
            max_biomass_kg=50.0,
            active=True
        )
        
        BatchContainerAssignment.objects.create(
            batch=self.batch,
            container=departed_container,
            lifecycle_stage=self.egg_stage,
            population_count=100000,
            biomass_kg=5.0,
            assignment_date=date(2025, 9, 1),
            departure_date=date(2026, 1, 15),  # Actual departure set
            is_active=True
        )
        
        delivery_date = date(2026, 1, 31)
        response = self.client.get(
            '/api/v1/batch/containers/availability/',
            {
                'geography': self.geography.id,
                'delivery_date': delivery_date.isoformat()
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        departed_result = next(
            (r for r in response.data['results'] if r['id'] == departed_container.id),
            None
        )
        self.assertIsNotNone(departed_result)
        # Should use actual departure date (2026-01-15) not calculated (2025-11-30)
        assignment_data = departed_result['current_assignments'][0]
        self.assertEqual(assignment_data['expected_departure_date'], '2026-01-15')
        self.assertEqual(departed_result['availability_status'], 'AVAILABLE')

