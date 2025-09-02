#!/usr/bin/env python3
"""
Post-Session Data Validation

Comprehensive validation script that runs after each data generation session.
Validates data integrity, relationships, and business logic.

This script should be integrated into the main data generation pipeline.
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import verification components
from data_integrity_verifier import DataIntegrityVerifier

class PostSessionValidator:
    """Validator that runs after each data generation session."""

    def __init__(self, session_number):
        self.session_number = session_number
        self.verifier = DataIntegrityVerifier()
        self.reports_dir = project_root / "scripts" / "data_generation" / "reports"
        self.reports_dir.mkdir(exist_ok=True)

    def run_validation(self):
        """Run complete post-session validation."""
        print(f"🔍 POST-SESSION {self.session_number} VALIDATION")
        print("=" * 60)

        start_time = datetime.now()
        success = self.verifier.run_full_verification()
        end_time = datetime.now()

        # Generate detailed report
        self.generate_detailed_report(start_time, end_time)

        # Generate summary for CI/CD
        self.generate_summary_report(success)

        return success

    def generate_detailed_report(self, start_time, end_time):
        """Generate detailed validation report."""
        report_file = self.reports_dir / f"session_{self.session_number}_detailed_report.json"

        report_data = {
            "session": self.session_number,
            "validation_timestamp": datetime.now().isoformat(),
            "execution_time_seconds": (end_time - start_time).total_seconds(),
            "summary": {
                "total_errors": len(self.verifier.errors),
                "total_warnings": len(self.verifier.warnings),
                "status": "PASS" if len(self.verifier.errors) == 0 else "FAIL"
            },
            "errors": self.verifier.errors,
            "warnings": self.verifier.warnings,
            "statistics": dict(self.verifier.stats),
            "relationships": {k: list(v) for k, v in self.verifier.relationships.items()}
        }

        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)

        print(f"📄 Detailed report saved: {report_file}")

    def generate_summary_report(self, success):
        """Generate summary report for CI/CD integration."""
        summary_file = self.reports_dir / f"session_{self.session_number}_summary.txt"

        with open(summary_file, 'w') as f:
            f.write(f"AQUAMIND SESSION {self.session_number} VALIDATION SUMMARY\n")
            f.write("=" * 60 + "\n")
            f.write(f"Timestamp: {datetime.now()}\n")
            f.write(f"Status: {'✅ PASS' if success else '❌ FAIL'}\n")
            f.write(f"Errors: {len(self.verifier.errors)}\n")
            f.write(f"Warnings: {len(self.verifier.warnings)}\n")
            f.write("\nSTATISTICS:\n")

            for key, value in sorted(self.verifier.stats.items()):
                f.write(f"  {key}: {value}\n")

            if self.verifier.errors:
                f.write("\nCRITICAL ERRORS:\n")
                for error in self.verifier.errors[:5]:  # Top 5 errors
                    f.write(f"  ❌ {error['message']}\n")

            if self.verifier.warnings:
                f.write("\nWARNINGS:\n")
                for warning in self.verifier.warnings[:5]:  # Top 5 warnings
                    f.write(f"  ⚠️  {warning['message']}\n")

        print(f"📋 Summary report saved: {summary_file}")

    def print_validation_results(self):
        """Print validation results to console."""
        print("
📊 VALIDATION RESULTS:"        print(f"   Errors: {len(self.verifier.errors)}")
        print(f"   Warnings: {len(self.verifier.warnings)}")

        if len(self.verifier.errors) == 0:
            print("   Status: ✅ PASS - All checks passed!")
        else:
            print("   Status: ❌ FAIL - Issues found"
            # Show top errors
            print("\n🚨 TOP ERRORS:")
            for i, error in enumerate(self.verifier.errors[:3], 1):
                print(f"   {i}. {error['message']}")

def validate_session(session_number):
    """Validate a specific session."""
    validator = PostSessionValidator(session_number)
    success = validator.run_validation()
    validator.print_validation_results()
    return success

def main():
    """Main function for command line usage."""
    if len(sys.argv) != 2:
        print("Usage: python post_session_validator.py <session_number>")
        sys.exit(1)

    try:
        session_number = int(sys.argv[1])
    except ValueError:
        print("Error: Session number must be an integer")
        sys.exit(1)

    success = validate_session(session_number)

    if success:
        print("\n✅ Session validation completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Session validation found issues!")
        sys.exit(1)

if __name__ == "__main__":
    main()

