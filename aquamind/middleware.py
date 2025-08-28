"""
TEMPORARY DEBUGGING MIDDLEWARE – API Authentication Diagnostics.

This middleware logs Authorization headers for every request to help debug
authentication issues during API testing and development.
This is TEMPORARY CODE and should be removed after debugging is complete.

Usage:
1. Add to MIDDLEWARE in settings_ci.py:
   MIDDLEWARE = [
       ...
       'aquamind.middleware.AuthHeaderDebugMiddleware',
       ...
   ]
2. Run API tests to capture header information
3. Check console output or log file for missing/malformed headers

Created: July 18, 2025
Updated: August 2025 (removed Schemathesis-specific references)
"""

import logging
import sys
import time
from datetime import datetime
from django.conf import settings

# Configure logger
logger = logging.getLogger('auth_header_debug')
logger.setLevel(logging.DEBUG)

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
console_formatter = logging.Formatter('AUTH_DEBUG: [%(asctime)s] %(message)s')
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

# File handler (optional, enabled in CI)
if getattr(settings, 'AUTH_DEBUG_LOG_FILE', None):
    file_handler = logging.FileHandler(settings.AUTH_DEBUG_LOG_FILE)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter('[%(asctime)s] %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)


class AuthHeaderDebugMiddleware:
    """
    Temporary middleware to log Authorization headers for debugging API authentication.

    This middleware logs every request's path, method, timestamp, and Authorization header
    to help identify authentication issues during API testing and development.
    """
    
    def __init__(self, get_response):
        """Initialize middleware with the get_response callable."""
        self.get_response = get_response
        # Log middleware initialization
        logger.info("=== AUTH HEADER DEBUG MIDDLEWARE INITIALIZED (TEMPORARY) ===")
        
    def __call__(self, request):
        """Process each request to log authentication headers."""
        # Get timestamp at the start of the request
        timestamp = datetime.now().isoformat()
        
        # Extract request details
        path = request.path
        method = request.method
        
        # Extract Authorization header (safely handle if missing)
        auth_header = request.META.get('HTTP_AUTHORIZATION', 'MISSING')
        
        # Mask token value if present (show only first/last 4 chars)
        if auth_header.startswith('Token ') and len(auth_header) > 10:
            token = auth_header[6:]  # Remove 'Token ' prefix
            if len(token) > 8:
                masked_token = f"{token[:4]}...{token[-4:]}"
                masked_auth = f"Token {masked_token}"
            else:
                masked_auth = auth_header
        else:
            masked_auth = auth_header
            
        # Log the request details
        logger.info(f"PATH: {path} | METHOD: {method} | AUTH: {masked_auth}")
        
        # Additional debug info for specific endpoints that might be failing
        if 'batch' in path or 'auth' in path:
            logger.debug(f"DETAILED REQUEST INFO - PATH: {path}")
            logger.debug(f"CONTENT_TYPE: {request.META.get('CONTENT_TYPE', 'MISSING')}")
            logger.debug(f"QUERY_STRING: {request.META.get('QUERY_STRING', 'EMPTY')}")
        
        # Process the request normally
        response = self.get_response(request)
        
        # Optionally log response status for debugging
        logger.debug(f"RESPONSE: {path} | STATUS: {response.status_code}")
        
        return response
