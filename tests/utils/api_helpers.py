"""
API Testing Helper Utilities

This module provides centralized utilities for API testing across all apps,
standardizing URL construction and common testing patterns.
"""
from django.urls import reverse
from typing import Optional, Dict, Any, Union
from urllib.parse import urlencode


class APITestHelper:
    """
    Helper class for API testing across all apps.
    
    This class centralizes URL construction methods to ensure consistency
    across test modules and simplify test maintenance.
    """
    
    @staticmethod
    def get_api_url(app_name: str, endpoint: str, detail: bool = False, 
                   pk: Optional[Union[int, str]] = None, 
                   query_params: Optional[Dict[str, Any]] = None) -> str:
        """
        Construct a direct URL string for API endpoints.
        
        Args:
            app_name: The name of the app (e.g., 'batch', 'environmental')
            endpoint: The API endpoint name (e.g., 'batches', 'species')
            detail: Whether this is a detail URL (with PK)
            pk: The primary key for detail URLs
            query_params: Optional query parameters to append to the URL
            
        Returns:
            The constructed API URL as a string
            
        Examples:
            >>> APITestHelper.get_api_url('batch', 'batches')
            '/api/v1/batch/batches/'
            >>> APITestHelper.get_api_url('batch', 'batches', detail=True, pk=1)
            '/api/v1/batch/batches/1/'
            >>> APITestHelper.get_api_url('batch', 'batches', query_params={'status': 'active'})
            '/api/v1/batch/batches/?status=active'
        """
        url = f'/api/v1/{app_name}/{endpoint}/'
        
        if detail and pk is not None:
            url = f'/api/v1/{app_name}/{endpoint}/{pk}/'
            
        if query_params:
            url = f"{url}?{urlencode(query_params)}"
            
        return url
    
    @staticmethod
    def get_named_url(viewname: str, kwargs: Optional[Dict[str, Any]] = None, 
                     query_params: Optional[Dict[str, Any]] = None) -> str:
        """
        Construct a URL using Django's reverse function with namespaces.
        
        This method supports the 'api' namespace pattern implemented in the
        API consolidation project.
        
        Args:
            viewname: The URL pattern name (e.g., 'batch-list', 'batch-detail')
            kwargs: URL keyword arguments (e.g., {'pk': 1})
            query_params: Optional query parameters to append to the URL
            
        Returns:
            The reversed URL as a string
            
        Examples:
            >>> APITestHelper.get_named_url('api:batch-list')
            '/api/v1/batch/batches/'
            >>> APITestHelper.get_named_url('api:batch-detail', {'pk': 1})
            '/api/v1/batch/batches/1/'
            >>> APITestHelper.get_named_url('api:batch-list', query_params={'status': 'active'})
            '/api/v1/batch/batches/?status=active'
        """
        url = reverse(viewname, kwargs=kwargs)
        
        if query_params:
            url = f"{url}?{urlencode(query_params)}"
            
        return url
    
    @staticmethod
    def get_action_url(app_name: str, endpoint: str, pk: Union[int, str], 
                      action: str, query_params: Optional[Dict[str, Any]] = None) -> str:
        """
        Construct a URL for a custom action on a viewset.
        
        Args:
            app_name: The name of the app (e.g., 'batch', 'scenario')
            endpoint: The API endpoint name (e.g., 'batches', 'scenarios')
            pk: The primary key for the object
            action: The custom action name (e.g., 'run_projection', 'calculate_aggregates')
            query_params: Optional query parameters to append to the URL
            
        Returns:
            The constructed API URL for the custom action
            
        Examples:
            >>> APITestHelper.get_action_url('scenario', 'scenarios', 1, 'run_projection')
            '/api/v1/scenario/scenarios/1/run_projection/'
        """
        url = f'/api/v1/{app_name}/{endpoint}/{pk}/{action}/'
        
        if query_params:
            url = f"{url}?{urlencode(query_params)}"
            
        return url
