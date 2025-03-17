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
