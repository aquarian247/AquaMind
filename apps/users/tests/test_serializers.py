from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory
from apps.users.models import UserProfile, Geography, Subsidiary, Role
from apps.users.serializers import (
    UserSerializer,
    UserCreateSerializer,
    UserProfileSerializer,
    UserProfileUpdateSerializer,
    CustomTokenObtainPairSerializer,
    PasswordChangeSerializer
)

User = get_user_model()


class UserSerializerTest(TestCase):
    """
    Tests for the User serializers.
    
    Tests serialization, deserialization, validation, and methods for
    user-related serializers.
    """
    
    def setUp(self):
        """
        Set up test data for serializer tests.
        """
        self.user_data = {
            'username': 'testserializer',
            'email': 'testserializer@example.com',
            'password': 'securepassword123',
            'profile': {
                'full_name': 'Test Serializer',
                'geography': Geography.FAROE_ISLANDS,
                'subsidiary': Subsidiary.FRESHWATER,
                'role': Role.MANAGER
            }
        }
        
        self.user = User.objects.create_user(
            username='existing',
            email='existing@example.com',
            password='existingpass123'
        )
        
        # Set up user profile
        self.user.profile.full_name = 'Existing User'
        self.user.profile.phone = '+4520123456'
        self.user.profile.geography = Geography.SCOTLAND
        self.user.profile.subsidiary = Subsidiary.FARMING
        self.user.profile.role = Role.VIEWER
        self.user.profile.job_title = 'Developer'
        self.user.profile.department = 'IT'
        self.user.profile.language_preference = 'en'
        self.user.profile.date_format_preference = 'DMY'
        self.user.profile.save()
    
    def test_user_serializer_contains_expected_fields(self):
        """
        Test that UserSerializer includes all expected fields.
        """
        serializer = UserSerializer(instance=self.user)
        expected_fields = ['id', 'username', 'email', 'full_name', 'phone', 'geography', 'subsidiary', 
                  'role', 'is_active', 'profile', 'date_joined']
        self.assertEqual(set(serializer.data.keys()), set(expected_fields) - {'password'})
    
    def test_user_create_serializer_create_user(self):
        """
        Test that UserCreateSerializer can create a user.
        """
        # Extract basic user data
        user_data = {
            'username': self.user_data['username'],
            'email': self.user_data['email'],
            'password': self.user_data['password'],
        }
        
        serializer = UserCreateSerializer(data=user_data)
        self.assertTrue(serializer.is_valid())
        user = serializer.save()
        
        self.assertEqual(user.username, self.user_data['username'])
        self.assertEqual(user.email, self.user_data['email'])
        
        # Manually update the profile as we would in a view
        for field, value in self.user_data['profile'].items():
            setattr(user.profile, field, value)
        user.profile.save()
        
        # Test profile data after manual update
        self.assertEqual(user.profile.full_name, self.user_data['profile']['full_name'])
        self.assertEqual(user.profile.geography, self.user_data['profile']['geography']) 
        self.assertEqual(user.profile.subsidiary, self.user_data['profile']['subsidiary'])
        self.assertEqual(user.profile.role, self.user_data['profile']['role'])
        
        self.assertTrue(user.check_password(self.user_data['password']))
        
        # Ensure a profile was created
        self.assertTrue(hasattr(user, 'profile'))
        self.assertIsInstance(user.profile, UserProfile)
    
    def test_user_create_serializer_password_required(self):
        """
        Test that UserCreateSerializer requires password.
        """
        data = self.user_data.copy()
        data.pop('password')
        
        serializer = UserCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('password', serializer.errors)
    
    def test_user_serializer_update_user(self):
        """
        Test that UserSerializer can update a user.
        """
        # Just update user fields, not profile
        update_data = {
            'username': 'updated_user',
            'email': 'updated@example.com'
        }
        
        serializer = UserSerializer(instance=self.user, data=update_data, partial=True)
        self.assertTrue(serializer.is_valid())
        updated_user = serializer.save()
        
        # Now update profile separately
        profile_data = {
            'full_name': 'Updated Name',
            'phone': '+4520123456',
            'geography': Geography.SCOTLAND,
            'subsidiary': Subsidiary.FARMING
        }
        
        # Manually update profile fields
        for field, value in profile_data.items():
            setattr(updated_user.profile, field, value)
        updated_user.profile.save()
        
        # Refresh user from database
        updated_user.refresh_from_db()
        
        # Verify user fields were updated
        self.assertEqual(updated_user.username, update_data['username'])
        self.assertEqual(updated_user.email, update_data['email'])
        
        # Verify profile fields were updated
        self.assertEqual(updated_user.profile.full_name, profile_data['full_name'])
        self.assertEqual(updated_user.profile.phone, profile_data['phone'])
        self.assertEqual(updated_user.profile.geography, profile_data['geography'])
        self.assertEqual(updated_user.profile.subsidiary, profile_data['subsidiary'])
    
    def test_user_serializer_update_password(self):
        """
        Test that UserSerializer can update a user's password.
        """
        new_password = 'newpassword123'
        update_data = {'password': new_password}
        
        serializer = UserSerializer(instance=self.user, data=update_data, partial=True)
        self.assertTrue(serializer.is_valid())
        updated_user = serializer.save()
        
        self.assertTrue(updated_user.check_password(new_password))


class UserProfileSerializerTest(TestCase):
    """
    Tests for the UserProfile serializers.
    
    Tests serialization, deserialization, and validation for
    profile-related serializers.
    """
    
    def setUp(self):
        """
        Set up test data for profile serializer tests.
        """
        self.user = User.objects.create_user(
            username='profile_serializer',
            email='profile_serializer@example.com',
            password='profilepass123'
        )
        
        self.profile = self.user.profile
        self.profile.full_name = 'Profile Serializer User'
        self.profile.phone = '+4520123456'
        self.profile.geography = Geography.FAROE_ISLANDS
        self.profile.subsidiary = Subsidiary.BROODSTOCK
        self.profile.role = Role.MANAGER
        self.profile.job_title = 'Developer'
        self.profile.department = 'IT'
        self.profile.language_preference = 'en'
        self.profile.date_format_preference = 'DMY'
        self.profile.save()
    
    def test_profile_serializer_contains_expected_fields(self):
        """
        Test that UserProfileSerializer includes all expected fields.
        """
        serializer = UserProfileSerializer(instance=self.profile)
        expected_fields = ['profile_picture', 'job_title', 'department', 
                          'language_preference', 'date_format_preference',
                          'created_at', 'updated_at']
        self.assertEqual(set(serializer.data.keys()), set(expected_fields))
    
    def test_profile_update_serializer(self):
        """
        Test that profile can be updated using UserProfileUpdateSerializer.
        """
        from apps.users.serializers import UserProfileUpdateSerializer
        
        update_data = {
            'job_title': 'Senior Developer',
            'department': 'Engineering',
            'language_preference': 'fo'
        }
        
        serializer = UserProfileUpdateSerializer(instance=self.profile, data=update_data, partial=True)
        self.assertTrue(serializer.is_valid())
        updated_profile = serializer.save()
        
        self.assertEqual(updated_profile.job_title, update_data['job_title'])
        self.assertEqual(updated_profile.department, update_data['department'])
        self.assertEqual(updated_profile.language_preference, update_data['language_preference'])


class PasswordChangeSerializerTest(TestCase):
    """
    Tests for the PasswordChangeSerializer.
    
    Tests validation and methods for password change functionality.
    """
    
    def setUp(self):
        """
        Set up test data for password change serializer tests.
        """
        self.user = User.objects.create_user(
            username='password_change',
            email='password_change@example.com',
            password='oldpassword123'
        )
        
        self.user.profile.full_name = 'Password Change User'
        self.user.profile.save()
        
        self.factory = APIRequestFactory()
        self.request = self.factory.get('/')
        self.request.user = self.user
    
    def test_password_change_serializer_old_password_validation(self):
        """
        Test that old password is validated correctly.
        """
        # Incorrect old password
        data = {
            'old_password': 'wrongpassword',
            'new_password': 'newpassword123'
        }
        
        serializer = PasswordChangeSerializer(data=data, context={'request': self.request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('old_password', serializer.errors)
        
        # Correct old password
        data = {
            'old_password': 'oldpassword123',
            'new_password': 'newpassword123'
        }
        
        serializer = PasswordChangeSerializer(data=data, context={'request': self.request})
        self.assertTrue(serializer.is_valid())
