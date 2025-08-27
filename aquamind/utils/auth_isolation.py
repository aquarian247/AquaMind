"""
Authentication Isolation System for CI/CD

This module provides a robust mechanism to distinguish between unit tests and
Schemathesis contract testing runs in CI environments, ensuring proper authentication
behavior without global state conflicts.

Key Features:
- Thread-safe context tracking using thread-local storage
- Database-agnostic mock user creation
- Reliable detection of test vs contract testing execution
- Clean separation of authentication contexts

Usage:
    # For Schemathesis runs (set in CI workflow):
    export SCHEMATHESIS_MODE=1

    # The system will automatically detect and provide mock authentication
    # while keeping unit tests using normal authentication flow
"""

import os
import sys
import threading
import uuid
from contextlib import contextmanager
from typing import Optional, Any

from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from drf_spectacular.extensions import OpenApiAuthenticationExtension


# Thread-local storage for tracking execution context
_local = threading.local()


class ExecutionContext:
    """Tracks the current execution context (test vs schemathesis)"""

    def __init__(self):
        self.is_schemathesis_mode = False
        self.is_test_mode = False
        self.context_id = str(uuid.uuid4())

    def set_schemathesis_mode(self):
        """Mark current thread as running Schemathesis"""
        self.is_schemathesis_mode = True
        self.is_test_mode = False

    def set_test_mode(self):
        """Mark current thread as running unit tests"""
        self.is_test_mode = True
        self.is_schemathesis_mode = False

    def reset(self):
        """Reset context to default state"""
        self.is_schemathesis_mode = False
        self.is_test_mode = False


def get_execution_context() -> ExecutionContext:
    """Get or create execution context for current thread"""
    if not hasattr(_local, 'execution_context'):
        _local.execution_context = ExecutionContext()
    return _local.execution_context


def is_schemathesis_mode() -> bool:
    """Check if current execution is in Schemathesis mode"""
    # Check environment variable first (most reliable)
    if os.getenv('SCHEMATHESIS_MODE') == '1':
        return True

    # Check thread-local context
    context = get_execution_context()
    return context.is_schemathesis_mode


def is_test_mode() -> bool:
    """Check if current execution is in test mode"""
    # If we explicitly set schemathesis mode (via env var or context), we're not in test mode
    if is_schemathesis_mode():
        return False

    context = get_execution_context()

    # Check thread-local context
    if context.is_test_mode:
        return True

    # Fallback to detection patterns (less reliable but useful)
    # Only consider it test mode if we haven't explicitly set schemathesis mode
    return (
        'test' in os.getenv('DJANGO_SETTINGS_MODULE', '') or
        any('test' in arg.lower() for arg in sys.argv) or
        os.getenv('PYTEST_CURRENT_TEST') is not None or
        'manage.py' in sys.argv[0] and len(sys.argv) > 1 and sys.argv[1] == 'test'
    )


@contextmanager
def schemathesis_context():
    """Context manager to explicitly mark Schemathesis execution"""
    context = get_execution_context()
    old_schemathesis = context.is_schemathesis_mode
    old_test = context.is_test_mode

    context.set_schemathesis_mode()

    try:
        yield
    finally:
        context.is_schemathesis_mode = old_schemathesis
        context.is_test_mode = old_test


@contextmanager
def test_context():
    """Context manager to explicitly mark test execution"""
    context = get_execution_context()
    old_schemathesis = context.is_schemathesis_mode
    old_test = context.is_test_mode

    context.set_test_mode()

    try:
        yield
    finally:
        context.is_schemathesis_mode = old_schemathesis
        context.is_test_mode = old_test


class CIMockUser:
    """
    Database-agnostic mock user that works across SQLite and PostgreSQL.

    This user is created once per database session and reused, avoiding
    relationship errors while maintaining consistency.
    """

    _instance = None
    _instance_lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Use __dict__ directly to avoid triggering __getattr__
        if not self.__dict__.get('_initialized', False):
            self._initialized = True
            self._user = None
            self._create_or_get_user()
            # Set up method bindings after initialization
            self._setup_methods()

    def _setup_methods(self):
        """Set up method bindings that can't be handled by __getattr__"""
        # Define is_authenticated as a proper method
        def is_authenticated():
            return True
        self.is_authenticated = is_authenticated

        # Define other methods that need to be callable
        def get_full_name():
            return f"{self.first_name} {self.last_name}"
        self.get_full_name = get_full_name

        def get_short_name():
            return self.first_name
        self.get_short_name = get_short_name

        def __int__():
            return self.id
        self.__int__ = __int__

    def __str__(self):
        """Return string representation of the user"""
        return self.username

    def _create_or_get_user(self):
        """Create or retrieve mock user in a database-agnostic way"""
        # Import Django models here to avoid AppRegistryNotReady
        from django.contrib.auth.models import User
        from django.db import transaction

        # Use a fixed username to ensure consistency across runs
        username = 'schemathesis_mock_user'

        try:
            with transaction.atomic():
                user, created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        'email': 'schemathesis@test.local',
                        'first_name': 'Schema',
                        'last_name': 'Thesis',
                        'is_active': True,
                        'is_staff': True,
                        'is_superuser': True
                    }
                )
                self._user = user

                if created:
                    print(f"🔑 Created mock user: {username}", file=sys.stderr)

        except Exception as e:
            # Fallback for database issues - create in-memory user
            print(f"⚠️  Database user creation failed, using in-memory fallback: {e}", file=sys.stderr)
            self._user = None
            self._username = username
            self._id = 999999  # Fixed ID for consistency

    @property
    def user(self):
        """Get the underlying User model instance"""
        return self._user

    def __getattr__(self, name):
        """Delegate attribute access to the underlying user or provide defaults"""
        # Use __dict__ to avoid triggering __getattr__ recursively
        user = self.__dict__.get('_user')
        if user is not None:
            return getattr(user, name)

        # Fallback attributes for in-memory user
        fallbacks = {
            'id': self.__dict__.get('_id', 999999),
            'username': self.__dict__.get('_username', 'schemathesis_mock_user'),
            'email': 'schemathesis@test.local',
            'first_name': 'Schema',
            'last_name': 'Thesis',
            'is_active': True,
            'is_staff': True,
            'is_superuser': True,
            'date_joined': None,
        }

        if name in fallbacks:
            return fallbacks[name]

        raise AttributeError(f"'CIMockUser' has no attribute '{name}'")


class CIAuthentication(BaseAuthentication):
    """
    Authentication class that provides mock user for Schemathesis
    while allowing normal authentication for unit tests.
    """

    def authenticate(self, request: Request) -> Optional[tuple]:
        """
        Authenticate the request based on execution context.

        Returns:
            - Mock user tuple for Schemathesis mode
            - None for unit tests (let normal auth classes handle it)
        """
        if is_schemathesis_mode():
            print("🔑 CI Auth: Providing mock user for Schemathesis", file=sys.stderr)
            mock_user = CIMockUser()
            return (mock_user, None)

        # For unit tests, let normal authentication classes handle it
        print("🔍 CI Auth: Using normal authentication for tests", file=sys.stderr)
        return None


class CIPermission(BasePermission):
    """
    Permission class that allows full access for Schemathesis
    while enforcing normal permissions for unit tests.
    """

    def has_permission(self, request: Request, view: Any) -> bool:
        """
        Check permissions based on execution context.

        Returns:
            - True for Schemathesis mode (full access)
            - True for authenticated users in test mode (delegate to normal flow)
            - False for unauthenticated users in test mode
        """
        if is_schemathesis_mode():
            print("🔓 CI Permission: Allowing full access for Schemathesis", file=sys.stderr)
            return True

        # For unit tests, check if user is authenticated
        if hasattr(request, 'user') and request.user and request.user.is_authenticated:
            print("🔓 CI Permission: Allowing authenticated user in test mode", file=sys.stderr)
            return True

        # For unauthenticated requests in test mode
        print("🔍 CI Permission: Blocking unauthenticated request in test mode", file=sys.stderr)
        return False

    def has_object_permission(self, request: Request, view: Any, obj: Any) -> bool:
        """
        Check object-level permissions based on execution context.
        """
        if is_schemathesis_mode():
            print("🔓 CI Permission: Allowing object access for Schemathesis", file=sys.stderr)
            return True

        # For unit tests, check if user is authenticated
        if hasattr(request, 'user') and request.user and request.user.is_authenticated:
            print("🔓 CI Permission: Allowing object access for authenticated user in test mode", file=sys.stderr)
            return True

        # For unauthenticated requests in test mode
        print("🔍 CI Permission: Blocking object access for unauthenticated request in test mode", file=sys.stderr)
        return False


class CIAuthenticationScheme(OpenApiAuthenticationExtension):
    """
    OpenAPI extension for CIAuthentication to properly document
    the authentication scheme in the generated schema.
    """
    target_class = 'aquamind.utils.auth_isolation.CIAuthentication'
    name = 'tokenAuth'

    def get_security_definition(self, auto_schema):
        return {
            'type': 'apiKey',
            'in': 'header',
            'name': 'Authorization',
            'description': (
                'Token-based authentication using Bearer tokens. '
                'In CI/CD environments, this authentication class '
                'automatically provides mock authentication for '
                'contract testing tools like Schemathesis.'
            )
        }
