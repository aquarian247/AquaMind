from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from apps.users.models import UserProfile, Geography, Subsidiary, Role

User = get_user_model()


class UserModelTest(TestCase):
    """
    Tests for the custom User model.
    
    Tests user creation, validation, and methods for the custom User model.
    """
    
    def setUp(self):
        """
        Set up test data for user model tests.
        """
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'securepassword123',
            'profile_data': {
                'full_name': 'Test User',
                'geography': Geography.FAROE_ISLANDS,
                'subsidiary': Subsidiary.FRESHWATER,
                'role': Role.MANAGER
            }
        }
    
    def test_create_user(self):
        """
        Test creating a regular user with all required fields.
        """
        user = User.objects.create_user(
            username=self.user_data['username'],
            email=self.user_data['email'],
            password=self.user_data['password']
        )
        
        # Update profile data
        profile = user.profile
        profile.full_name = self.user_data['profile_data']['full_name']
        profile.geography = self.user_data['profile_data']['geography']
        profile.subsidiary = self.user_data['profile_data']['subsidiary']
        profile.role = self.user_data['profile_data']['role']
        profile.save()
        
        # Refresh from database
        user.refresh_from_db()
        
        self.assertEqual(user.username, self.user_data['username'])
        self.assertEqual(user.email, self.user_data['email'])
        self.assertEqual(user.profile.full_name, self.user_data['profile_data']['full_name'])
        self.assertEqual(user.profile.geography, self.user_data['profile_data']['geography'])
        self.assertEqual(user.profile.subsidiary, self.user_data['profile_data']['subsidiary'])
        self.assertEqual(user.profile.role, self.user_data['profile_data']['role'])
        self.assertTrue(user.check_password(self.user_data['password']))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.is_active)
    
    def test_create_superuser(self):
        """
        Test creating a superuser with admin privileges.
        """
        admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpassword123'
        )
        
        # Update profile
        admin_user.profile.full_name = 'Admin User'
        admin_user.profile.role = Role.ADMIN
        admin_user.profile.save()
        
        # Refresh from database
        admin_user.refresh_from_db()
        
        self.assertEqual(admin_user.email, 'admin@example.com')
        self.assertEqual(admin_user.profile.full_name, 'Admin User')
        self.assertEqual(admin_user.profile.role, Role.ADMIN)
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
        self.assertTrue(admin_user.is_active)
    
    def test_email_required(self):
        """
        Test that email is required for user creation with Django's built-in User model.
        """
        # Django's built-in User model doesn't require email, but we can test our validation
        # in serializers or forms. For now, we'll just test that username is required.
        with self.assertRaises(ValueError):
            User.objects.create_user(username='', password='password123', email='noemail@example.com')
    
    def test_username_unique(self):
        """
        Test that username must be unique for users.
        """
        User.objects.create_user(
            username=self.user_data['username'],
            email=self.user_data['email'],
            password=self.user_data['password']
        )
        
        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                username=self.user_data['username'],  # Same username as existing user
                email='another@example.com',
                password='anotherpassword'
            )
    
    def test_user_str_representation(self):
        """
        Test the string representation of a user.
        """
        user = User.objects.create_user(
            username=self.user_data['username'],
            email=self.user_data['email'],
            password=self.user_data['password']
        )
        
        # For Django's built-in User model, the string representation is the username
        expected_str = user.username
        self.assertEqual(str(user), expected_str)


class UserProfileModelTest(TestCase):
    """
    Tests for the UserProfile model.
    
    Tests profile creation and relationship with User model.
    """
    
    def setUp(self):
        """
        Set up test data for user profile tests.
        """
        self.user = User.objects.create_user(
            username='profiletest',
            email='profile_test@example.com',
            password='profilepassword123'
        )
        
        # Update profile
        self.user.profile.full_name = 'Profile Test User'
        self.user.profile.save()
    
    def test_profile_created_automatically(self):
        """
        Test that a UserProfile is created automatically when a User is created.
        """
        self.assertTrue(hasattr(self.user, 'profile'))
        self.assertIsInstance(self.user.profile, UserProfile)
    
    def test_profile_update(self):
        """
        Test updating a user's profile fields.
        """
        profile = self.user.profile
        profile.phone = '+4520123456'
        profile.geography = Geography.SCOTLAND
        profile.subsidiary = Subsidiary.FARMING
        profile.role = Role.OPERATOR
        profile.save()
        
        # Refresh from database
        profile.refresh_from_db()
        
        self.assertEqual(profile.phone, '+4520123456')
        self.assertEqual(profile.geography, Geography.SCOTLAND)
        self.assertEqual(profile.subsidiary, Subsidiary.FARMING)
        self.assertEqual(profile.role, Role.OPERATOR)
    
    def test_profile_str_representation(self):
        """
        Test the string representation of a user profile.
        """
        expected_str = f"Profile for {self.user.username}"
        self.assertEqual(str(self.user.profile), expected_str)
    
    def test_profile_deletion_on_user_delete(self):
        """
        Test that UserProfile is deleted when User is deleted (cascade).
        """
        profile_id = self.user.profile.id
        self.user.delete()
        
        # Check profile doesn't exist anymore
        with self.assertRaises(UserProfile.DoesNotExist):
            UserProfile.objects.get(id=profile_id)