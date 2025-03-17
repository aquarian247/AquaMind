#!/usr/bin/env python3
"""
Script to update all infrastructure test files to use the get_response_items helper function.
"""
import os
import re

def update_file(file_path):
    """Update a test file to use the get_response_items helper function."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Add import if it doesn't exist
    if 'from apps.core.test_utils import get_response_items' not in content:
        content = re.sub(
            r'from rest_framework.test import APITestCase',
            'from rest_framework.test import APITestCase\nfrom apps.core.test_utils import get_response_items',
            content
        )
    
    # Replace all instances of response.data['results'] access
    content = re.sub(
        r'(\s+for\s+item\s+in\s+)response\.data\[\'results\'\]',
        r'\1get_response_items(response)',
        content
    )
    
    # Update the file
    with open(file_path, 'w') as f:
        f.write(content)
    
    print(f"Updated {file_path}")

def main():
    """Main function."""
    # Directory containing test files
    test_dir = 'apps/infrastructure/tests/test_api'
    
    # Find all Python test files
    for file_name in os.listdir(test_dir):
        if file_name.endswith('.py') and file_name.startswith('test_'):
            file_path = os.path.join(test_dir, file_name)
            update_file(file_path)

if __name__ == '__main__':
    main()
