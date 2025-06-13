"""
Basic API tests for the Broodstock Management app.

This module contains tests to verify that API endpoints are properly configured
and accessible.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()


class BroodstockAPITestCase(TestCase):
    """Test case for broodstock API endpoints."""
    
    def setUp(self):
        """Set up test client and authentication."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
    
    def test_maintenance_tasks_endpoint(self):
        """Test that maintenance tasks endpoint is accessible."""
        response = self.client.get('/api/v1/broodstock/maintenance-tasks/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_broodstock_fish_endpoint(self):
        """Test that broodstock fish endpoint is accessible."""
        response = self.client.get('/api/v1/broodstock/fish/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_breeding_plans_endpoint(self):
        """Test that breeding plans endpoint is accessible."""
        response = self.client.get('/api/v1/broodstock/breeding-plans/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_egg_productions_endpoint(self):
        """Test that egg productions endpoint is accessible."""
        response = self.client.get('/api/v1/broodstock/egg-productions/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_authentication_required(self):
        """Test that authentication is required for API access."""
        self.client.logout()
        response = self.client.get('/api/v1/broodstock/fish/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED) 