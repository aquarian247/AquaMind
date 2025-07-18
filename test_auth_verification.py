#!/usr/bin/env python
"""
Test script to verify authentication is working properly for batch endpoints.

This script makes requests to batch endpoints with and without authentication
to verify that authentication is properly enforced.
"""
import os
import sys
import django
from django.contrib.auth import get_user_model
from django.core.management import call_command

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings_ci')
django.setup()

# Now we can import models after Django is set up
from rest_framework.authtoken.models import Token


def test_authentication():
    """Test authentication on batch endpoints."""
    # Import REST framework utilities **after** Django has been configured to
    # avoid ImproperlyConfigured errors during settings access at import time.
    from rest_framework.test import APIClient
    from rest_framework import status

    print("Testing authentication on batch endpoints...")
    
    # Create a test client
    client = APIClient()
    
    # 1. Make a request WITHOUT authentication
    print("\n1. Testing request WITHOUT authentication:")
    response = client.get('/api/v1/batch/batches/')
    print(f"Response status: {response.status_code}")
    
    # Verify it returns 401 Unauthorized
    assert response.status_code == status.HTTP_401_UNAUTHORIZED, \
        f"Expected 401 Unauthorized, got {response.status_code}"
    print("✅ Authentication check passed: Received 401 Unauthorized as expected")
    
    # 2. Create a user and authenticate
    print("\n2. Testing request WITH authentication:")
    User = get_user_model()
    username = 'testuser'
    password = 'testpassword'
    
    # Create user if it doesn't exist
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        user = User.objects.create_user(username=username, password=password)
    
    # Get or create token
    token, _ = Token.objects.get_or_create(user=user)
    print(f"Created/retrieved token: {token.key}")
    
    # Authenticate the client
    client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
    
    # Make an authenticated request
    response = client.get('/api/v1/batch/batches/')
    print(f"Response status: {response.status_code}")
    
    # Verify it returns 200 OK or appropriate success code
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED], \
        f"Expected 200 OK or 201 Created, got {response.status_code}"
    print("✅ Authentication check passed: Received successful response with authentication")
    
    # 3. Test another endpoint to be thorough
    print("\n3. Testing another endpoint WITH authentication:")
    response = client.get('/api/v1/batch/container-assignments/')
    print(f"Response status: {response.status_code}")
    
    # Verify it returns 200 OK
    assert response.status_code == status.HTTP_200_OK, \
        f"Expected 200 OK, got {response.status_code}"
    print("✅ Authentication check passed: Received 200 OK for container-assignments endpoint")
    
    print("\nAll authentication tests passed! ✅")


if __name__ == "__main__":
    test_authentication()
