#!/usr/bin/env python
"""
analyze_schemathesis_failures.py - Analyze Schemathesis test failures

This script analyzes the output from Schemathesis contract tests to identify
patterns in API failures, categorize them by type, and provide recommendations
for fixes.

Usage:
    python analyze_schemathesis_failures.py [schemathesis_output_file]

If no file is specified, defaults to 'schemathesis-after-fix.txt'
"""

import re
import sys
import os
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Set, Any, Optional

# Default input file
DEFAULT_INPUT_FILE = "schemathesis-after-fix.txt"

# Failure type patterns
PATTERNS = {
    "integrity_error": r"IntegrityError.*NOT NULL constraint failed: (\w+)\.(\w+)",
    "response_schema": r"Response violates schema.*\n\s+(.*) is not of type '(\w+)'",
    "undocumented_status": r"Undocumented HTTP status code\s+Received: (\d+)\s+Documented: ([\d, ]+)",
    "server_error": r"Server error.*\[(\d+)\] ([\w\s]+):",
    "auth_error": r"\[401\] Unauthorized:",
}

# Endpoint patterns
ENDPOINT_PATTERN = r"^(GET|POST|PUT|PATCH|DELETE) (\/api\/[\w\/-]+)( F| \.)"
TEST_CASE_PATTERN = r"Test Case ID: (\w+)"

class SchemaFailureAnalyzer:
    """Analyzes Schemathesis test failures to identify patterns and suggest fixes."""
    
    def __init__(self, filename: str):
        self.filename = filename
        self.failures = []
        self.endpoints = {}  # Maps endpoint to pass/fail status
        self.failure_types = defaultdict(list)
        self.endpoint_failures = defaultdict(list)
        self.method_failures = defaultdict(int)
        self.method_total = defaultdict(int)
        self.total_operations = 0
        self.total_failures = 0
        self.failure_details = []
        self.missing_required_fields = defaultdict(set)
        self.schema_type_mismatches = defaultdict(list)
        
    def read_file(self) -> str:
        """Read the Schemathesis output file."""
        try:
            with open(self.filename, 'r', encoding='utf-8', errors='replace') as f:
                return f.read()
        except FileNotFoundError:
            print(f"Error: File '{self.filename}' not found.")
            sys.exit(1)
        except Exception as e:
            print(f"Error reading file: {e}")
            sys.exit(1)
    
    def extract_endpoints(self, content: str) -> None:
        """Extract all endpoints and their pass/fail status."""
        for line in content.split('\n'):
            match = re.search(ENDPOINT_PATTERN, line)
            if match:
                method, path, status = match.groups()
                self.total_operations += 1
                self.method_total[method] += 1
                endpoint = f"{method} {path}"
                is_failure = status.strip() == "F"
                self.endpoints[endpoint] = is_failure
                if is_failure:
                    self.total_failures += 1
                    self.method_failures[method] += 1
    
    def extract_failure_details(self, content: str) -> None:
        """Extract detailed information about each failure."""
        # Split content into failure sections
        failure_sections = re.split(r"_{20,} ", content)
        
        # Skip the first section which is usually the header
        if "FAILURES" in failure_sections[0]:
            failure_sections = failure_sections[1:]
        
        for section in failure_sections:
            if not section.strip():
                continue
                
            # Extract endpoint and method
            endpoint_match = re.search(r"(GET|POST|PUT|PATCH|DELETE) (\/api\/[\w\/-]+)", section)
            if not endpoint_match:
                continue
                
            method, path = endpoint_match.groups()
            endpoint = f"{method} {path}"
            
            # Extract test case ID
            test_id_match = re.search(TEST_CASE_PATTERN, section)
            test_id = test_id_match.group(1) if test_id_match else "unknown"
            
            # Extract failure type and details
            failure_type = "unknown"
            details = {}
            
            # Check for integrity errors
            integrity_match = re.search(PATTERNS["integrity_error"], section)
            if integrity_match:
                failure_type = "integrity_error"
                table, field = integrity_match.groups()
                details = {
                    "table": table,
                    "field": field,
                    "message": f"NOT NULL constraint failed: {table}.{field}"
                }
                self.missing_required_fields[table].add(field)
            
            # Check for schema violations
            schema_match = re.search(PATTERNS["response_schema"], section)
            if schema_match:
                failure_type = "response_schema"
                value, expected_type = schema_match.groups()
                details = {
                    "value": value,
                    "expected_type": expected_type
                }
                self.schema_type_mismatches[endpoint].append((value, expected_type))
            
            # Check for undocumented status codes
            status_match = re.search(PATTERNS["undocumented_status"], section)
            if status_match:
                failure_type = "undocumented_status"
                received, documented = status_match.groups()
                details = {
                    "received": received,
                    "documented": documented
                }
            
            # Check for server errors
            server_match = re.search(PATTERNS["server_error"], section)
            if server_match:
                failure_type = "server_error"
                status_code, error_type = server_match.groups()
                details = {
                    "status_code": status_code,
                    "error_type": error_type
                }
            
            # Check for auth errors
            if re.search(PATTERNS["auth_error"], section):
                failure_type = "auth_error"
                details = {
                    "message": "Authentication required but not provided or invalid"
                }
            
            # Extract curl command for reproduction
            curl_match = re.search(r"Reproduce with:\s+curl (.+?)http", section, re.DOTALL)
            curl_command = curl_match.group(1).strip() if curl_match else ""
            
            # Add to failure collections
            failure_info = {
                "endpoint": endpoint,
                "method": method,
                "path": path,
                "test_id": test_id,
                "type": failure_type,
                "details": details,
                "curl": curl_command
            }
            
            self.failure_details.append(failure_info)
            self.failure_types[failure_type].append(failure_info)
            self.endpoint_failures[endpoint].append(failure_info)
    
    def analyze(self) -> None:
        """Analyze the Schemathesis output file."""
        content = self.read_file()
        self.extract_endpoints(content)
        self.extract_failure_details(content)
    
    def generate_recommendations(self) -> List[str]:
        """Generate recommendations based on failure analysis."""
        recommendations = []
        
        # Recommendations for integrity errors
        if self.missing_required_fields:
            recommendations.append("## Data Integrity Recommendations")
            for table, fields in self.missing_required_fields.items():
                fields_list = ", ".join(f"`{field}`" for field in sorted(fields))
                recommendations.append(f"- Add default values or make nullable for {table} fields: {fields_list}")
                recommendations.append(f"  - Update serializers to handle missing {fields_list}")
                recommendations.append(f"  - Add examples in OpenAPI schema for {table}")
        
        # Recommendations for schema violations
        if self.schema_type_mismatches:
            recommendations.append("\n## Schema Mismatch Recommendations")
            for endpoint, mismatches in self.schema_type_mismatches.items():
                mismatch_types = set((value, expected) for value, expected in mismatches)
                for value, expected in mismatch_types:
                    if value == "[]" and expected == "object":
                        recommendations.append(f"- Update {endpoint} schema to accept empty arrays")
                        recommendations.append(f"  - Change response schema to allow both object and array types")
                        recommendations.append(f"  - Or ensure endpoint always returns an object, even when empty")
        
        # Recommendations for endpoints with multiple failures
        if len(self.endpoint_failures) > 0:
            problem_endpoints = sorted(
                [(endpoint, len(failures)) for endpoint, failures in self.endpoint_failures.items()],
                key=lambda x: x[1],
                reverse=True
            )
            
            recommendations.append("\n## High-Priority Endpoints")
            for endpoint, count in problem_endpoints[:5]:
                recommendations.append(f"- {endpoint}: {count} failures")
        
        # General recommendations
        recommendations.append("\n## General Recommendations")
        recommendations.append("1. Create test data seeding script to ensure valid IDs exist for all detail endpoints")
        recommendations.append("2. Add examples to OpenAPI schema for complex request bodies")
        recommendations.append("3. Implement consistent error handling for all endpoints")
        recommendations.append("4. Update schema to match actual response formats (especially empty arrays vs. objects)")
        
        return recommendations
    
    def print_summary(self) -> None:
        """Print a summary of the analysis."""
        print("\n" + "=" * 80)
        print(f"SCHEMATHESIS FAILURE ANALYSIS: {self.filename}")
        print("=" * 80)
        
        # Overall statistics
        pass_count = self.total_operations - self.total_failures
        pass_rate = (pass_count / self.total_operations) * 100 if self.total_operations > 0 else 0
        print(f"\n## Overall Statistics")
        print(f"- Total operations: {self.total_operations}")
        print(f"- Passed: {pass_count} ({pass_rate:.1f}%)")
        print(f"- Failed: {self.total_failures} ({100-pass_rate:.1f}%)")
        
        # Method statistics
        print(f"\n## Failures by HTTP Method")
        for method in sorted(self.method_total.keys()):
            total = self.method_total[method]
            failures = self.method_failures[method]
            failure_rate = (failures / total) * 100 if total > 0 else 0
            print(f"- {method}: {failures}/{total} ({failure_rate:.1f}% failure rate)")
        
        # Failure type statistics
        print(f"\n## Failures by Type")
        for failure_type, failures in sorted(self.failure_types.items(), key=lambda x: len(x[1]), reverse=True):
            print(f"- {failure_type}: {len(failures)}")
            
            # Show examples for each failure type
            if failures:
                example = failures[0]
                print(f"  Example: {example['endpoint']}")
                if 'details' in example and example['details']:
                    for key, value in example['details'].items():
                        print(f"    {key}: {value}")
        
        # Missing required fields
        if self.missing_required_fields:
            print(f"\n## Missing Required Fields")
            for table, fields in self.missing_required_fields.items():
                print(f"- {table}: {', '.join(sorted(fields))}")
        
        # Schema type mismatches
        if self.schema_type_mismatches:
            print(f"\n## Schema Type Mismatches")
            for endpoint, mismatches in self.schema_type_mismatches.items():
                mismatch_types = set((value, expected) for value, expected in mismatches)
                print(f"- {endpoint}:")
                for value, expected in mismatch_types:
                    print(f"  - Got {value}, expected {expected}")
        
        # Recommendations
        print("\n" + "=" * 80)
        print("RECOMMENDATIONS")
        print("=" * 80)
        for rec in self.generate_recommendations():
            print(rec)


def main():
    """Main function to run the analysis."""
    # Get input file from command line or use default
    input_file = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_INPUT_FILE
    
    # Check if file exists
    if not os.path.exists(input_file):
        print(f"Error: File '{input_file}' not found.")
        sys.exit(1)
    
    # Run analysis
    analyzer = SchemaFailureAnalyzer(input_file)
    analyzer.analyze()
    analyzer.print_summary()


if __name__ == "__main__":
    main()
