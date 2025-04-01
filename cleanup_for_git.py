#!/usr/bin/env python
"""
Cleanup script for AquaMind repository before committing to GitHub.
This script removes cache files and other unwanted artifacts.
"""
import os
import shutil
import fnmatch
from pathlib import Path
import sys

# Root directory of the project
ROOT_DIR = Path(__file__).resolve().parent

# Patterns to match for deletion
PATTERNS_TO_DELETE = [
    '**/__pycache__',
    '**/*.pyc',
    '**/*.pyo',
    '**/*.pyd',
    '**/.pytest_cache',
    '**/.mypy_cache',
    '**/.ruff_cache',
    '**/.ipynb_checkpoints',
    '**/.cache',
]

# Directories to exclude from cleanup
EXCLUDE_DIRS = [
    '.git',
    'venv',
    '.venv',
    'node_modules',
]

# Files to exclude from cleanup
EXCLUDE_FILES = [
    '__init__.py',  # These files are essential for Python's package system and must be preserved
]

def is_excluded(path):
    """Check if the path should be excluded from cleanup."""
    # Check if path is in excluded directories
    for exclude in EXCLUDE_DIRS:
        if exclude in str(path):
            return True
    
    # Check if file is in excluded files list
    if path.is_file() and path.name in EXCLUDE_FILES:
        return True
        
    return False

def cleanup_files():
    """Remove cache files and directories."""
    print("Starting cleanup process...")
    
    total_removed = 0
    
    for pattern in PATTERNS_TO_DELETE:
        for path in ROOT_DIR.glob(pattern):
            if is_excluded(path):
                continue
                
            if path.is_dir():
                print(f"Removing directory: {path}")
                shutil.rmtree(path, ignore_errors=True)
            else:
                print(f"Removing file: {path}")
                path.unlink(missing_ok=True)
            total_removed += 1
    
    print(f"Cleanup complete. Removed {total_removed} items.")

if __name__ == "__main__":
    # Ask for confirmation
    if len(sys.argv) > 1 and sys.argv[1] == "--force":
        cleanup_files()
    else:
        confirm = input("This will remove all cache files and directories. Continue? (y/n): ")
        if confirm.lower() == 'y':
            cleanup_files()
        else:
            print("Cleanup aborted.")
