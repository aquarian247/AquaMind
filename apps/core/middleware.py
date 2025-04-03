"""
Custom middleware for the AquaMind project.
"""

class UTF8ResponseMiddleware:
    """
    Middleware to ensure all responses have the correct UTF-8 encoding.
    This fixes issues with special characters like 'ø', 'ð', and superscript characters.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        response = self.get_response(request)
        
        # Set the content type to include UTF-8 charset if not already set
        if 'Content-Type' in response and 'charset' not in response['Content-Type']:
            if response['Content-Type'].startswith('text/html'):
                response['Content-Type'] = 'text/html; charset=utf-8'
            elif response['Content-Type'].startswith('application/json'):
                response['Content-Type'] = 'application/json; charset=utf-8'
                
        return response
