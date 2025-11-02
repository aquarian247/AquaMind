"""
RBAC enforcement tests.

Tests to verify that Role-Based Access Control is properly enforced across
the application, including geographic isolation, subsidiary filtering, and
role-based permissions.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from apps.users.models import UserProfile, Geography, Subsidiary, Role
from apps.infrastructure.models import Geography as GeographyModel, Area, Container, ContainerType
from apps.batch.models import Batch, Species, LifecycleStage, BatchContainerAssignment
from apps.health.models import JournalEntry

User = get_user_model()


class RBACGeographicIsolationTest(TestCase):
    """
    Test suite for verifying geographic data isolation.
    
    These tests ensure that users can only access data within their
    authorized geography and cannot access or modify data in other geographies.
    """
    
    def setUp(self):
        """Set up test data with Scottish and Faroese geographies."""
        # Create geographies
        self.geo_scotland = GeographyModel.objects.create(
            name='Scotland',
            description='Scotland operations'
        )
        self.geo_faroe = GeographyModel.objects.create(
            name='Faroe Islands',
            description='Faroe Islands operations'
        )
        
        # Create areas
        self.area_scotland = Area.objects.create(
            name='Scottish Area 1',
            geography=self.geo_scotland,
            latitude=56.0,
            longitude=-4.0,
            max_biomass=1000000
        )
        self.area_faroe = Area.objects.create(
            name='Faroe Area 1',
            geography=self.geo_faroe,
            latitude=62.0,
            longitude=-6.5,
            max_biomass=1000000
        )
        
        # Create container type and containers
        self.container_type = ContainerType.objects.create(
            name='Test Tank',
            category='TANK',
            max_volume_m3=100
        )
        self.container_scotland = Container.objects.create(
            name='Scottish Tank 1',
            container_type=self.container_type,
            area=self.area_scotland,
            volume_m3=100,
            max_biomass_kg=10000
        )
        self.container_faroe = Container.objects.create(
            name='Faroe Tank 1',
            container_type=self.container_type,
            area=self.area_faroe,
            volume_m3=100,
            max_biomass_kg=10000
        )
        
        # Create species and lifecycle stage
        self.species = Species.objects.create(
            name='Atlantic Salmon',
            scientific_name='Salmo salar'
        )
        self.lifecycle_stage = LifecycleStage.objects.create(
            name='Smolt',
            order=4
        )
        
        # Create batches
        self.batch_scotland = Batch.objects.create(
            batch_number='SCO-2024-001',
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            status='ACTIVE',
            batch_type='STANDARD'
        )
        self.batch_faroe = Batch.objects.create(
            batch_number='FAR-2024-001',
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            status='ACTIVE',
            batch_type='STANDARD'
        )
        
        # Create batch container assignments
        self.assignment_scotland = BatchContainerAssignment.objects.create(
            batch=self.batch_scotland,
            container=self.container_scotland,
            lifecycle_stage=self.lifecycle_stage,
            population_count=1000,
            avg_weight_g=50.0,
            biomass_kg=50.0
        )
        self.assignment_faroe = BatchContainerAssignment.objects.create(
            batch=self.batch_faroe,
            container=self.container_faroe,
            lifecycle_stage=self.lifecycle_stage,
            population_count=1000,
            avg_weight_g=50.0,
            biomass_kg=50.0
        )
        
        # Create users with different geographies
        self.scottish_operator = User.objects.create_user(
            username='scottish_operator',
            email='scottish_operator@aquamind.io',
            password='testpass123'
        )
        self.scottish_operator.profile.geography = Geography.SCOTLAND
        self.scottish_operator.profile.subsidiary = Subsidiary.FARMING
        self.scottish_operator.profile.role = Role.OPERATOR
        self.scottish_operator.profile.save()
        
        self.faroese_operator = User.objects.create_user(
            username='faroese_operator',
            email='faroese_operator@aquamind.io',
            password='testpass123'
        )
        self.faroese_operator.profile.geography = Geography.FAROE_ISLANDS
        self.faroese_operator.profile.subsidiary = Subsidiary.FARMING
        self.faroese_operator.profile.role = Role.OPERATOR
        self.faroese_operator.profile.save()
        
        # Create admin with ALL geography access
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@aquamind.io',
            password='testpass123',
            is_staff=True,
            is_superuser=True
        )
        self.admin_user.profile.geography = Geography.ALL
        self.admin_user.profile.subsidiary = Subsidiary.ALL
        self.admin_user.profile.role = Role.ADMIN
        self.admin_user.profile.save()
        
        self.client = APIClient()
    
    def test_scottish_operator_cannot_see_faroese_batches(self):
        """Test that Scottish operator cannot see Faroese batches."""
        self.client.force_authenticate(user=self.scottish_operator)
        response = self.client.get('/api/v1/batch/batches/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Extract batch IDs from response
        batch_ids = [b['id'] for b in response.data.get('results', response.data)]
        
        # Scottish operator should see Scottish batch
        self.assertIn(self.batch_scotland.id, batch_ids, 
                     "Scottish operator should see Scottish batches")
        
        # Scottish operator should NOT see Faroese batch
        self.assertNotIn(self.batch_faroe.id, batch_ids,
                        "Scottish operator should NOT see Faroese batches")
    
    def test_faroese_operator_cannot_see_scottish_batches(self):
        """Test that Faroese operator cannot see Scottish batches."""
        self.client.force_authenticate(user=self.faroese_operator)
        response = self.client.get('/api/v1/batch/batches/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Extract batch IDs from response
        batch_ids = [b['id'] for b in response.data.get('results', response.data)]
        
        # Faroese operator should see Faroese batch
        self.assertIn(self.batch_faroe.id, batch_ids,
                     "Faroese operator should see Faroese batches")
        
        # Faroese operator should NOT see Scottish batch
        self.assertNotIn(self.batch_scotland.id, batch_ids,
                        "Faroese operator should NOT see Scottish batches")
    
    def test_admin_can_see_all_batches(self):
        """Test that admin with ALL geography can see all batches."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/v1/batch/batches/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Extract batch IDs from response
        batch_ids = [b['id'] for b in response.data.get('results', response.data)]
        
        # Admin should see both batches
        self.assertIn(self.batch_scotland.id, batch_ids,
                     "Admin should see Scottish batches")
        self.assertIn(self.batch_faroe.id, batch_ids,
                     "Admin should see Faroese batches")
    
    def test_scottish_operator_cannot_access_faroese_batch_detail(self):
        """Test that Scottish operator cannot access Faroese batch by direct ID."""
        self.client.force_authenticate(user=self.scottish_operator)
        response = self.client.get(f'/api/v1/batch/batches/{self.batch_faroe.id}/')
        
        # Should get 404 (not found) due to queryset filtering
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND,
                        "Scottish operator should get 404 when accessing Faroese batch")


class RBACRoleBasedAccessTest(TestCase):
    """
    Test suite for verifying role-based access control.
    
    These tests ensure that only users with appropriate roles can access
    specific functionality (e.g., only veterinarians can access health data).
    """
    
    def setUp(self):
        """Set up test data with users of different roles."""
        # Create geography and infrastructure
        self.geography = GeographyModel.objects.create(
            name='Test Geography',
            description='Test geography for role testing'
        )
        self.area = Area.objects.create(
            name='Test Area',
            geography=self.geography,
            latitude=60.0,
            longitude=-5.0,
            max_biomass=1000000
        )
        self.container_type = ContainerType.objects.create(
            name='Test Tank',
            category='TANK',
            max_volume_m3=100
        )
        self.container = Container.objects.create(
            name='Test Tank 1',
            container_type=self.container_type,
            area=self.area,
            volume_m3=100,
            max_biomass_kg=10000
        )
        
        # Create batch for health data
        self.species = Species.objects.create(
            name='Atlantic Salmon',
            scientific_name='Salmo salar'
        )
        self.lifecycle_stage = LifecycleStage.objects.create(
            name='Smolt',
            order=4
        )
        self.batch = Batch.objects.create(
            batch_number='TEST-2024-001',
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            status='ACTIVE',
            batch_type='STANDARD'
        )
        
        # Create users with different roles
        self.operator = User.objects.create_user(
            username='operator',
            email='operator@aquamind.io',
            password='testpass123'
        )
        self.operator.profile.geography = Geography.FAROE_ISLANDS
        self.operator.profile.role = Role.OPERATOR
        self.operator.profile.save()
        
        self.veterinarian = User.objects.create_user(
            username='veterinarian',
            email='vet@aquamind.io',
            password='testpass123'
        )
        self.veterinarian.profile.geography = Geography.FAROE_ISLANDS
        self.veterinarian.profile.role = Role.VETERINARIAN
        self.veterinarian.profile.save()
        
        self.qa_user = User.objects.create_user(
            username='qa_user',
            email='qa@aquamind.io',
            password='testpass123'
        )
        self.qa_user.profile.geography = Geography.FAROE_ISLANDS
        self.qa_user.profile.role = Role.QA
        self.qa_user.profile.save()
        
        self.client = APIClient()
    
    def test_operator_cannot_access_health_data(self):
        """Test that operators cannot access health journal entries."""
        self.client.force_authenticate(user=self.operator)
        response = self.client.get('/api/v1/health/journal-entries/')
        
        # Should be denied (403 Forbidden)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN,
                        "Operator should not have access to health data")
    
    def test_veterinarian_can_access_health_data(self):
        """Test that veterinarians can access health journal entries."""
        self.client.force_authenticate(user=self.veterinarian)
        response = self.client.get('/api/v1/health/journal-entries/')
        
        # Should be allowed
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                        "Veterinarian should have access to health data")
    
    def test_qa_can_read_health_data(self):
        """Test that QA users can read health journal entries."""
        self.client.force_authenticate(user=self.qa_user)
        response = self.client.get('/api/v1/health/journal-entries/')
        
        # Should be allowed for reading
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                        "QA user should have read access to health data")
    
    def test_operator_can_access_batch_data(self):
        """Test that operators can access batch data."""
        self.client.force_authenticate(user=self.operator)
        response = self.client.get('/api/v1/batch/batches/')
        
        # Should be allowed
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                        "Operator should have access to batch data")


class RBACObjectLevelValidationTest(TestCase):
    """
    Test suite for object-level validation.
    
    These tests ensure that users cannot create or update objects outside
    their authorized geography even if they try to POST/PUT with foreign IDs.
    """
    
    def setUp(self):
        """Set up test data for object-level validation tests."""
        # Create geographies
        self.geo_scotland = GeographyModel.objects.create(
            name='Scotland',
            description='Scotland operations'
        )
        self.geo_faroe = GeographyModel.objects.create(
            name='Faroe Islands',
            description='Faroe Islands operations'
        )
        
        # Create Scottish operator
        self.scottish_operator = User.objects.create_user(
            username='scottish_operator',
            email='scottish_operator@aquamind.io',
            password='testpass123'
        )
        self.scottish_operator.profile.geography = Geography.SCOTLAND
        self.scottish_operator.profile.role = Role.OPERATOR
        self.scottish_operator.profile.save()
        
        self.client = APIClient()
    
    def test_scottish_operator_cannot_create_faroese_batch(self):
        """
        Test that Scottish operator cannot create a batch in Faroe Islands
        by guessing/using Faroese container IDs.
        
        Note: This test may need adjustment based on actual implementation
        of object-level validation in serializers.
        """
        # This is a placeholder test - actual implementation would depend on
        # how batch creation validates the geography of referenced containers
        pass


# Note: Additional tests should be added for:
# - Subsidiary filtering
# - Treatment editing (VET only, QA read-only)
# - Finance data access (Finance role only)
# - Operator location restrictions (when implemented)
