#!/usr/bin/env python
"""
Debug script to explore available API URLs in the Django test environment.
"""
import os
import sys
import json

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'test_settings')

import django
django.setup()

from django.urls import get_resolver
from django.test import Client
from rest_framework.test import APIClient

# Try to detect the API root URL
api_client = APIClient()
client = Client()

# Check if API root is accessible
response = client.get('/api/')
print(f"API Root (/api/): {response.status_code}")

# Try different potential API roots
for path in [
    '/api/environmental/',
    '/api/infrastructure/',
    '/environmental/',
    '/infrastructure/',
    '/api/v1/environmental/',
    '/api/'
]:
    response = client.get(path)
    print(f"{path}: {response.status_code}")
    if response.status_code == 200:
        print(f"Content: {response.content[:500]}...")

# Try the specific endpoint patterns we're using in tests
for path in [
    '/api/environmental/weather/',
    '/environmental/weather/',
    '/api/weather/'
]:
    response = client.get(path)
    print(f"Weather endpoint {path}: {response.status_code}")

if __name__ == "__main__":
    print("Exploring API endpoints in the test environment:")
    print("-" * 40)
