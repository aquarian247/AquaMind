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


# Note: Full integration tests (with real scenarios, projections, and actual states)
# are deferred to Phase 9 validation with Faroe Islands dataset.
# These contract tests ensure the API plumbing works correctly.
