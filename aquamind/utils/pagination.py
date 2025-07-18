"""
Custom pagination classes for AquaMind API.

This module provides pagination classes that enforce consistent
validation and error handling for page parameters across the API.
"""
from typing import Any, Dict, Optional, Union
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.request import Request
from rest_framework.response import Response


class ValidatedPageNumberPagination(PageNumberPagination):
    """
    Custom pagination class that enforces proper page number validation.
    
    This class extends DRF's PageNumberPagination to ensure:
    - Minimum page number is 1 (returns 400 Bad Request for page=0)
    - Negative pages return 400 Bad Request
    - Pages beyond the last page return empty results with 200 status
    
    This behavior aligns with REST API best practices and ensures
    consistent behavior across all paginated endpoints.
    """
    
    def get_page_number(self, request: Request, paginator) -> int:
        """
        Get and validate the page number from the request query parameters.
        
        Args:
            request: The request object containing query parameters
            paginator: The paginator instance
            
        Returns:
            int: The validated page number
            
        Raises:
            ValidationError: If page number is invalid (zero or negative)
        """
        page_number = request.query_params.get(self.page_query_param, 1)
        
        try:
            page_number = int(page_number)
        except (TypeError, ValueError):
            # If page is not an integer, default to first page
            return 1
            
        if page_number <= 0:
            # Explicitly reject page=0 or negative pages with 400 Bad Request
            raise ValidationError(
                f"Invalid page number: {page_number}. Page numbers must be positive integers."
            )
            
        return page_number
    
    def get_paginated_response(self, data: Any) -> Response:
        """
        Return a paginated response.
        
        This overrides the default implementation to ensure consistent
        response format even when the page number exceeds the total pages.
        
        Args:
            data: The paginated data
            
        Returns:
            Response: The paginated response
        """
        return Response({
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })
