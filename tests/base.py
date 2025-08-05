"""
Base Test Classes for AquaMind API Testing

This module provides base test classes that can be extended by
all apps to ensure consistent testing patterns across the project.
"""
from typing import Optional, Dict, Any, Union
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.test import APITestCase, APIClient

from tests.utils.api_helpers import APITestHelper

User = get_user_model()


class BaseAPITestCase(APITestCase):
    """
    Base test case for API tests across all apps.
    
    This class provides common setup, authentication, and utility methods
    to standardize API testing across the project. It integrates with
    APITestHelper for URL construction.
    
    Example usage:
        class BatchAPITest(BaseAPITestCase):
            def setUp(self):
                super().setUp()
                # Additional setup specific to BatchAPITest
                
            def test_list_batches(self):
                url = self.get_api_url('batch', 'batches')
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
    """
    
    def setUp(self):
        """
        Set up test data and authenticate the test client.
        
        Creates a test user and authenticates the client with that user.
        Override this method in subclasses to add additional setup,
        but be sure to call super().setUp() first.
        """
        self.client = APIClient()
        self.user = self._create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            is_staff=False,
            is_superuser=False
        )
        self.client.force_authenticate(user=self.user)
        
    def _create_user(self, username: str, email: str, password: str, 
                    is_staff: bool = False, is_superuser: bool = False) -> User:
        """
        Create a user for testing purposes.
        
        Args:
            username: The username for the test user
            email: The email for the test user
            password: The password for the test user
            is_staff: Whether the user should be a staff user
            is_superuser: Whether the user should be a superuser
            
        Returns:
            The created User instance
        """
        return User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_staff=is_staff,
            is_superuser=is_superuser
        )
    
    def create_and_authenticate_superuser(self, username: str = 'admin', 
                                         email: str = 'admin@example.com',
                                         password: str = 'adminpass123') -> User:
        """
        Create a superuser and authenticate the client with that user.
        
        Args:
            username: The username for the superuser
            email: The email for the superuser
            password: The password for the superuser
            
        Returns:
            The created superuser instance
        """
        superuser = self._create_user(
            username=username,
            email=email,
            password=password,
            is_staff=True,
            is_superuser=True
        )
        self.client.force_authenticate(user=superuser)
        return superuser
    
    def get_api_url(self, app_name: str, endpoint: str, detail: bool = False, 
                   pk: Optional[Union[int, str]] = None,
                   query_params: Optional[Dict[str, Any]] = None) -> str:
        """
        Get an API URL using the APITestHelper.
        
        This is a convenience method that delegates to APITestHelper.get_api_url.
        
        Args:
            app_name: The name of the app (e.g., 'batch', 'environmental')
            endpoint: The API endpoint name (e.g., 'batches', 'species')
            detail: Whether this is a detail URL (with PK)
            pk: The primary key for detail URLs
            query_params: Optional query parameters to append to the URL
            
        Returns:
            The constructed API URL as a string
        """
        return APITestHelper.get_api_url(
            app_name=app_name,
            endpoint=endpoint,
            detail=detail,
            pk=pk,
            query_params=query_params
        )
    
    def get_named_url(self, viewname: str, kwargs: Optional[Dict[str, Any]] = None,
                     query_params: Optional[Dict[str, Any]] = None) -> str:
        """
        Get a URL using Django's reverse function with namespaces.
        
        This is a convenience method that delegates to APITestHelper.get_named_url.
        
        Args:
            viewname: The URL pattern name (e.g., 'api:batch-list')
            kwargs: URL keyword arguments (e.g., {'pk': 1})
            query_params: Optional query parameters to append to the URL
            
        Returns:
            The reversed URL as a string
        """
        return APITestHelper.get_named_url(
            viewname=viewname,
            kwargs=kwargs,
            query_params=query_params
        )
    
    def get_action_url(self, app_name: str, endpoint: str, pk: Union[int, str],
                      action: str, query_params: Optional[Dict[str, Any]] = None) -> str:
        """
        Get a URL for a custom action on a viewset.
        
        This is a convenience method that delegates to APITestHelper.get_action_url.
        
        Args:
            app_name: The name of the app (e.g., 'batch', 'scenario')
            endpoint: The API endpoint name (e.g., 'batches', 'scenarios')
            pk: The primary key for the object
            action: The custom action name (e.g., 'run_projection')
            query_params: Optional query parameters to append to the URL
            
        Returns:
            The constructed API URL for the custom action
        """
        return APITestHelper.get_action_url(
            app_name=app_name,
            endpoint=endpoint,
            pk=pk,
            action=action,
            query_params=query_params
        )
    
    @staticmethod
    def run_in_transaction(func):
        """
        Decorator to run a test method in a transaction.
        
        This ensures that database changes made during the test are rolled back,
        which helps prevent test isolation issues.
        
        Example usage:
            @BaseAPITestCase.run_in_transaction
            def test_create_batch(self):
                # This test will run in a transaction
                # and changes will be rolled back after the test
        """
        def wrapper(*args, **kwargs):
            with transaction.atomic():
                return func(*args, **kwargs)
        return wrapper
