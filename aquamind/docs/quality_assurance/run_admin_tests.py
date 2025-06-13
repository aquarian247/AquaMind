#!/usr/bin/env python3
"""
Simple script to run AquaMind Django Admin Playwright tests

This script demonstrates how to run the Playwright tests for the Django admin interface.
It can be used for development, CI/CD, or manual testing.

Run from project root: python aquamind/docs/quality_assurance/run_admin_tests.py
"""

import subprocess
import sys
import os
from pathlib import Path


def check_requirements():
    """Check if required dependencies are installed"""
    try:
        import pytest
        import playwright
        print("✅ Required dependencies found")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Please install with: pip install pytest playwright pytest-playwright")
        return False


def check_django_server():
    """Check if Django server is running"""
    import urllib.request
    import urllib.error
    
    try:
        urllib.request.urlopen("http://localhost:8000/admin/", timeout=5)
        print("✅ Django server is running on localhost:8000")
        return True
    except urllib.error.URLError:
        print("❌ Django server is not running on localhost:8000")
        print("Please start the server with: python manage.py runserver 8000")
        return False


def run_tests(test_type="all", browser="firefox", headless=False):
    """Run the Playwright tests"""
    
    # Get project root (3 levels up from this script)
    project_root = Path(__file__).parent.parent.parent.parent
    os.chdir(project_root)
    
    # Base pytest command - tests are in project root/tests/
    cmd = ["python", "-m", "pytest", "tests/test_django_admin_playwright.py", "-v"]
    
    # Add browser selection
    cmd.extend(["--browser", browser])
    
    # Add headless mode if requested
    if headless:
        cmd.append("--headless")
    
    # Add test type filtering
    if test_type == "smoke":
        cmd.extend(["-m", "smoke"])
    elif test_type == "ui":
        cmd.extend(["-m", "ui"])
    elif test_type == "integration":
        cmd.extend(["-m", "integration"])
    elif test_type == "fast":
        cmd.extend(["-m", "not slow"])
    
    # Add HTML report generation (in quality_assurance folder)
    cmd.extend(["--html=aquamind/docs/quality_assurance/test-results/report.html", "--self-contained-html"])
    
    # Add screenshot on failure
    cmd.append("--screenshot=on")
    
    print(f"🚀 Running tests with command: {' '.join(cmd)}")
    print(f"📁 Working directory: {project_root}")
    
    try:
        result = subprocess.run(cmd, check=True)
        print("✅ Tests completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Tests failed with exit code: {e.returncode}")
        return False


def main():
    """Main function"""
    print("🧪 AquaMind Django Admin Playwright Test Runner")
    print("=" * 50)
    
    # Check requirements
    if not check_requirements():
        sys.exit(1)
    
    # Check Django server
    if not check_django_server():
        sys.exit(1)
    
    # Create test results directory in quality_assurance folder
    results_dir = Path(__file__).parent / "test-results"
    results_dir.mkdir(exist_ok=True)
    (results_dir / "screenshots").mkdir(exist_ok=True)
    (results_dir / "videos").mkdir(exist_ok=True)
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Run AquaMind Django Admin Playwright tests")
    parser.add_argument("--type", choices=["all", "smoke", "ui", "integration", "fast"], 
                       default="all", help="Type of tests to run")
    parser.add_argument("--browser", choices=["chromium", "firefox", "webkit"], 
                       default="firefox", help="Browser to use for testing")
    parser.add_argument("--headless", action="store_true", 
                       help="Run tests in headless mode")
    
    args = parser.parse_args()
    
    # Run tests
    success = run_tests(args.type, args.browser, args.headless)
    
    if success:
        print("\n📊 Test Results:")
        print(f"  - HTML Report: aquamind/docs/quality_assurance/test-results/report.html")
        print(f"  - Screenshots: aquamind/docs/quality_assurance/test-results/screenshots/")
        print(f"  - Videos: aquamind/docs/quality_assurance/test-results/videos/")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main() 