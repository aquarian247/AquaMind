#!/usr/bin/env python
"""
AquaMind Test Data Generation Runner

This script is a convenience wrapper to run the test data generation script
with the proper Python module imports.

Usage:
    python run_data_generation.py [options]

Options:
    --days N                Number of days to generate data for (default: 900)
    --start-date YYYY-MM-DD Start date for data generation (default: 900 days ago)
"""
import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and run the actual utility
from scripts.utils.run_data_generation import main

if __name__ == "__main__":
    main()
