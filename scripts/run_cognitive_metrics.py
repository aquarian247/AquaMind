#!/usr/bin/env python
"""
AquaMind CI Cognitive Complexity Collection Script
Runs flake8-cognitive-complexity and exports text artifacts for CI
"""

import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

# Django app directories to analyze
DJANGO_APPS = [
    'batch', 'broodstock', 'environmental', 'health',
    'infrastructure', 'inventory', 'operational', 'scenario', 'users'
]


class CognitiveMetricsCollector:
    def __init__(self, base_path: str = 'apps', output_dir: str = 'aquamind/docs/metrics'):
        self.base_path = Path(base_path)
        self.output_dir = Path(output_dir)
        self.timestamp = datetime.now().strftime('%Y-%m-%d')
        self.keep_historical = False

    def cleanup_old_files(self, pattern: str):
        """Remove old cognitive complexity files matching the pattern, keeping only the most recent."""
        import glob

        # Find all files matching the pattern
        pattern_path = self.output_dir / pattern
        files = glob.glob(str(pattern_path))

        if len(files) <= 1:
            return  # Keep at least one file

        # Sort by modification time (newest first)
        files.sort(key=os.path.getmtime, reverse=True)

        # Remove all but the most recent file
        for old_file in files[1:]:
            try:
                os.remove(old_file)
                print(f"Cleaned up old cognitive file: {Path(old_file).name}")
            except OSError as e:
                print(f"Warning: Could not remove {old_file}: {e}", file=sys.stderr)

    def run_flake8_cognitive(self, target_path: Path) -> tuple[str, str, int]:
        """Run flake8 with cognitive complexity plugin on target path."""
        try:
            # Run flake8 with cognitive complexity plugin
            cmd = [
                'python', '-m', 'flake8',
                '--select=C90',  # Cognitive complexity checks
                '--max-cognitive-complexity=15',  # Warning threshold
                '--format=%(path)s:%(row)d:%(col)d: C90%(code)s %(text)s',
                str(target_path)
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            return result.stdout, result.stderr, result.returncode

        except subprocess.TimeoutExpired:
            return "", "Timeout: Cognitive complexity analysis took too long", 1
        except Exception as e:
            return "", f"Error running flake8 cognitive complexity: {e}", 1

    def analyze_app(self, app_name: str) -> dict:
        """Analyze cognitive complexity for a single Django app."""
        app_path = self.base_path / app_name

        if not app_path.exists():
            return {
                'app': app_name,
                'timestamp': self.timestamp,
                'error': f'App path {app_path} does not exist',
                'files_analyzed': 0,
                'violations': [],
                'summary': {}
            }

        print(f"Running cognitive complexity analysis for {app_name}...")

        stdout, stderr, returncode = self.run_flake8_cognitive(app_path)

        # Parse violations
        violations = []
        if stdout:
            for line in stdout.strip().split('\n'):
                if line.strip():
                    violations.append(line)

        # Count violations by severity
        violation_summary = {
            'total_violations': len(violations),
            'severity_breakdown': {
                'C901': 0,  # Cognitive complexity too high
            }
        }

        for violation in violations:
            if 'C901' in violation:
                violation_summary['severity_breakdown']['C901'] += 1

        # Count Python files (excluding tests, migrations, __pycache__)
        python_files = []
        for py_file in app_path.rglob('*.py'):
            if not any(skip in str(py_file) for skip in ['migrations', '__pycache__', '/tests/']):
                python_files.append(str(py_file.relative_to(self.base_path.parent)))

        result = {
            'app': app_name,
            'timestamp': self.timestamp,
            'files_analyzed': len(python_files),
            'python_files': python_files,
            'violations': violations,
            'summary': violation_summary,
            'raw_output': stdout,
            'error_output': stderr,
            'return_code': returncode
        }

        # Add threshold analysis
        result['threshold_analysis'] = self._analyze_thresholds(violation_summary)

        return result

    def _analyze_thresholds(self, violation_summary: dict) -> dict:
        """Analyze violations against predefined thresholds."""
        total_violations = violation_summary['total_violations']

        # Define thresholds (warn-only for now)
        thresholds = {
            'warning': 5,    # Warn if > 5 violations per app
            'critical': 15   # Critical if > 15 violations per app
        }

        analysis = {
            'thresholds': thresholds,
            'status': 'pass',
            'message': 'Cognitive complexity within acceptable limits'
        }

        if total_violations > thresholds['critical']:
            analysis.update({
                'status': 'critical',
                'message': f'Critical: {total_violations} violations exceed critical threshold of {thresholds["critical"]}'
            })
        elif total_violations > thresholds['warning']:
            analysis.update({
                'status': 'warning',
                'message': f'Warning: {total_violations} violations exceed warning threshold of {thresholds["warning"]}'
            })

        return analysis

    def run_analysis(self, keep_historical: bool = False):
        """Run complete cognitive complexity analysis for all apps."""
        print("Starting AquaMind CI Cognitive Complexity Collection...")
        print(f"Timestamp: {self.timestamp}")

        # Set the keep_historical flag
        self.keep_historical = keep_historical

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Clean up old files unless keeping historical data
        if not keep_historical:
            print("Cleaning up old cognitive complexity files...")
            self.cleanup_old_files("backend_cognitive_*.txt")

        all_results = {
            'project': 'aquamind-backend',
            'timestamp': self.timestamp,
            'generated_at': datetime.now().isoformat(),
            'metric_type': 'cognitive_complexity',
            'apps': []
        }

        project_summary = {
            'total_apps': len(DJANGO_APPS),
            'total_violations': 0,
            'apps_with_violations': 0,
            'apps_above_warning': 0,
            'apps_above_critical': 0
        }

        # Analyze each app
        for app in DJANGO_APPS:
            try:
                app_metrics = self.analyze_app(app)
                all_results['apps'].append(app_metrics)

                # Update project summary
                violations = app_metrics['summary']['total_violations']
                project_summary['total_violations'] += violations

                if violations > 0:
                    project_summary['apps_with_violations'] += 1

                threshold_status = app_metrics['threshold_analysis']['status']
                if threshold_status == 'warning':
                    project_summary['apps_above_warning'] += 1
                elif threshold_status == 'critical':
                    project_summary['apps_above_critical'] += 1

                # Save individual app results
                filename = f"backend_cognitive_{app}_{self.timestamp}.txt" if self.keep_historical else f"backend_cognitive_{app}.txt"
                app_output_file = self.output_dir / filename
                with open(app_output_file, 'w', encoding='utf-8') as f:
                    f.write(f"# Cognitive Complexity Report for {app}\n")
                    f.write(f"# Generated: {app_metrics['timestamp']}\n")
                    f.write(f"# Files analyzed: {app_metrics['files_analyzed']}\n")
                    f.write(f"# Total violations: {violations}\n")
                    f.write(f"# Status: {app_metrics['threshold_analysis']['status']}\n")
                    f.write(f"# Message: {app_metrics['threshold_analysis']['message']}\n\n")

                    if app_metrics['violations']:
                        f.write("## Violations:\n")
                        for violation in app_metrics['violations']:
                            f.write(f"{violation}\n")
                    else:
                        f.write("## No violations found\n")

                    if app_metrics['error_output']:
                        f.write(f"\n## Errors:\n{app_metrics['error_output']}\n")

                print(f"Saved {app} cognitive report to {app_output_file}")

            except Exception as e:
                print(f"Error analyzing {app}: {e}", file=sys.stderr)
                continue

        # Add project summary
        all_results['project_summary'] = project_summary

        # Save aggregated results
        summary_filename = f"backend_cognitive_{self.timestamp}.txt" if self.keep_historical else "backend_cognitive_summary.txt"
        summary_output_file = self.output_dir / summary_filename
        with open(summary_output_file, 'w', encoding='utf-8') as f:
            f.write("# AquaMind Backend Cognitive Complexity Summary\n")
            f.write(f"# Generated: {self.timestamp}\n")
            f.write(f"# Total apps analyzed: {project_summary['total_apps']}\n")
            f.write(f"# Total violations: {project_summary['total_violations']}\n")
            f.write(f"# Apps with violations: {project_summary['apps_with_violations']}\n")
            f.write(f"# Apps above warning threshold: {project_summary['apps_above_warning']}\n")
            f.write(f"# Apps above critical threshold: {project_summary['apps_above_critical']}\n\n")

            f.write("## App Details:\n")
            for app_data in all_results['apps']:
                f.write(f"### {app_data['app']}\n")
                f.write(f"- Files analyzed: {app_data['files_analyzed']}\n")
                f.write(f"- Violations: {app_data['summary']['total_violations']}\n")
                f.write(f"- Status: {app_data['threshold_analysis']['status']}\n")
                f.write(f"- Message: {app_data['threshold_analysis']['message']}\n\n")

        print(f"Saved cognitive summary to {summary_output_file}")
        print(f"CI Cognitive complexity collection completed. Artifacts saved to {self.output_dir}")
        return all_results


def main():
    """Main entry point for CI cognitive complexity collection."""
    import argparse

    parser = argparse.ArgumentParser(description='Run cognitive complexity analysis for CI')
    parser.add_argument('--output-dir', default='aquamind/docs/metrics',
                       help='Output directory for text artifacts')
    parser.add_argument('--base-path', default='apps',
                       help='Base path for Django apps')
    parser.add_argument('--keep-historical', action='store_true',
                       help='Keep historical versions of cognitive files instead of overwriting')

    args = parser.parse_args()

    collector = CognitiveMetricsCollector(
        base_path=args.base_path,
        output_dir=args.output_dir
    )

    try:
        results = collector.run_analysis(keep_historical=args.keep_historical)
        print("✓ CI Cognitive complexity collection completed successfully")

        # Print summary
        summary = results['project_summary']
        print("\n🧠 Cognitive Complexity Summary:")
        print(f"  Total apps analyzed: {summary['total_apps']}")
        print(f"  Total violations: {summary['total_violations']}")
        print(f"  Apps with violations: {summary['apps_with_violations']}")
        print(f"  Apps above warning: {summary['apps_above_warning']}")
        print(f"  Apps above critical: {summary['apps_above_critical']}")

        return 0

    except Exception as e:
        print(f"✗ CI Cognitive complexity collection failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
