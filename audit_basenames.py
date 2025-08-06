#!/usr/bin/env python
"""
Audit basename usage in router registrations across the AquaMind project.

This script scans all router.py files in the apps directory, checks for
router.register() calls, and verifies that each has an explicit basename
parameter. It also reports any duplicate basenames across the project.

Usage:
    python audit_basenames.py
"""
import os
import ast
import sys
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, Set


class RouterVisitor(ast.NodeVisitor):
    """AST visitor to find router.register() calls."""
    
    def __init__(self):
        self.registrations = []
        
    def visit_Call(self, node):
        # Check if this is a router.register() call
        if (isinstance(node.func, ast.Attribute) and 
            node.func.attr == 'register' and 
            isinstance(node.func.value, ast.Name) and
            node.func.value.id in ['router']):
            
            # Extract the URL pattern (first arg)
            url_pattern = None
            if node.args and len(node.args) > 0:
                if isinstance(node.args[0], ast.Constant):
                    url_pattern = node.args[0].value
                elif isinstance(node.args[0], ast.Str):  # For Python < 3.8
                    url_pattern = node.args[0].s
            
            # Extract the ViewSet (second arg)
            viewset = None
            if node.args and len(node.args) > 1:
                if isinstance(node.args[1], ast.Name):
                    viewset = node.args[1].id
            
            # Extract the basename (keyword arg)
            basename = None
            for keyword in node.keywords:
                if keyword.arg == 'basename':
                    if isinstance(keyword.value, ast.Constant):
                        basename = keyword.value.value
                    elif isinstance(keyword.value, ast.Str):  # For Python < 3.8
                        basename = keyword.value.s
            
            # Store the registration info
            self.registrations.append({
                'url_pattern': url_pattern,
                'viewset': viewset,
                'basename': basename
            })
        
        # Continue visiting children
        self.generic_visit(node)


def find_router_files() -> List[str]:
    """Find all router.py files in the apps directory."""
    router_files = []
    apps_dir = os.path.join(os.getcwd(), 'apps')
    
    for app_name in os.listdir(apps_dir):
        app_path = os.path.join(apps_dir, app_name)
        if os.path.isdir(app_path):
            # Check for api/routers.py
            router_path = os.path.join(app_path, 'api', 'routers.py')
            if os.path.exists(router_path):
                router_files.append((app_name, router_path))
    
    return router_files


def parse_router_file(app_name: str, file_path: str) -> List[Dict]:
    """Parse a router.py file and extract router.register() calls."""
    try:
        with open(file_path, 'r') as f:
            code = f.read()
        
        # Parse the code into an AST
        tree = ast.parse(code)
        
        # Visit the AST to find router.register() calls
        visitor = RouterVisitor()
        visitor.visit(tree)
        
        # Add app_name to each registration
        for reg in visitor.registrations:
            reg['app_name'] = app_name
            reg['file_path'] = file_path
        
        return visitor.registrations
    
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return []


def analyze_basenames() -> Tuple[List[Dict], Dict[str, List[Dict]], Set[str]]:
    """Analyze all router files and check for missing or duplicate basenames."""
    router_files = find_router_files()
    all_registrations = []
    basename_map = defaultdict(list)
    missing_basenames = []
    
    for app_name, file_path in router_files:
        registrations = parse_router_file(app_name, file_path)
        all_registrations.extend(registrations)
        
        # Check for missing basenames
        for reg in registrations:
            if reg['basename'] is None:
                missing_basenames.append(reg)
            else:
                basename_map[reg['basename']].append(reg)
    
    # Find duplicate basenames
    duplicate_basenames = {
        basename: regs for basename, regs in basename_map.items() 
        if len(regs) > 1
    }
    
    return missing_basenames, duplicate_basenames, set(basename_map.keys())


def print_report(missing_basenames: List[Dict], 
                 duplicate_basenames: Dict[str, List[Dict]],
                 all_basenames: Set[str]) -> None:
    """Print a report of the basename analysis."""
    print("\n" + "="*80)
    print("BASENAME AUDIT REPORT")
    print("="*80)
    
    # Print missing basenames
    print("\n1. REGISTRATIONS MISSING EXPLICIT BASENAMES")
    print("-"*50)
    if missing_basenames:
        for i, reg in enumerate(missing_basenames, 1):
            print(f"{i}. App: {reg['app_name']}")
            print(f"   ViewSet: {reg['viewset']}")
            print(f"   URL Pattern: {reg['url_pattern']}")
            print(f"   File: {reg['file_path']}")
            print()
    else:
        print("No registrations missing basenames! [OK]")
    
    # Print duplicate basenames
    print("\n2. DUPLICATE BASENAMES ACROSS APPS")
    print("-"*50)
    if duplicate_basenames:
        for basename, regs in duplicate_basenames.items():
            print(f"Basename '{basename}' used {len(regs)} times:")
            for reg in regs:
                print(f"  - App: {reg['app_name']}, ViewSet: {reg['viewset']}")
            print()
    else:
        print("No duplicate basenames found! [OK]")
    
    # Print all basenames
    print("\n3. ALL BASENAMES IN USE")
    print("-"*50)
    for basename in sorted(all_basenames):
        print(f"- {basename}")
    
    # Print summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total router registrations: {len(missing_basenames) + len(all_basenames)}")
    print(f"Registrations with explicit basenames: {len(all_basenames)}")
    print(f"Registrations missing basenames: {len(missing_basenames)}")
    print(f"Unique basenames in use: {len(all_basenames)}")
    print(f"Duplicate basenames: {len(duplicate_basenames)}")
    
    # Print recommendations
    if missing_basenames:
        print("\nRECOMMENDATION:")
        print("Add explicit basenames to all router registrations using kebab-case.")
        print("Example: router.register(r'users', UserViewSet, basename='user')")
    else:
        print("\nAll router registrations have explicit basenames! [OK]")


def main():
    """Main function to run the basename audit."""
    print("Auditing basename usage across the project...")
    missing_basenames, duplicate_basenames, all_basenames = analyze_basenames()
    print_report(missing_basenames, duplicate_basenames, all_basenames)
    
    # Exit with error code if there are missing basenames
    if missing_basenames:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
