#!/usr/bin/env python
"""
CI Test Token Generator

This script creates a test user and generates an authentication token for use in CI environments,
particularly for Schemathesis API contract testing that requires authenticated requests.

Usage:
    python scripts/ci/create_test_token.py [--server-url=http://127.0.0.1:8000]

The script will print only the token key to stdout, allowing it to be captured in CI:
    TOKEN=$(python scripts/ci/create_test_token.py)

Requirements:
    - Requires the requests library
    - Django server must be running and accessible
    - Default server URL: http://127.0.0.1:8000
"""

import sys
import argparse
import requests
from requests.exceptions import RequestException


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Create CI test user and get auth token')
    parser.add_argument('--server-url', default='http://127.0.0.1:8000',
                        help='URL of the running Django server (default: http://127.0.0.1:8000)')
    return parser.parse_args()


def get_auth_token(server_url):
    """Get authentication token for the test user."""
    # CI test user credentials
    username = "schemathesis_ci"
    password = "testpass123"
    
    # Try the token auth endpoint
    try:
        # Primary token endpoint used by AquaMind backend
        response = requests.post(
            f"{server_url}/api/v1/users/token/",
            json={
                "username": username,
                "password": password
            }
        )
        
        if response.status_code == 200:
            return response.json().get("token")
        
        # If that fails, try the DRF auth token endpoint
        response = requests.post(
            f"{server_url}/api/v1/auth-token/",
            json={
                "username": username,
                "password": password
            }
        )
        
        if response.status_code == 200:
            return response.json().get("token")
            
        # If that fails too, try the login endpoint which might return a token
        response = requests.post(
            f"{server_url}/api/v1/users/login/",
            json={
                "username": username,
                "password": password
            }
        )
        
        if response.status_code == 200 and "token" in response.json():
            return response.json().get("token")
            
        # If all token endpoints fail, try a simple login and check if we can extract token from cookies
        response = requests.post(
            f"{server_url}/api/v1/login/",
            json={
                "username": username,
                "password": password
            }
        )
        
        # Last resort - try to create a token via the admin API
        response = requests.post(
            f"{server_url}/api/v1/admin/tokens/",
            json={
                "username": username
            }
        )
        
        if response.status_code == 201:
            return response.json().get("key")
            
        print(f"Error getting token: No working token endpoint found", file=sys.stderr)
        return None
        
    except RequestException as e:
        print(f"Network error getting token: {e}", file=sys.stderr)
        return None


def create_test_user_and_token():
    """Create a test user and generate an authentication token via HTTP API."""
    args = parse_arguments()
    server_url = args.server_url.rstrip('/')

    # Get token for the pre-created CI user (migrations ensure user exists)
    token = get_auth_token(server_url)
    
    if token:
        # Print only the token key (for capture in CI)
        print(token, end='')
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(create_test_user_and_token())
