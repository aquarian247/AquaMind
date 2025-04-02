#!/usr/bin/env python
"""
Run Data Generation Utility

This script provides a convenient wrapper for running the test data generation scripts
with proper Python path and module imports.

Usage:
    python -m scripts.utils.run_data_generation
    # Or from the project root:
    python run_data_generation.py
"""
import os
import sys
import argparse
import subprocess

def main():
    """Main function to parse arguments and run the appropriate script."""
    parser = argparse.ArgumentParser(description='Run AquaMind data generation scripts')
    parser.add_argument('--days', type=int, default=900, help='Number of days to generate data for')
    parser.add_argument('--start-date', type=str, help='Start date in YYYY-MM-DD format')
    args = parser.parse_args()

    # Determine the project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    
    # Build the command for running the script as a module
    cmd = [sys.executable, "-m", "scripts.data_generation.generate_batch_lifecycle"]
    
    # Add arguments if provided
    if args.days:
        cmd.extend(["--days", str(args.days)])
    if args.start_date:
        cmd.extend(["--start-date", args.start_date])
    
    print(f"Running command: {' '.join(cmd)}")
    print(f"Working directory: {project_root}")
    
    # Run the command from the project root
    subprocess.run(cmd, cwd=project_root)

if __name__ == "__main__":
    main()
