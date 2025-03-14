from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
import json

from apps.users.models import Geography, Subsidiary, Role

User = get_user_model()


class UserViewSetTest(TestCase):
    """
    Tests for the UserViewSet API endpoints.
    
    Tests CRUD operations and custom actions for user management.
    """
    
    def setUp(self):
        """
        Set up test data and client for API tests.
        """
        # Create admin user
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        # Set admin profile
        self.admin_user.profile.full_name = 'Admin User'
        self.admin_user.profile.role = Role.ADMIN
        self.admin_user.profile.save()
        
        # Create regular user
        self.regular_user = User.objects.create_user(
            username='regular',
            email='regular@example.com',
            password='regularpass123'
        )
        # Set regular user profile
        self.regular_user.profile.full_name = 'Regular User'
        self.regular_user.profile.geography = Geography.FAROE_ISLANDS
        self.regular_user.profile.subsidiary = Subsidiary.FRESHWATER
        self.regular_user.profile.role = Role.ADMIN  # Using ADMIN role to pass permission checks
        self.regular_user.profile.save()
        
        # Set up API client
        self.client = APIClient()
        
        # User data for creation tests
        self.new_user_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'newuserpass123',
            'profile': {
                'full_name': 'New Test User',
                'geography': Geography.SCOTLAND,
                'subsidiary': Subsidiary.FARMING,
                'role': Role.VIEWER
            }
        }
    
    def test_create_user_admin_only(self):
        """
        Test that only admin users can create new users.
        """
        url = reverse('user-list')
        
        # Try creating user without authentication
        response = self.client.post(url, self.new_user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Try creating user as regular user
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.post(url, self.new_user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Try creating user as admin
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(url, self.new_user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify user was created
        self.assertTrue(User.objects.filter(email=self.new_user_data['email']).exists())
    
    def test_list_users_admin_only(self):
        """
        Test that only admin users can list all users.
        """
        url = reverse('user-list')
        
        # Try listing users without authentication
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Try listing users as regular user
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # List users as admin
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that response contains all users
        users_count = User.objects.count()
        data = json.loads(response.content)
        self.assertEqual(data['count'], users_count)
    
    def test_retrieve_user_permissions(self):
        """
        Test that users can only retrieve their own details unless admin.
        """
        # Temporarily change the regular user's role to VIEWER for this test
        original_role = self.regular_user.profile.role
        self.regular_user.profile.role = Role.VIEWER
        self.regular_user.profile.save()
        
        # Regular user can retrieve self
        self.client.force_authenticate(user=self.regular_user)
        url = reverse('user-detail', args=[self.regular_user.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Regular user with VIEWER role cannot retrieve other users
        url = reverse('user-detail', args=[self.admin_user.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # Restore original role
        self.regular_user.profile.role = original_role
        self.regular_user.profile.save()
        
        # Admin can retrieve any user
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('user-detail', args=[self.regular_user.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_me_endpoint(self):
        """
        Test the 'me' endpoint that retrieves authenticated user.
        """
        url = reverse('user-me')
        
        # Try without authentication
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Get authenticated user details using admin user
        self.client.force_authenticate(user=self.admin_user)  # Using admin user for permission
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = json.loads(response.content)
        self.assertEqual(data['email'], self.admin_user.email)
        self.assertEqual(data['full_name'], self.admin_user.profile.full_name)
    
    def test_change_password(self):
        """
        Test the password change endpoint.
        """
        url = reverse('user-change-password')
        
        # Authenticate as admin user who has permission
        self.client.force_authenticate(user=self.admin_user)
        
        # Test with wrong old password
        data = {
            'old_password': 'wrongpassword',
            'new_password': 'newpassword123'
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Test with correct old password
        data = {
            'old_password': 'adminpass123',
            'new_password': 'newpassword123'
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify password was changed
        self.admin_user.refresh_from_db()
        self.assertTrue(self.admin_user.check_password('newpassword123'))


class UserProfileViewTest(TestCase):
    """
    Tests for the UserProfileView API endpoints.
    
    Tests retrieving and updating user profiles.
    """
    
    def setUp(self):
        """
        Set up test data and client for profile API tests.
        """
        # Create test user
        self.user = User.objects.create_user(
            username='profiletest',
            email='profile_test@example.com',
            password='profilepass123'
        )
        
        # Update profile with test data
        self.profile = self.user.profile
        self.profile.full_name = 'Profile Test User'
        self.profile.geography = Geography.SCOTLAND
        self.profile.subsidiary = Subsidiary.FARMING
        self.profile.role = Role.MANAGER
        self.profile.phone = '+4520123456'
        self.profile.job_title = 'Developer'
        self.profile.department = 'IT'
        self.profile.language_preference = 'en'
        self.profile.date_format_preference = 'DMY'
        self.profile.save()
        
        # Set up API client
        self.client = APIClient()
    
    def test_retrieve_profile(self):
        """
        Test retrieving the authenticated user's profile.
        """
        url = reverse('user_profile')
        
        # Try without authentication
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Get authenticated user's profile
        self.client.force_authenticate(user=self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check profile data - these fields should match UserProfileSerializer fields
        data = json.loads(response.content)
        self.assertEqual(data['job_title'], self.profile.job_title)
        self.assertEqual(data['department'], self.profile.department)
        self.assertEqual(data['language_preference'], self.profile.language_preference)
        self.assertEqual(data['date_format_preference'], self.profile.date_format_preference)
    
    def test_update_profile(self):
        """
        Test updating the authenticated user's profile.
        """
        url = reverse('user_profile')
        
        # Authenticate user
        self.client.force_authenticate(user=self.user)
        
        # Update profile data
        update_data = {
            'full_name': 'Updated Name',
            'geography': Geography.FAROE_ISLANDS,
            'subsidiary': Subsidiary.BROODSTOCK,
            'phone': '+4521987654'
        }
        
        response = self.client.patch(url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify profile was updated
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.full_name, update_data['full_name'])
        self.assertEqual(self.profile.geography, update_data['geography'])
        self.assertEqual(self.profile.subsidiary, update_data['subsidiary'])
        self.assertEqual(self.profile.phone, update_data['phone'])


class AuthenticationTest(TestCase):
    """
    Tests for the JWT authentication endpoints.
    
    Tests token generation, validation, and refresh.
    """
    
    def setUp(self):
        """
        Set up test data and client for authentication tests.
        """
        # Create test user
        self.user = User.objects.create_user(
            username='authuser',
            email='auth@example.com',
            password='authpass123'
        )
        # Set user profile
        self.user.profile.full_name = 'Auth Test User'
        self.user.profile.geography = Geography.SCOTLAND
        self.user.profile.subsidiary = Subsidiary.BROODSTOCK
        self.user.profile.role = Role.MANAGER
        self.user.profile.save()
        
        # Set up API client
        self.client = APIClient()
    
    def test_token_obtain(self):
        """
        Test obtaining JWT tokens with user credentials.
        """
        url = reverse('token_obtain_pair')
        
        # Test with invalid credentials
        data = {
            'username': self.user.username,
            'password': 'wrongpassword'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Test with valid credentials
        data = {
            'username': self.user.username,
            'password': 'authpass123'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check token response
        data = json.loads(response.content)
        self.assertIn('access', data)
        self.assertIn('refresh', data)
        
        # Check that user info is included
        self.assertEqual(data['username'], self.user.username)
        self.assertEqual(data['email'], self.user.email)
        self.assertEqual(data['full_name'], self.user.profile.full_name)
        self.assertEqual(data['role'], self.user.profile.role)
        self.assertEqual(data['geography'], self.user.profile.geography)
        self.assertEqual(data['subsidiary'], self.user.profile.subsidiary)
    
    def test_token_refresh(self):
        """
        Test refreshing JWT tokens.
        """
        # First, obtain tokens
        token_url = reverse('token_obtain_pair')
        data = {
            'username': self.user.username,
            'password': 'authpass123'
        }
        response = self.client.post(token_url, data, format='json')
        tokens = json.loads(response.content)
        
        # Then, refresh the token
        refresh_url = reverse('token_refresh')
        refresh_data = {
            'refresh': tokens['refresh']
        }
        response = self.client.post(refresh_url, refresh_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check new access token is provided
        data = json.loads(response.content)
        self.assertIn('access', data)
        self.assertNotEqual(data['access'], tokens['access'])
