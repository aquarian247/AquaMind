"""
RBAC Test Utilities

Provides helper methods and mixins for creating test users with proper RBAC setup.
"""

from django.contrib.auth.models import User
from apps.users.models import UserProfile, Geography, Subsidiary, Role
from apps.infrastructure.models import Geography as InfraGeography


class RBACTestMixin:
    """Mixin to help create test users with proper RBAC setup."""
    
    @classmethod
    def create_test_user_with_profile(cls, username, geography=Geography.SCOTLAND, role=Role.ADMIN, subsidiary=Subsidiary.ALL):
        """
        Create a test user with proper UserProfile for RBAC.
        
        Args:
            username: Username for the user
            geography: Geography choice (default: Scotland)
            role: Role choice (default: Admin)
            subsidiary: Subsidiary choice (default: All)
            
        Returns:
            User instance with profile
        """
        user = User.objects.create_user(username=username, password='testpass123')
        profile = UserProfile.objects.create(
            user=user,
            geography=geography,
            role=role,
            subsidiary=subsidiary
        )
        return user
    
    @classmethod
    def create_scottish_admin(cls):
        """Create a Scottish admin user for tests."""
        return cls.create_test_user_with_profile('scottish_admin', Geography.SCOTLAND, Role.ADMIN)
    
    @classmethod
    def create_scottish_operator(cls):
        """Create a Scottish operator user for tests."""
        return cls.create_test_user_with_profile('scottish_operator', Geography.SCOTLAND, Role.OPERATOR)
    
    @classmethod
    def create_faroese_admin(cls):
        """Create a Faroese admin user for tests."""
        return cls.create_test_user_with_profile('faroese_admin', Geography.FAROE_ISLANDS, Role.ADMIN)
    
    @classmethod
    def create_veterinarian(cls, geography=Geography.SCOTLAND):
        """Create a veterinarian user for health tests."""
        return cls.create_test_user_with_profile(f'vet_{geography.lower()}', geography, Role.VETERINARIAN)
    
    @classmethod
    def create_superuser_with_profile(cls):
        """Create a superuser with profile (bypasses all RBAC)."""
        user = User.objects.create_superuser(username='superuser', password='testpass123', email='super@test.com')
        UserProfile.objects.create(
            user=user,
            geography=Geography.ALL,
            role=Role.ADMIN,
            subsidiary=Subsidiary.ALL
        )
        return user


def disable_rbac_for_test(test_func):
    """
    Decorator to temporarily disable RBAC for a specific test.
    
    Use this for tests that are testing non-RBAC functionality
    and don't want RBAC interference.
    """
    def wrapper(self):
        # Create a superuser for the test
        self.user = User.objects.create_superuser(
            username='test_superuser',
            password='testpass123',
            email='test@example.com'
        )
        UserProfile.objects.create(
            user=self.user,
            geography=Geography.ALL,
            role=Role.ADMIN,
            subsidiary=Subsidiary.ALL
        )
        self.client.force_authenticate(user=self.user)
        return test_func(self)
    return wrapper


# Helper to ensure Infrastructure Geographies exist for tests
def ensure_test_geographies():
    """Ensure required Infrastructure Geography objects exist for tests."""
    scotland, _ = InfraGeography.objects.get_or_create(
        name='Scotland',
        defaults={'description': 'Scotland operations'}
    )
    faroe, _ = InfraGeography.objects.get_or_create(
        name='Faroe Islands', 
        defaults={'description': 'Faroe Islands operations'}
    )
    return scotland, faroe
