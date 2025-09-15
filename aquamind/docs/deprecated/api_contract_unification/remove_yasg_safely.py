#!/usr/bin/env python
"""
remove_yasg_safely.py - A script to safely remove yasg decorators using regex.

This script:
1. Removes @swagger_auto_schema decorators and their complete arguments
2. Removes drf_yasg imports
3. Uses regex to handle multi-line decorators
4. Preserves original indentation and formatting
5. Creates backups before modifying
6. Is conservative - only removes what we're certain is yasg-related
"""
import os
import re
import argparse
import shutil
from pathlib import Path
import sys

# Regex patterns
YASG_IMPORT_PATTERN = re.compile(r'^\s*from\s+drf_yasg.*import.*$|^\s*import\s+drf_yasg.*$', re.MULTILINE)

# This pattern matches @swagger_auto_schema decorators, including multi-line ones
# It uses a non-greedy approach to match the entire decorator
SWAGGER_DECORATOR_PATTERN = re.compile(
    r'^\s*@swagger_auto_schema\s*\(.*?\)\s*$',
    re.MULTILINE | re.DOTALL
)

def count_parentheses(text):
    """Count opening and closing parentheses to ensure proper matching."""
    open_count = text.count('(')
    close_count = text.count(')')
    return open_count, close_count

def find_decorator_end(lines, start_idx):
    """Find the end of a multi-line decorator starting at start_idx."""
    combined_text = lines[start_idx]
    open_count, close_count = count_parentheses(combined_text)
    
    current_idx = start_idx
    while open_count > close_count and current_idx < len(lines) - 1:
        current_idx += 1
        line = lines[current_idx]
        combined_text += line
        new_open, new_close = count_parentheses(line)
        open_count += new_open
        close_count += new_close
    
    return current_idx

def remove_yasg_from_file(file_path, dry_run=True, verbose=False):
    """
    Remove yasg imports and decorators from a file.
    
    Args:
        file_path: Path to the file
        dry_run: If True, only show what would be changed without modifying the file
        verbose: If True, print detailed information
    
    Returns:
        Tuple of (imports_removed, decorators_removed, modified_content)
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if file contains yasg imports or decorators
    if 'drf_yasg' not in content and '@swagger_auto_schema' not in content:
        if verbose:
            print(f"No yasg imports or decorators found in {file_path}")
        return 0, 0, content
    
    # Count and remove yasg imports
    imports_removed = len(re.findall(YASG_IMPORT_PATTERN, content))
    modified_content = re.sub(YASG_IMPORT_PATTERN, '', content)
    
    # Handle decorators line by line for better control
    lines = modified_content.splitlines(True)  # Keep line endings
    modified_lines = []
    decorators_removed = 0
    skip_until_line = -1
    
    for i, line in enumerate(lines):
        if i <= skip_until_line:
            continue
            
        if '@swagger_auto_schema' in line:
            # Found a decorator start, now find its end
            decorator_end = find_decorator_end(lines, i)
            decorators_removed += 1
            skip_until_line = decorator_end
            
            if verbose:
                decorator_text = ''.join(lines[i:decorator_end+1]).strip()
                print(f"Removing decorator at line {i+1}:\n{decorator_text}")
        else:
            modified_lines.append(line)
    
    modified_content = ''.join(modified_lines)
    
    # Clean up multiple consecutive blank lines
    modified_content = re.sub(r'\n{3,}', '\n\n', modified_content)
    
    return imports_removed, decorators_removed, modified_content

def process_files(directory, file_pattern="*.py", dry_run=True, verbose=False):
    """
    Process Python files in the directory recursively.
    
    Args:
        directory: Directory to search for Python files
        file_pattern: Pattern to match files (default: *.py)
        dry_run: If True, only show what would be changed without modifying files
        verbose: If True, print detailed information
    
    Returns:
        Tuple of (files_modified, total_imports_removed, total_decorators_removed)
    """
    files_modified = 0
    total_imports_removed = 0
    total_decorators_removed = 0
    
    directory_path = Path(directory)
    python_files = list(directory_path.glob(f"**/{file_pattern}"))
    
    print(f"Found {len(python_files)} Python files to check")
    
    for file_path in python_files:
        imports_removed, decorators_removed, modified_content = remove_yasg_from_file(
            file_path, dry_run=dry_run, verbose=verbose
        )
        
        if imports_removed > 0 or decorators_removed > 0:
            total_imports_removed += imports_removed
            total_decorators_removed += decorators_removed
            
            if not dry_run:
                # Create backup
                backup_path = str(file_path) + '.bak'
                shutil.copy2(file_path, backup_path)
                
                # Write modified content
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(modified_content)
                
                files_modified += 1
                print(f"Modified {file_path} (removed {imports_removed} imports, {decorators_removed} decorators)")
            else:
                files_modified += 1
                print(f"Would modify {file_path} (would remove {imports_removed} imports, {decorators_removed} decorators)")
    
    return files_modified, total_imports_removed, total_decorators_removed

def main():
    parser = argparse.ArgumentParser(description="Safely remove yasg decorators using regex")
    parser.add_argument("--dir", required=True, help="Directory to search for Python files")
    parser.add_argument("--pattern", default="*.py", help="File pattern to match (default: *.py)")
    parser.add_argument("--dry-run", action="store_true", help="Only show what would be changed without modifying files")
    parser.add_argument("--verbose", action="store_true", help="Print detailed information")
    args = parser.parse_args()
    
    if not os.path.isdir(args.dir):
        print(f"Error: {args.dir} is not a valid directory")
        return 1
    
    print(f"Processing Python files in {args.dir}" + (" (dry run)" if args.dry_run else ""))
    
    files_modified, imports_removed, decorators_removed = process_files(
        args.dir, args.pattern, args.dry_run, args.verbose
    )
    
    print("\nSummary:")
    print(f"Files checked: {len(list(Path(args.dir).glob('**/' + args.pattern)))}")
    print(f"Files {'to be modified' if args.dry_run else 'modified'}: {files_modified}")
    print(f"Import statements {'to be removed' if args.dry_run else 'removed'}: {imports_removed}")
    print(f"Decorators {'to be removed' if args.dry_run else 'removed'}: {decorators_removed}")
    
    if not args.dry_run and files_modified > 0:
        print("\nBackups were created with .bak extension.")
    
    if args.dry_run and files_modified > 0:
        response = input("\nDo you want to apply these changes? (y/n): ").lower()
        if response == 'y':
            print("Applying changes...")
            process_files(args.dir, args.pattern, dry_run=False, verbose=args.verbose)
            print("\nChanges applied. Backups were created with .bak extension.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
