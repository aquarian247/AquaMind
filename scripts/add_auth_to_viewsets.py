#!/usr/bin/env python
"""
Script to add explicit authentication classes to all ViewSet classes across the codebase.
This prevents SessionAuthentication fallback in Schemathesis tests.

Usage:
    python scripts/add_auth_to_viewsets.py

The script will:
1. Find all files containing ViewSet classes
2. Add authentication_classes and permission_classes to each ViewSet
3. Add necessary imports if not already present
4. Skip ViewSets that already have these attributes
"""

import os
import re
import sys
from pathlib import Path

# Regular expressions for finding ViewSets and imports
VIEWSET_PATTERN = re.compile(r'class\s+(\w+)(?:\(.*?(?:ModelViewSet|ViewSet).*?\))', re.DOTALL)
DOCSTRING_PATTERN = re.compile(r'""".*?"""', re.DOTALL)
AUTH_CLASS_PATTERN = re.compile(r'authentication_classes\s*=')
PERM_CLASS_PATTERN = re.compile(r'permission_classes\s*=')

# Import statements to add
IMPORT_STATEMENTS = [
    "from rest_framework.authentication import TokenAuthentication",
    "from rest_framework_simplejwt.authentication import JWTAuthentication",
    "from rest_framework.permissions import IsAuthenticated"
]

# Authentication class code to add
AUTH_CODE = """
    # Explicitly override authentication to prevent SessionAuthentication fallback
    authentication_classes = [TokenAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]
"""

def check_imports(file_content):
    """Check if the necessary imports are already in the file content."""
    missing_imports = []
    for import_stmt in IMPORT_STATEMENTS:
        if import_stmt not in file_content:
            missing_imports.append(import_stmt)
    return missing_imports

def add_imports(file_content, missing_imports):
    """Add missing imports to the file content."""
    if not missing_imports:
        return file_content
    
    # Only consider TOP-LEVEL imports (no leading indentation); this prevents
    # inserting new imports inside a method that already contains a local
    # `import` statement which broke the batch viewsets previously.
    import_lines = [
        i
        for i, line in enumerate(file_content.split("\n"))
        if (line.startswith("import ") or line.startswith("from "))
    ]
    
    if not import_lines:
        # If no imports found, add at the beginning
        lines = file_content.split('\n')
        for i, import_stmt in enumerate(missing_imports):
            lines.insert(i, import_stmt)
        return '\n'.join(lines)
    
    # Add after the last import
    last_import_line = max(import_lines)
    lines = file_content.split('\n')
    for i, import_stmt in enumerate(missing_imports):
        lines.insert(last_import_line + 1 + i, import_stmt)
    return '\n'.join(lines)

def add_auth_to_viewset(file_content, class_match):
    """Add authentication classes to a ViewSet class if not already present."""
    class_name = class_match.group(1)

    # Early-out if auth already present in this class body
    class_start_pos = class_match.start()
    class_body_slice = file_content[class_start_pos:]
    next_class_match = re.search(r"^\s*class\s+\w+", class_body_slice, re.MULTILINE)
    if next_class_match:
        class_body_slice = class_body_slice[: next_class_match.start()]
    if AUTH_CLASS_PATTERN.search(class_body_slice) and PERM_CLASS_PATTERN.search(
        class_body_slice
    ):
        print(f"    - {class_name} already has authentication classes")
        return file_content

    # Split whole file into individual lines for easier manipulation
    lines = file_content.splitlines(keepends=True)

    # Locate the header line index of this class
    header_abs_index = None
    collected = 0
    for idx, line in enumerate(lines):
        collected += len(line)
        if collected > class_start_pos:
            header_abs_index = idx
            break

    if header_abs_index is None:
        return file_content  # Should not happen

    # Determine insertion index just after possible class docstring
    insert_idx = header_abs_index + 1
    # Skip any immediately blank lines
    while insert_idx < len(lines) and lines[insert_idx].strip() == "":
        insert_idx += 1

    # If we have a docstring immediately after header, skip it
    if (
        insert_idx < len(lines)
        and lines[insert_idx].lstrip().startswith('"""')
    ):
        # Find closing triple quotes
        while (
            insert_idx < len(lines)
            and '"""' not in lines[insert_idx].rstrip().rstrip()
            or lines[insert_idx].rstrip().count('"""') == 1
        ):
            insert_idx += 1
        # Move past the closing docstring line
        insert_idx += 1

    # Build auth block with correct indentation (4 spaces)
    indent = " " * 4
    auth_block = (
        f"{indent}# Explicitly override authentication to prevent "
        "SessionAuthentication fallback\n"
        f"{indent}authentication_classes = "
        "[TokenAuthentication, JWTAuthentication]\n"
        f"{indent}permission_classes = [IsAuthenticated]\n\n"
    )

    lines.insert(insert_idx, auth_block)
    print(f"    - Added auth classes to {class_name}")
    return "".join(lines)

def process_file(file_path):
    """Process a single file to add authentication classes to ViewSets."""
    print(f"Processing {file_path}...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Find all ViewSet classes in the file
    viewset_matches = list(VIEWSET_PATTERN.finditer(content))
    if not viewset_matches:
        print("  No ViewSet classes found")
        return
    
    # Check and add missing imports
    missing_imports = check_imports(content)
    if missing_imports:
        content = add_imports(content, missing_imports)
        print(f"  Added missing imports: {', '.join(missing_imports)}")
    
    # Add authentication classes to each ViewSet
    for match in reversed(viewset_matches):  # Process in reverse to maintain positions
        content = add_auth_to_viewset(content, match)
    
    # Write changes back to file if content changed
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  Updated {file_path}")
    else:
        print(f"  No changes needed for {file_path}")

def find_viewset_files():
    """Find all files that might contain ViewSet classes."""
    viewset_files = []
    apps_dir = Path('apps')
    
    if not apps_dir.exists():
        print("Error: 'apps' directory not found. Make sure you're running this from the project root.")
        sys.exit(1)
    
    for app_dir in apps_dir.iterdir():
        if not app_dir.is_dir() or app_dir.name.startswith('__'):
            continue
            
        # Check common locations for viewsets
        api_dir = app_dir / 'api'
        if api_dir.exists():
            # Check for viewsets.py
            viewsets_file = api_dir / 'viewsets.py'
            if viewsets_file.exists():
                viewset_files.append(viewsets_file)
            
            # Check for viewsets directory
            viewsets_dir = api_dir / 'viewsets'
            if viewsets_dir.exists() and viewsets_dir.is_dir():
                for file in viewsets_dir.glob('*.py'):
                    if not file.name.startswith('__'):
                        viewset_files.append(file)
        
        # Also check for views.py which might contain viewsets
        views_file = app_dir / 'views.py'
        if views_file.exists():
            viewset_files.append(views_file)
            
        # Check for api/views.py which might contain viewsets
        if api_dir.exists():
            api_views_file = api_dir / 'views.py'
            if api_views_file.exists():
                viewset_files.append(api_views_file)
    
    return viewset_files

def main():
    """Main function to process all ViewSet files."""
    print("Starting authentication classes update for ViewSets...")
    
    viewset_files = find_viewset_files()
    print(f"Found {len(viewset_files)} potential ViewSet files")
    
    for file_path in viewset_files:
        process_file(file_path)
    
    print("Finished processing all files")

if __name__ == "__main__":
    main()
