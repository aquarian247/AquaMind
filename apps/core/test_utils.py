"""
Utility functions for testing in the AquaMind project.
"""


def get_response_items(response):
    """
    Helper function to get items from a response, handling both paginated and non-paginated responses.
    
    Args:
        response: DRF response object
    
    Returns:
        list: Items from the response
    """
    if isinstance(response.data, list):
        # Non-paginated response
        return response.data
    elif isinstance(response.data, dict) and 'results' in response.data:
        # Paginated response
        return response.data['results']
    else:
        # Something else, return as is
        return response.data


def get_api_url(app_name, endpoint, detail=False, **kwargs):
    """Helper function to construct URLs for API endpoints."""
    # Ensure trailing slashes for consistency with DRF router
    base_url = f'/api/v1/{app_name}/{endpoint}/'
    if detail:
        pk = kwargs.get('pk')
        if pk is None:
            raise ValueError("pk must be provided for detail URLs")
        return f'{base_url}{pk}/'
    return base_url
