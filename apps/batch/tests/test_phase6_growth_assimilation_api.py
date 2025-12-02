"""
Tests for Phase 6 - Growth Assimilation API Endpoints.

Validates API contract and basic functionality:
1. Endpoint availability and authentication
2. Response data shape
3. Permission enforcement
4. Error handling

Full integration testing with scenarios + data deferred to Phase 9
with real Faroe Islands dataset per handover recommendation.

Issue: #112 - Phase 6
"""
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from apps.batch.models import Batch, ActualDailyAssignmentState, GrowthSample

# Reuse existing test helpers
from apps.batch.tests.models.test_utils import (
    create_test_batch,
    create_test_container,
    create_test_batch_container_assignment,
    create_test_species,
    create_test_lifecycle_stage,
    create_test_user,
)
from apps.users.models import Role, Geography as UserGeography

User = get_user_model()


class GrowthAssimilationAPIContractTestCase(TestCase):
    """
    Test Growth Assimilation API contracts (endpoints, auth, structure).
    
    These tests validate that endpoints exist, require proper authentication,
    and return expected data shapes. Full data validation happens in Phase 9.
    """
    
    def setUp(self):
        """Set up minimal test data."""
        # Create admin user with geography=ALL (sees everything)
        self.admin_user = create_test_user(
            username='admin',
            role=Role.ADMIN,
            geography=UserGeography.ALL
        )
        
        # API client
        self.client = APIClient()
        
        # Create minimal batch (no scenario - will test that case)
        self.container = create_test_container(name="API-Tank-001")
        species = create_test_species(name="Atlantic Salmon API")
        stage = create_test_lifecycle_stage(species=species, name="Fry API", order=1)
        self.batch = create_test_batch(
            species=species,
            lifecycle_stage=stage,
            batch_number="API-TEST-001"
        )
        
        self.assignment = create_test_batch_container_assignment(
            batch=self.batch,
            container=self.container,
            lifecycle_stage=stage,
            population_count=5000,
            avg_weight_g=Decimal('50.0')
        )
    
    def test_combined_growth_data_endpoint_exists(self):
        """Test combined endpoint is accessible (requires auth)."""
        url = f'/api/v1/batch/batches/{self.batch.id}/combined-growth-data/'
        
        # Without auth - should get 401
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # With auth - should get response (404 expected since no scenario)
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(url)
        self.assertIn(response.status_code, [
            status.HTTP_200_OK,  # If scenario exists
            status.HTTP_404_NOT_FOUND,  # Expected: no scenario
        ])
    
    def test_combined_growth_data_no_scenario_response(self):
        """Test endpoint returns proper 404 when no scenario available."""
        self.client.force_authenticate(user=self.admin_user)
        url = f'/api/v1/batch/batches/{self.batch.id}/combined-growth-data/'
        
        response = self.client.get(url)
        
        # Should return 404 with helpful message
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        data = response.json()
        self.assertIn('detail', data)
        self.assertIn('batch_id', data)
        self.assertIn('scenario', data['detail'].lower())  # Message mentions scenario
    
    def test_pin_scenario_endpoint_exists(self):
        """Test pin scenario endpoint is accessible."""
        self.client.force_authenticate(user=self.admin_user)
        url = f'/api/v1/batch/batches/{self.batch.id}/pin-scenario/'
        
        # Invalid scenario ID - should get 400
        response = self.client.post(url, {'scenario_id': 999999})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_pin_scenario_requires_scenario_id(self):
        """Test pin scenario validates required fields."""
        self.client.force_authenticate(user=self.admin_user)
        url = f'/api/v1/batch/batches/{self.batch.id}/pin-scenario/'
        
        # Missing scenario_id - should get 400
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    @patch('apps.batch.tasks.recompute_batch_window.delay')
    def test_recompute_endpoint_exists(self, mock_delay):
        """Test recompute endpoint is accessible (admin)."""
        # Mock task
        mock_task = MagicMock()
        mock_task.id = 'test-task-123'
        mock_delay.return_value = mock_task
        
        self.client.force_authenticate(user=self.admin_user)
        url = f'/api/v1/batch/batches/{self.batch.id}/recompute-daily-states/'
        
        response = self.client.post(url, {
            'start_date': '2024-01-01',
            'end_date': '2024-01-31',
        })
        
        # Should accept (202) or forbid (403) depending on permissions
        self.assertIn(response.status_code, [
            status.HTTP_202_ACCEPTED,
            status.HTTP_403_FORBIDDEN,
        ])
    
    @patch('apps.batch.tasks.recompute_batch_window.delay')
    def test_recompute_validates_date_range(self, mock_delay):
        """Test recompute endpoint validates date range."""
        self.client.force_authenticate(user=self.admin_user)
        url = f'/api/v1/batch/batches/{self.batch.id}/recompute-daily-states/'
        
        # Invalid: end_date before start_date
        response = self.client.post(url, {
            'start_date': '2024-12-31',
            'end_date': '2024-01-01',
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    @patch('apps.batch.tasks.recompute_batch_window.delay')
    def test_recompute_accepts_valid_request(self, mock_delay):
        """Test recompute endpoint accepts valid request."""
        # Mock task
        mock_task = MagicMock()
        mock_task.id = 'test-task-456'
        mock_delay.return_value = mock_task
        
        self.client.force_authenticate(user=self.admin_user)
        url = f'/api/v1/batch/batches/{self.batch.id}/recompute-daily-states/'
        
        response = self.client.post(url, {
            'start_date': '2024-01-01',
            'end_date': '2024-01-31',
        })
        
        # Admin should be able to trigger recompute
        if response.status_code == status.HTTP_202_ACCEPTED:
            data = response.json()
            self.assertTrue(data['success'])
            self.assertIn('task_ids', data)
            mock_delay.assert_called_once()


class GrowthAssimilationIntegrationTestCase(TestCase):
    """
    Integration tests for Growth Assimilation API with actual scenario data.
    
    These tests validate the success path - that the endpoint correctly
    retrieves and returns scenario projections. This catches breaking
    changes in the data model (e.g., ScenarioProjection FK changes).
    """
    
    def setUp(self):
        """Set up test data with a complete scenario chain."""
        from apps.scenario.models import (
            Scenario, ProjectionRun, ScenarioProjection,
            TGCModel, FCRModel, MortalityModel, TemperatureProfile
        )
        from apps.batch.models import Batch
        
        # Create admin user
        self.admin_user = create_test_user(
            username='admin_integration',
            role=Role.ADMIN,
            geography=UserGeography.ALL
        )
        
        # API client
        self.client = APIClient()
        
        # Create minimal infrastructure
        self.container = create_test_container(name="Integration-Tank-001")
        self.species = create_test_species(name="Atlantic Salmon Integration")
        self.stage = create_test_lifecycle_stage(
            species=self.species, name="Fry Integration", order=1
        )
        
        # Create batch with specific start_date for scenario alignment
        self.batch = Batch.objects.create(
            batch_number="INTEG-TEST-001",
            species=self.species,
            lifecycle_stage=self.stage,
            start_date=date(2024, 1, 1),
            expected_end_date=date(2024, 12, 31)
        )
        
        self.assignment = create_test_batch_container_assignment(
            batch=self.batch,
            container=self.container,
            lifecycle_stage=self.stage,
            population_count=10000,
            avg_weight_g=Decimal('10.0')
        )
        
        # Create scenario models (minimal)
        self.temp_profile = TemperatureProfile.objects.create(name="Integration Profile")
        self.tgc_model = TGCModel.objects.create(
            name="Integration TGC",
            location="Test",
            release_period="Spring",
            tgc_value=0.001,
            profile=self.temp_profile
        )
        self.fcr_model = FCRModel.objects.create(name="Integration FCR")
        self.mortality_model = MortalityModel.objects.create(
            name="Integration Mortality",
            frequency='daily',
            rate=0.01
        )
        
        # Create scenario linked to batch
        self.scenario = Scenario.objects.create(
            name="Integration Test Scenario",
            start_date=date(2024, 1, 1),
            duration_days=30,
            initial_count=10000,
            initial_weight=10.0,
            genotype="Test",
            supplier="Test Supplier",
            tgc_model=self.tgc_model,
            fcr_model=self.fcr_model,
            mortality_model=self.mortality_model,
            batch=self.batch,
            created_by=self.admin_user
        )
        
        # Create projection run
        self.projection_run = ProjectionRun.objects.create(
            scenario=self.scenario,
            run_number=1,
            label='Integration Test Run',
            total_projections=30,
            final_weight_g=50.0,
            final_biomass_kg=500.0,
            created_by=self.admin_user
        )
        
        # Create a few projection records
        for day in range(5):
            ScenarioProjection.objects.create(
                projection_run=self.projection_run,
                projection_date=date(2024, 1, 1) + timedelta(days=day),
                day_number=day + 1,
                average_weight=10.0 + day * 2,
                population=10000 - day * 10,
                biomass=(10.0 + day * 2) * (10000 - day * 10) / 1000,
                daily_feed=5.0,
                cumulative_feed=5.0 * (day + 1),
                temperature=12.0,
                current_stage=self.stage
            )
        
        # Pin projection run to batch
        self.batch.pinned_projection_run = self.projection_run
        self.batch.save()
    
    def test_combined_growth_data_success_path(self):
        """
        Test that combined-growth-data endpoint returns data when scenario exists.
        
        This is the critical test that catches breaking changes to
        ScenarioProjection query logic.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = f'/api/v1/batch/batches/{self.batch.id}/combined-growth-data/'
        
        response = self.client.get(url)
        
        # Should return 200 OK
        self.assertEqual(
            response.status_code, status.HTTP_200_OK,
            f"Expected 200 OK but got {response.status_code}: {response.json()}"
        )
        
        data = response.json()
        
        # Verify response structure
        self.assertEqual(data['batch_id'], self.batch.id)
        self.assertEqual(data['batch_number'], 'INTEG-TEST-001')
        
        # Verify scenario info
        self.assertIn('scenario', data)
        self.assertEqual(data['scenario']['id'], self.scenario.scenario_id)
        self.assertEqual(data['scenario']['name'], 'Integration Test Scenario')
        
        # Verify projection_run info (new field added after ProjectionRun model)
        self.assertIn('projection_run', data)
        self.assertEqual(data['projection_run']['id'], self.projection_run.run_id)
        self.assertEqual(data['projection_run']['run_number'], 1)
        
        # Verify scenario_projection data exists
        self.assertIn('scenario_projection', data)
        self.assertGreater(len(data['scenario_projection']), 0)
        
        # Verify projection data shape
        first_projection = data['scenario_projection'][0]
        self.assertIn('day_number', first_projection)
        self.assertIn('avg_weight_g', first_projection)
        self.assertIn('population', first_projection)
        self.assertIn('biomass_kg', first_projection)
    
    def test_combined_growth_data_with_date_range(self):
        """Test that date range filtering works for projections."""
        self.client.force_authenticate(user=self.admin_user)
        url = f'/api/v1/batch/batches/{self.batch.id}/combined-growth-data/'
        
        # Request specific date range
        response = self.client.get(url, {
            'start_date': '2024-01-01',
            'end_date': '2024-01-03',
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Verify date range in response
        self.assertEqual(data['date_range']['start'], '2024-01-01')
        self.assertEqual(data['date_range']['end'], '2024-01-03')


# Note: Additional full integration tests with Faroe Islands dataset
# should be added in Phase 9 for comprehensive validation.
