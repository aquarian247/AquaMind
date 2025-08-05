#!/usr/bin/env python
"""
URL Pattern Lister for Django

This script lists all URLs registered in a Django application,
including nested patterns from includes. It also identifies
duplicate URL patterns that could cause conflicts.
"""
import os
import sys
import re
from collections import defaultdict

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
import django
django.setup()

from django.urls import URLPattern, URLResolver
from django.urls.resolvers import RegexPattern, RoutePattern
from django.core.management import BaseCommand
from django.urls import get_resolver


def get_pattern_string(pattern):
    """Extract the pattern string from different pattern types."""
    if isinstance(pattern, RegexPattern):
        return pattern._regex
    elif isinstance(pattern, RoutePattern):
        return pattern._route
    else:
        return str(pattern)


def get_all_urls(urlpatterns, prefix='', namespace=None):
    """
    Recursively extract all URL patterns, including those from includes.
    
    Args:
        urlpatterns: The URL patterns to process
        prefix: URL prefix for nested patterns
        namespace: Current namespace
        
    Returns:
        List of (pattern, name, namespace) tuples
    """
    all_urls = []
    
    for pattern in urlpatterns:
        if isinstance(pattern, URLPattern):
            # Handle URL patterns
            pattern_str = get_pattern_string(pattern.pattern)
            url = prefix + pattern_str
            name = pattern.name or ''
            full_name = f"{namespace}:{name}" if namespace and name else name
            all_urls.append((url, full_name, namespace))
            
        elif isinstance(pattern, URLResolver):
            # Handle URL resolvers (includes)
            pattern_str = get_pattern_string(pattern.pattern)
            new_prefix = prefix + pattern_str
            
            # Handle namespace
            new_namespace = namespace
            if pattern.namespace:
                new_namespace = f"{namespace}:{pattern.namespace}" if namespace else pattern.namespace
            
            # Recursively process included patterns
            all_urls.extend(get_all_urls(pattern.url_patterns, new_prefix, new_namespace))
    
    return all_urls


def find_duplicates(urls):
    """Find duplicate URL patterns."""
    url_map = defaultdict(list)
    for url, name, namespace in urls:
        # Normalize URL pattern for comparison (remove named groups)
        normalized_url = re.sub(r'\(\?P<[^>]+>.*?\)', '(.*?)', url)
        url_map[normalized_url].append((url, name, namespace))
    
    # Filter to only patterns that appear more than once
    duplicates = {url: patterns for url, patterns in url_map.items() if len(patterns) > 1}
    return duplicates


def main():
    """Main function to list all URLs and find duplicates."""
    resolver = get_resolver()
    all_urls = get_all_urls(resolver.url_patterns)
    
    # Print all URLs
    print("\n=== All URL Patterns ===")
    print(f"{'URL Pattern':<60} {'URL Name':<30} {'Namespace'}")
    print("-" * 100)
    
    for url, name, namespace in sorted(all_urls, key=lambda x: x[0]):
        print(f"{url:<60} {name:<30} {namespace or '-'}")
    
    # Find and print duplicates
    duplicates = find_duplicates(all_urls)
    
    if duplicates:
        print("\n=== Duplicate URL Patterns ===")
        for norm_url, patterns in duplicates.items():
            print(f"\nDuplicate pattern: {norm_url}")
            for url, name, namespace in patterns:
                print(f"  - {url:<60} {name:<30} {namespace or '-'}")
    else:
        print("\nNo duplicate URL patterns found.")
    
    # Print summary
    print(f"\nTotal URL patterns: {len(all_urls)}")
    print(f"Duplicate patterns: {len(duplicates)}")


if __name__ == "__main__":
    main()
