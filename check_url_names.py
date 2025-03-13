#!/usr/bin/env python
"""
Script to check available URL names in the Django project.
"""
import os
import sys

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'test_settings')

import django
django.setup()

from django.urls import get_resolver, URLPattern, URLResolver


def print_all_url_names(resolver=None, prefix=''):
    """Print all URL pattern names in the resolver."""
    if resolver is None:
        resolver = get_resolver()
    
    for pattern in resolver.url_patterns:
        if isinstance(pattern, URLPattern):
            name = pattern.name
            if name:
                print(f"{prefix}{name}")
        elif isinstance(pattern, URLResolver):
            namespace = prefix
            if pattern.namespace:
                namespace = f"{prefix}{pattern.namespace}:"
            print_all_url_names(pattern, namespace)


if __name__ == "__main__":
    print("Available URL names in the project:")
    print("-" * 40)
    print_all_url_names()
