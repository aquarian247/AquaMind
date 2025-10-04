"""
Security tests for users app - Task 1: Privilege Escalation Prevention

Tests to ensure non-admin users cannot modify RBAC fields (role, geography, subsidiary)
and that admin users can still modify these fields through appropriate endpoints.
"""

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
import json

from apps.users.models import Geography, Subsidiary, Role

User = get_user_model()


class PrivilegeEscalationPreventionTest(TestCase):
    """
    Tests to prevent privilege escalation through profile updates.
    
    Critical security tests ensuring users cannot modify their own RBAC fields
    (role, geography, subsidiary) to gain unauthorized access.
    """
    
    def setUp(self):
        """
        Set up test data and client for security tests.
        """
        # Create admin user
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        self.admin_user.profile.full_name = 'Admin User'
        self.admin_user.profile.role = Role.ADMIN
        self.admin_user.profile.geography = Geography.ALL
        self.admin_user.profile.subsidiary = Subsidiary.ALL
        self.admin_user.profile.save()
        
        # Create regular user with limited permissions
        self.regular_user = User.objects.create_user(
            username='regular',
            email='regular@example.com',
            password='regularpass123'
        )
        self.regular_user.profile.full_name = 'Regular User'
        self.regular_user.profile.geography = Geography.FAROE_ISLANDS
        self.regular_user.profile.subsidiary = Subsidiary.FRESHWATER
        self.regular_user.profile.role = Role.VIEWER
        self.regular_user.profile.save()
        
        # Set up API client
        self.client = APIClient()
    
    def test_regular_user_cannot_update_role_via_profile_endpoint(self):
        """
        Test that regular users cannot update their role via the profile endpoint.
        
        This is the primary privilege escalation vector - users attempting to
        grant themselves admin privileges.
        """
        self.client.force_authenticate(user=self.regular_user)
        url = reverse('user_profile')
        
        # Attempt to escalate to ADMIN role
        update_data = {
            'role': Role.ADMIN,
            'full_name': 'Updated Name'
        }
        
        response = self.client.patch(url, update_data, format='json')
        
        # Request should succeed (200) but role should not be updated
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify role was NOT updated
        self.regular_user.profile.refresh_from_db()
        self.assertEqual(self.regular_user.profile.role, Role.VIEWER)
        
        # Verify allowed fields were updated
        self.assertEqual(self.regular_user.profile.full_name, 'Updated Name')
    
    def test_regular_user_cannot_update_geography_via_profile_endpoint(self):
        """
        Test that regular users cannot update their geography via the profile endpoint.
        
        Geography field controls data visibility across regions.
        """
        self.client.force_authenticate(user=self.regular_user)
        url = reverse('user_profile')
        
        # Attempt to change geography to ALL (broader access)
        update_data = {
            'geography': Geography.ALL,
            'full_name': 'Updated Name'
        }
        
        response = self.client.patch(url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify geography was NOT updated
        self.regular_user.profile.refresh_from_db()
        self.assertEqual(self.regular_user.profile.geography, Geography.FAROE_ISLANDS)
        
        # Verify allowed fields were updated
        self.assertEqual(self.regular_user.profile.full_name, 'Updated Name')
    
    def test_regular_user_cannot_update_subsidiary_via_profile_endpoint(self):
        """
        Test that regular users cannot update their subsidiary via the profile endpoint.
        
        Subsidiary field controls data visibility across business units.
        """
        self.client.force_authenticate(user=self.regular_user)
        url = reverse('user_profile')
        
        # Attempt to change subsidiary to ALL (broader access)
        update_data = {
            'subsidiary': Subsidiary.ALL,
            'full_name': 'Updated Name'
        }
        
        response = self.client.patch(url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify subsidiary was NOT updated
        self.regular_user.profile.refresh_from_db()
        self.assertEqual(self.regular_user.profile.subsidiary, Subsidiary.FRESHWATER)
        
        # Verify allowed fields were updated
        self.assertEqual(self.regular_user.profile.full_name, 'Updated Name')
    
    def test_regular_user_cannot_update_rbac_fields_via_user_serializer(self):
        """
        Test that UserSerializer.update() enforces RBAC field restrictions.
        
        This tests the server-side enforcement in the serializer itself.
        """
        self.client.force_authenticate(user=self.regular_user)
        url = reverse('user-detail', args=[self.regular_user.id])
        
        # Attempt to update RBAC fields through user endpoint
        update_data = {
            'email': 'updated@example.com',
            'role': Role.ADMIN,
            'geography': Geography.ALL,
            'subsidiary': Subsidiary.ALL
        }
        
        response = self.client.patch(url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify RBAC fields were NOT updated
        self.regular_user.refresh_from_db()
        self.assertEqual(self.regular_user.profile.role, Role.VIEWER)
        self.assertEqual(self.regular_user.profile.geography, Geography.FAROE_ISLANDS)
        self.assertEqual(self.regular_user.profile.subsidiary, Subsidiary.FRESHWATER)
        
        # Verify allowed fields were updated
        self.assertEqual(self.regular_user.email, 'updated@example.com')
    
    def test_admin_can_update_rbac_fields_via_admin_endpoint(self):
        """
        Test that admin users CAN update RBAC fields through the admin endpoint.
        
        Ensures the admin functionality works correctly after security fixes.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('user-admin-update', args=[self.regular_user.id])
        
        # Admin updates RBAC fields
        update_data = {
            'role': Role.MANAGER,
            'geography': Geography.SCOTLAND,
            'subsidiary': Subsidiary.FARMING
        }
        
        response = self.client.patch(url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify RBAC fields WERE updated
        self.regular_user.profile.refresh_from_db()
        self.assertEqual(self.regular_user.profile.role, Role.MANAGER)
        self.assertEqual(self.regular_user.profile.geography, Geography.SCOTLAND)
        self.assertEqual(self.regular_user.profile.subsidiary, Subsidiary.FARMING)
    
    def test_regular_user_cannot_access_admin_endpoint(self):
        """
        Test that regular users cannot access the admin update endpoint.
        
        Verifies proper permission checks on the admin endpoint.
        """
        self.client.force_authenticate(user=self.regular_user)
        url = reverse('user-admin-update', args=[self.regular_user.id])
        
        update_data = {
            'role': Role.ADMIN
        }
        
        response = self.client.patch(url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Verify role was NOT updated
        self.regular_user.profile.refresh_from_db()
        self.assertEqual(self.regular_user.profile.role, Role.VIEWER)
    
    def test_profile_get_request_includes_rbac_fields(self):
        """
        Test that GET requests to profile endpoint include RBAC fields for visibility.
        
        Users should be able to see their current RBAC settings even though they
        cannot modify them.
        """
        self.client.force_authenticate(user=self.regular_user)
        url = reverse('user_profile')
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = json.loads(response.content)
        
        # Verify RBAC fields are included in response
        self.assertIn('role', data)
        self.assertIn('geography', data)
        self.assertIn('subsidiary', data)
        
        # Verify values match the user's profile
        self.assertEqual(data['role'], self.regular_user.profile.role)
        self.assertEqual(data['geography'], self.regular_user.profile.geography)
        self.assertEqual(data['subsidiary'], self.regular_user.profile.subsidiary)
    
    def test_admin_can_update_user_via_user_serializer(self):
        """
        Test that admin users can update RBAC fields through UserSerializer.
        
        Verifies the server-side enforcement allows admin users to make updates.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('user-detail', args=[self.regular_user.id])
        
        update_data = {
            'email': 'newadmin@example.com',
            'role': Role.MANAGER,
            'geography': Geography.SCOTLAND
        }
        
        response = self.client.patch(url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify both regular and RBAC fields were updated
        self.regular_user.refresh_from_db()
        self.assertEqual(self.regular_user.email, 'newadmin@example.com')
        self.assertEqual(self.regular_user.profile.role, Role.MANAGER)
        self.assertEqual(self.regular_user.profile.geography, Geography.SCOTLAND)
    
    def test_regular_user_can_update_allowed_profile_fields(self):
        """
        Test that regular users CAN update allowed profile fields.
        
        Ensures the security fix doesn't prevent legitimate profile updates.
        """
        self.client.force_authenticate(user=self.regular_user)
        url = reverse('user_profile')
        
        update_data = {
            'full_name': 'New Full Name',
            'phone': '+4521111111',
            'job_title': 'Senior Developer',
            'department': 'Engineering',
            'language_preference': 'fo',
            'date_format_preference': 'YMD'
        }
        
        response = self.client.patch(url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify all allowed fields were updated
        self.regular_user.profile.refresh_from_db()
        self.assertEqual(self.regular_user.profile.full_name, 'New Full Name')
        self.assertEqual(self.regular_user.profile.phone, '+4521111111')
        self.assertEqual(self.regular_user.profile.job_title, 'Senior Developer')
        self.assertEqual(self.regular_user.profile.department, 'Engineering')
        self.assertEqual(self.regular_user.profile.language_preference, 'fo')
        self.assertEqual(self.regular_user.profile.date_format_preference, 'YMD')
        
        # Verify RBAC fields remain unchanged
        self.assertEqual(self.regular_user.profile.role, Role.VIEWER)
        self.assertEqual(self.regular_user.profile.geography, Geography.FAROE_ISLANDS)
        self.assertEqual(self.regular_user.profile.subsidiary, Subsidiary.FRESHWATER)

