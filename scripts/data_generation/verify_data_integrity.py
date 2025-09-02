#!/usr/bin/env python3
"""
Data Integrity Verification Runner

Simple script to run data integrity verification after each session.
Integrates with the main data generation pipeline.

Usage:
    python verify_data_integrity.py [--session SESSION_NUMBER] [--quiet]
"""

import os
import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import the verifier
from data_integrity_verifier import DataIntegrityVerifier

def run_verification(session_number=None, quiet=False):
    """Run data integrity verification."""

    if not quiet:
        print(f"🔍 Running AquaMind Data Integrity Verification")
        if session_number:
            print(f"   Session: {session_number}")
        print("-" * 60)

    # Initialize verifier
    verifier = DataIntegrityVerifier()

    # Run verification
    success = verifier.run_full_verification()

    # Save results to file if specified
    if session_number:
        results_file = project_root / "scripts" / "data_generation" / "reports" / f"session_{session_number}_integrity_report.txt"
        results_file.parent.mkdir(exist_ok=True)

        with open(results_file, 'w') as f:
            f.write("AQUAMIND DATA INTEGRITY VERIFICATION REPORT\n")
            f.write("=" * 50 + "\n")
            f.write(f"Session: {session_number}\n")
            f.write(f"Timestamp: {verifier.errors[0]['timestamp'] if verifier.errors else 'N/A'}\n\n")

            f.write(f"ISSUES FOUND:\n")
            f.write(f"Errors: {len(verifier.errors)}\n")
            f.write(f"Warnings: {len(verifier.warnings)}\n\n")

            if verifier.errors:
                f.write("ERRORS:\n")
                for error in verifier.errors:
                    f.write(f"- {error['message']}\n")
                f.write("\n")

            if verifier.warnings:
                f.write("WARNINGS:\n")
                for warning in verifier.warnings:
                    f.write(f"- {warning['message']}\n")
                f.write("\n")

            f.write("STATISTICS:\n")
            for key, value in verifier.stats.items():
                f.write(f"- {key}: {value}\n")

        if not quiet:
            print(f"\n📄 Report saved to: {results_file}")

    return success

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Run AquaMind Data Integrity Verification')
    parser.add_argument('--session', type=int, help='Session number for reporting')
    parser.add_argument('--quiet', action='store_true', help='Suppress verbose output')

    args = parser.parse_args()

    success = run_verification(args.session, args.quiet)

    if success:
        if not args.quiet:
            print("\n✅ All data integrity checks passed!")
        sys.exit(0)
    else:
        if not args.quiet:
            print("\n❌ Data integrity issues found!")
        sys.exit(1)

if __name__ == "__main__":
    main()

