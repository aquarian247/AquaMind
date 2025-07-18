#!/usr/bin/env python
"""
Script to fix syntax errors in viewset files caused by misplaced authentication class declarations.

This script:
1. Reads each file with syntax errors
2. Removes incorrectly placed authentication_classes and permission_classes declarations
3. Saves the cleaned files

After running this script, you should re-run add_auth_to_viewsets.py to properly add authentication.

Usage:
    python scripts/fix_auth_syntax.py
"""

import os
import re
import sys
from pathlib import Path

# Patterns to identify misplaced authentication declarations
AUTH_CLASS_PATTERN = re.compile(r'^\s*authentication_classes\s*=\s*\[.*?\]', re.MULTILINE)
PERM_CLASS_PATTERN = re.compile(r'^\s*permission_classes\s*=\s*\[.*?\]', re.MULTILINE)
AUTH_COMMENT_PATTERN = re.compile(r'^\s*#\s*Explicitly override authentication.*$', re.MULTILINE)

# Pattern to identify import statements
IMPORT_PATTERN = re.compile(r'^(?:from|import)\s+.*$', re.MULTILINE)

def fix_file(file_path):
    """Fix syntax errors in a single file."""
    print(f"Processing {file_path}...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Check for authentication classes in import section
    import_section_end = 0
    import_matches = list(IMPORT_PATTERN.finditer(content))
    
    if import_matches:
        # Find where the import section ends (last import + 1 line)
        last_import = import_matches[-1]
        import_section_end = content.find('\n', last_import.end()) + 1
        
        # Check if there are authentication classes in the import section
        import_section = content[:import_section_end]
        if AUTH_CLASS_PATTERN.search(import_section) or PERM_CLASS_PATTERN.search(import_section):
            # Remove auth classes from import section
            lines = import_section.split('\n')
            cleaned_lines = []
            skip_next = False
            
            for line in lines:
                if skip_next:
                    skip_next = False
                    continue
                    
                if re.match(r'\s*#\s*Explicitly override authentication', line):
                    skip_next = True  # Skip the next line (authentication_classes)
                    continue
                    
                if re.match(r'\s*authentication_classes\s*=', line) or re.match(r'\s*permission_classes\s*=', line):
                    continue
                    
                cleaned_lines.append(line)
            
            # Replace the import section
            content = '\n'.join(cleaned_lines) + content[import_section_end:]
    
    # Fix indentation issues - remove any authentication classes with unexpected indentation
    class_pattern = re.compile(r'class\s+\w+\(.*?\):', re.DOTALL)
    class_matches = list(class_pattern.finditer(content))
    
    for i, class_match in enumerate(class_matches):
        class_start = class_match.start()
        
        # Determine where this class ends
        next_class_start = len(content)
        if i < len(class_matches) - 1:
            next_class_start = class_matches[i + 1].start()
        
        class_content = content[class_start:next_class_start]
        
        # Find all authentication declarations in this class
        auth_matches = list(AUTH_CLASS_PATTERN.finditer(class_content))
        perm_matches = list(PERM_CLASS_PATTERN.finditer(class_content))
        comment_matches = list(AUTH_COMMENT_PATTERN.finditer(class_content))
        
        # Keep only the first occurrence of each if there are duplicates
        if len(auth_matches) > 1 or len(perm_matches) > 1:
            # Split into lines for easier processing
            lines = class_content.split('\n')
            cleaned_lines = []
            
            # Track if we've seen auth declarations
            seen_auth = False
            seen_perm = False
            skip_next = False
            
            for line in lines:
                if skip_next:
                    skip_next = False
                    continue
                    
                if re.match(r'\s*#\s*Explicitly override authentication', line):
                    if not seen_auth:
                        cleaned_lines.append(line)
                        seen_auth = True
                    else:
                        skip_next = True  # Skip the next line (authentication_classes)
                    continue
                    
                if re.match(r'\s*authentication_classes\s*=', line):
                    if not seen_auth:
                        cleaned_lines.append(line)
                        seen_auth = True
                    continue
                    
                if re.match(r'\s*permission_classes\s*=', line):
                    if not seen_perm:
                        cleaned_lines.append(line)
                        seen_perm = True
                    continue
                    
                cleaned_lines.append(line)
            
            # Replace the class content
            content = content[:class_start] + '\n'.join(cleaned_lines) + content[next_class_start:]
    
    # Check for any remaining incorrectly indented authentication classes
    lines = content.split('\n')
    cleaned_lines = []
    in_class = False
    class_indent = 0
    
    for line in lines:
        # Track when we enter/exit a class definition
        if re.match(r'^class\s+\w+\(.*?\):', line):
            in_class = True
            class_indent = len(line) - len(line.lstrip())
            cleaned_lines.append(line)
            continue
            
        # Skip incorrectly indented authentication lines
        if in_class:
            line_indent = len(line) - len(line.lstrip())
            
            # If we've moved to a new class or module level
            if line and line_indent <= class_indent and not line.isspace():
                in_class = False
            
            # Check for misplaced auth lines with wrong indentation
            if re.match(r'\s*authentication_classes\s*=', line) or re.match(r'\s*permission_classes\s*=', line):
                expected_indent = class_indent + 4  # Standard indentation is 4 spaces
                
                # If indentation is wrong, skip this line
                if line_indent != expected_indent:
                    continue
        
        cleaned_lines.append(line)
    
    content = '\n'.join(cleaned_lines)
    
    # Write changes back to file if content changed
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  Fixed {file_path}")
    else:
        print(f"  No changes needed for {file_path}")

def find_viewset_files():
    """Find all viewset files that might have syntax errors."""
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
    """Main function to process all viewset files."""
    print("Starting syntax error fixes for ViewSet files...")
    
    viewset_files = find_viewset_files()
    print(f"Found {len(viewset_files)} potential ViewSet files")
    
    for file_path in viewset_files:
        fix_file(file_path)
    
    print("\nFinished processing all files")
    print("\nNow you should run the add_auth_to_viewsets.py script again to properly add authentication.")

if __name__ == "__main__":
    main()
