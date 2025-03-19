"""
Helper functions for API tests in the batch application.
"""

def get_api_url(app_name, endpoint, detail=False, **kwargs):
    """
    Helper function to construct URLs for API endpoints.
    
    Args:
        app_name (str): The name of the app (e.g., 'batch', 'infrastructure')
        endpoint (str): The API endpoint name (e.g., 'batches', 'species')
        detail (bool): Whether this is a detail URL (with PK)
        **kwargs: Additional URL parameters, primarily 'pk' for detail URLs
    
    Returns:
        str: The constructed API URL
    """
    if detail:
        pk = kwargs.get('pk')
        return f'/api/v1/{app_name}/{endpoint}/{pk}/'
    return f'/api/v1/{app_name}/{endpoint}/'
