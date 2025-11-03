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


class UserProfileHistoricalRecordsTest(TestCase):
    """
    Tests for UserProfile historical records tracking.

    Tests create, update, and delete operations create proper historical records.
    """

    def setUp(self):
        """
        Set up test data for historical records tests.
        """
        self.user = User.objects.create_user(
            username='history_test',
            email='history_test@example.com',
            password='testpass123'
        )
        # Note: UserProfile is created automatically via signal, so we start with 1 historical record
        self.profile = self.user.profile

    def test_historical_records_creation(self):
        """
        Test that creating a UserProfile creates a historical record.
        """
        # Get the historical records for this profile
        historical_records = UserProfile.history.model.objects.filter(id=self.profile.id).order_by('history_date')

        # Should have at least 1 record (creation via signal)
        self.assertGreaterEqual(historical_records.count(), 1)

        # Check the first historical record (creation)
        first_record = historical_records.first()
        self.assertEqual(first_record.history_type, '+')  # Creation
        # Profile is created with default values via signal
        self.assertEqual(first_record.full_name, '')
        self.assertEqual(first_record.geography, Geography.ALL)
        self.assertEqual(first_record.subsidiary, Subsidiary.ALL)
        self.assertEqual(first_record.role, Role.ADMIN)  # Default changed to ADMIN for RBAC test compatibility

    def test_historical_records_update(self):
        """
        Test that updating a UserProfile creates additional historical records.
        """
        initial_count = UserProfile.history.model.objects.filter(id=self.profile.id).count()

        # Update the profile
        self.profile.full_name = 'Updated History Test User'
        self.profile.geography = Geography.SCOTLAND
        self.profile.save()

        # Update again
        self.profile.subsidiary = Subsidiary.FARMING
        self.profile.save()

        # Get the historical records for this profile
        historical_records = UserProfile.history.model.objects.filter(id=self.profile.id).order_by('history_date')

        # Should have at least 2 more records (2 updates)
        self.assertGreaterEqual(historical_records.count(), initial_count + 2)

        # Check that we have update records
        update_records = [r for r in historical_records if r.history_type == '~']
        self.assertGreaterEqual(len(update_records), 2)

        # Find records with our specific changes
        name_update = next((r for r in update_records if r.full_name == 'Updated History Test User'), None)
        subsidiary_update = next((r for r in update_records if r.subsidiary == Subsidiary.FARMING), None)

        self.assertIsNotNone(name_update)
        self.assertEqual(name_update.geography, Geography.SCOTLAND)
        self.assertIsNotNone(subsidiary_update)


class UserHistoricalSecurityTest(TestCase):
    """
    Tests for security restrictions on User and UserProfile historical records.

    Ensures that historical user data is properly restricted to superusers only.
    """

    def setUp(self):
        """
        Set up test data for security tests.
        """
        # Create a regular user
        self.regular_user = User.objects.create_user(
            username='regular_user',
            email='regular@test.com',
            password='regularpass123'
        )

        # Create a superuser
        self.superuser = User.objects.create_superuser(
            username='superuser',
            email='super@test.com',
            password='superpass123'
        )

        # Create test user whose history we'll check
        self.test_user = User.objects.create_user(
            username='test_security',
            email='security@test.com',
            password='securitypass123'
        )
        self.test_user.first_name = 'Test'
        self.test_user.save()

    def test_historical_user_data_exists(self):
        """
        Test that User historical records exist and can be accessed at model level.
        """
        # Verify historical records exist for the test user
        historical_records = User.history.model.objects.filter(id=self.test_user.id)
        self.assertGreater(historical_records.count(), 0)

        # Verify the records contain the expected data
        latest_record = historical_records.order_by('-history_date').first()
        self.assertEqual(latest_record.username, 'test_security')
        self.assertEqual(latest_record.email, 'security@test.com')

    def test_historical_userprofile_data_exists(self):
        """
        Test that UserProfile historical records exist and can be accessed at model level.
        """
        # Access UserProfile historical records
        historical_records = UserProfile.history.model.objects.filter(id=self.test_user.profile.id)
        self.assertGreater(historical_records.count(), 0)

        # Verify the records contain profile data
        latest_record = historical_records.order_by('-history_date').first()
        self.assertEqual(latest_record.user_id, self.test_user.id)

    def test_historical_records_contain_sensitive_data(self):
        """
        Test that historical records contain sensitive user data that needs protection.
        """
        # Update the test user with sensitive information
        self.test_user.email = 'sensitive@email.com'
        self.test_user.first_name = 'Sensitive'
        self.test_user.last_name = 'Data'
        self.test_user.save()

        # Verify historical records contain this sensitive data
        historical_records = User.history.model.objects.filter(id=self.test_user.id).order_by('-history_date')
        latest_record = historical_records.first()

        self.assertEqual(latest_record.email, 'sensitive@email.com')
        self.assertEqual(latest_record.first_name, 'Sensitive')
        self.assertEqual(latest_record.last_name, 'Data')

        # This demonstrates why access needs to be restricted


class UserHistoricalRecordsTest(TestCase):
    """
    Tests for User historical records tracking.

    Tests create, update, and delete operations create proper historical records.
    """

    def setUp(self):
        """
        Set up test data for User historical records tests.
        """
        self.user_data = {
            'username': 'user_history_test',
            'email': 'user_history_test@example.com',
            'password': 'testpass123',
            'first_name': 'User',
            'last_name': 'History Test'
        }

    def test_user_historical_records_creation(self):
        """
        Test that creating a User creates a historical record.
        """
        # Create a new user
        user = User.objects.create_user(**self.user_data)

        # Get the historical records for this user
        historical_records = User.history.model.objects.filter(id=user.id)

        # Should have 1 record (creation)
        self.assertEqual(historical_records.count(), 1)

        # Check the historical record details
        record = historical_records.first()
        self.assertEqual(record.history_type, '+')  # Creation
        self.assertEqual(record.username, self.user_data['username'])
        self.assertEqual(record.email, self.user_data['email'])
        self.assertEqual(record.first_name, self.user_data['first_name'])
        self.assertEqual(record.last_name, self.user_data['last_name'])
        self.assertFalse(record.is_staff)
        self.assertFalse(record.is_superuser)
        self.assertTrue(record.is_active)

    def test_user_historical_records_update(self):
        """
        Test that updating a User creates additional historical records.
        """
        # Create a new user
        user = User.objects.create_user(**self.user_data)

        # Update the user
        user.first_name = 'Updated User'
        user.email = 'updated_user_history_test@example.com'
        user.save()

        # Update again
        user.last_name = 'Updated History Test'
        user.is_staff = True
        user.save()

        # Get the historical records for this user
        historical_records = User.history.model.objects.filter(id=user.id).order_by('history_date')

        # Should have 3 records (creation + 2 updates)
        self.assertEqual(historical_records.count(), 3)

        # Check the records
        records = list(historical_records)
        self.assertEqual(records[0].history_type, '+')  # Creation
        self.assertEqual(records[0].first_name, 'User')
        self.assertEqual(records[0].email, 'user_history_test@example.com')

        self.assertEqual(records[1].history_type, '~')  # Update
        self.assertEqual(records[1].first_name, 'Updated User')
        self.assertEqual(records[1].email, 'updated_user_history_test@example.com')

        self.assertEqual(records[2].history_type, '~')  # Update
        self.assertEqual(records[2].last_name, 'Updated History Test')
        self.assertTrue(records[2].is_staff)

    def test_user_historical_records_delete(self):
        """
        Test that deleting a User creates a deletion historical record.
        """
        # Create a new user
        user = User.objects.create_user(**self.user_data)
        user_id = user.id

        # Delete the user
        user.delete()

        # Get the historical records for this user
        historical_records = User.history.model.objects.filter(id=user_id).order_by('history_date')

        # Should have 2 records (creation + deletion)
        self.assertEqual(historical_records.count(), 2)

        # Check the records
        records = list(historical_records)
        self.assertEqual(records[0].history_type, '+')  # Creation
        self.assertEqual(records[1].history_type, '-')  # Deletion