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
import argparse

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


def detailed_report(all_urls, duplicates):
    """Print the existing verbose report."""
    # Print all URLs
    print("\n=== All URL Patterns ===")
    print(f"{'URL Pattern':<60} {'URL Name':<30} {'Namespace'}")
    print("-" * 100)
    for url, name, namespace in sorted(all_urls, key=lambda x: x[0]):
        print(f"{url:<60} {name:<30} {namespace or '-'}")

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


def _infer_app_from_url(url: str) -> str:
    """
    Attempt to infer the app name from a URL pattern.
    Heuristic: take the first non-empty segment after optional leading slash
    and optional 'api' or 'api/v1'.
    """
    parts = [p for p in url.split('/') if p]  # filter empties
    if not parts:
        return 'root'
    if parts[0] == 'api':
        # Strip version if present
        if len(parts) > 1 and re.match(r'v[0-9]+', parts[1]):
            return parts[2] if len(parts) > 2 else 'api'
        return parts[1] if len(parts) > 1 else 'api'
    return parts[0]


def summary_report(all_urls, duplicates):
    """Print condensed duplicate statistics."""
    print("=== URL Pattern Summary ===")
    print(f"Total URL patterns : {len(all_urls)}")
    print(f"Duplicate patterns : {len(duplicates)}")

    if not duplicates:
        print("No duplicate URL patterns detected.")
        return

    # List duplicate patterns only once
    print("\nDuplicate pattern list:")
    for pattern in sorted(duplicates.keys()):
        print(f" - {pattern}")

    # Group duplicates by inferred app
    dup_by_app = defaultdict(int)
    for norm_url in duplicates.keys():
        app = _infer_app_from_url(norm_url)
        dup_by_app[app] += 1

    print("\nDuplicate pattern count by app:")
    for app, count in sorted(dup_by_app.items(), key=lambda x: x[0]):
        print(f" {app:<20} : {count}")


def main():
    """Entry point. Parses args & shows requested report."""
    parser = argparse.ArgumentParser(
        description="List Django URL patterns and identify duplicates."
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Show only summary information about duplicates.",
    )
    args = parser.parse_args()

    resolver = get_resolver()
    all_urls = get_all_urls(resolver.url_patterns)
    duplicates = find_duplicates(all_urls)

    if args.summary:
        summary_report(all_urls, duplicates)
    else:
        detailed_report(all_urls, duplicates)


if __name__ == "__main__":
    main()
