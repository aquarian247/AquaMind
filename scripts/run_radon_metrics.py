#!/usr/bin/env python
"""
AquaMind CI Metrics Collection Script
Runs radon metrics (CC, MI, Halstead, Raw) and exports JSON artifacts for CI
"""

import os
import json
import sys
from datetime import datetime
from pathlib import Path

# Radon imports
from radon.complexity import cc_visit
from radon.metrics import h_visit, mi_visit
from radon.raw import analyze

# Django app directories to analyze
DJANGO_APPS = [
    'batch', 'broodstock', 'environmental', 'health',
    'infrastructure', 'inventory', 'operational', 'scenario', 'users'
]

class CIMetricsCollector:
    def __init__(self, base_path: str = 'apps', output_dir: str = 'aquamind/docs/metrics'):
        self.base_path = Path(base_path)
        self.output_dir = Path(output_dir)
        self.timestamp = datetime.now().strftime('%Y-%m-%d')
        self.keep_historical = False

    def cleanup_old_files(self, pattern: str):
        """Remove old metric files matching the pattern, keeping only the most recent."""
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
                print(f"Cleaned up old metrics file: {Path(old_file).name}")
            except OSError as e:
                print(f"Warning: Could not remove {old_file}: {e}", file=sys.stderr)

    def collect_file_metrics(self, file_path: Path) -> dict:
        """Collect all radon metrics for a single Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
        except (UnicodeDecodeError, OSError) as e:
            print(f"Warning: Could not read {file_path}: {e}", file=sys.stderr)
            return None

        metrics = {
            'file': str(file_path.relative_to(self.base_path.parent)),
            'timestamp': self.timestamp
        }

        # Raw metrics (LOC, SLOC, comments, etc.)
        try:
            raw = analyze(code)
            metrics.update({
                'raw': {
                    'loc': raw.loc,
                    'sloc': raw.sloc,
                    'comments': raw.comments,
                    'multi': raw.multi,
                    'blank': raw.blank
                }
            })
        except Exception as e:
            print(f"Warning: Could not analyze raw metrics for {file_path}: {e}", file=sys.stderr)
            metrics['raw'] = None

        # Cyclomatic Complexity
        try:
            cc_results = cc_visit(code)
            cc_data = []
            for result in cc_results:
                endline = getattr(result, 'endline', getattr(result, 'endlineno', None))
                cc_data.append({
                    'name': getattr(result, 'name', None),
                    'complexity': getattr(result, 'complexity', 0),
                    'lineno': getattr(result, 'lineno', None),
                    'col_offset': getattr(result, 'col_offset', None),
                    'endline': endline,
                    'type': result.__class__.__name__
                })

            metrics['cyclomatic_complexity'] = {
                'functions': cc_data,
                'summary': {
                    'total_functions': len(cc_data),
                    'average_complexity': sum(r['complexity'] for r in cc_data) / len(cc_data) if cc_data else 0,
                    'max_complexity': max((r['complexity'] for r in cc_data), default=0),
                    'complexity_distribution': self._get_complexity_distribution(cc_data)
                }
            }
        except Exception as e:
            print(f"Warning: Could not analyze CC for {file_path}: {e}", file=sys.stderr)
            metrics['cyclomatic_complexity'] = None

        # Halstead Metrics
        try:
            h_results = h_visit(code)
            total = getattr(h_results, 'total', None)
            if total is not None:
                metrics['halstead'] = {
                    'h1': total.h1,  # Distinct operators
                    'h2': total.h2,  # Distinct operands
                    'N1': total.N1,  # Total operators
                    'N2': total.N2,  # Total operands
                    'vocabulary': total.vocabulary,
                    'length': total.length,
                    'volume': total.volume,
                    'difficulty': total.difficulty,
                    'effort': total.effort,
                    'time': total.time,
                    'bugs': total.bugs
                }
            else:
                metrics['halstead'] = None
        except Exception as e:
            print(f"Warning: Could not analyze Halstead metrics for {file_path}: {e}", file=sys.stderr)
            metrics['halstead'] = None

        # Maintainability Index
        try:
            mi_score = mi_visit(code, multi=False)
            metrics['maintainability_index'] = mi_score
        except Exception as e:
            print(f"Warning: Could not analyze MI for {file_path}: {e}", file=sys.stderr)
            metrics['maintainability_index'] = None

        return metrics

    def _get_complexity_distribution(self, cc_data):
        """Get distribution of complexity levels."""
        distribution = {'low': 0, 'medium': 0, 'high': 0, 'very_high': 0}

        for item in cc_data:
            cc = item['complexity']
            if cc <= 5:
                distribution['low'] += 1
            elif cc <= 10:
                distribution['medium'] += 1
            elif cc <= 20:
                distribution['high'] += 1
            else:
                distribution['very_high'] += 1

        return distribution

    def analyze_app(self, app_name: str) -> dict:
        """Analyze all Python files in a Django app."""
        app_path = self.base_path / app_name
        app_metrics = {
            'app': app_name,
            'timestamp': self.timestamp,
            'files': [],
            'summary': {
                'total_files': 0,
                'total_functions': 0,
                'cc_average': 0,
                'cc_max': 0,
                'mi_average': 0,
                'mi_min': float('inf'),
                'halstead_avg_volume': 0,
                'halstead_avg_difficulty': 0,
                'halstead_avg_effort': 0
            }
        }

        cc_values = []
        mi_values = []
        halstead_volumes = []
        halstead_difficulties = []
        halstead_efforts = []

        # Walk through all Python files
        for py_file in app_path.rglob('*.py'):
            # Skip migrations, __pycache__, and test files in CI
            if any(skip in str(py_file) for skip in ['migrations', '__pycache__', '/tests/']):
                continue

            file_metrics = self.collect_file_metrics(py_file)
            if file_metrics:
                app_metrics['files'].append(file_metrics)

                # Aggregate metrics
                if file_metrics['cyclomatic_complexity']:
                    cc_data = file_metrics['cyclomatic_complexity']['functions']
                    cc_values.extend([f['complexity'] for f in cc_data])
                    app_metrics['summary']['total_functions'] += len(cc_data)

                if file_metrics['maintainability_index'] is not None:
                    mi_values.append(file_metrics['maintainability_index'])

                if file_metrics['halstead']:
                    halstead_volumes.append(file_metrics['halstead']['volume'])
                    halstead_difficulties.append(file_metrics['halstead']['difficulty'])
                    halstead_efforts.append(file_metrics['halstead']['effort'])

        # Calculate summary statistics
        app_metrics['summary']['total_files'] = len(app_metrics['files'])

        if cc_values:
            app_metrics['summary']['cc_average'] = sum(cc_values) / len(cc_values)
            app_metrics['summary']['cc_max'] = max(cc_values)

        if mi_values:
            app_metrics['summary']['mi_average'] = sum(mi_values) / len(mi_values)
            app_metrics['summary']['mi_min'] = min(mi_values)
        else:
            app_metrics['summary']['mi_min'] = 0

        if halstead_volumes:
            app_metrics['summary']['halstead_avg_volume'] = sum(halstead_volumes) / len(halstead_volumes)
            app_metrics['summary']['halstead_avg_difficulty'] = sum(halstead_difficulties) / len(halstead_difficulties)
            app_metrics['summary']['halstead_avg_effort'] = sum(halstead_efforts) / len(halstead_efforts)

        return app_metrics

    def run_analysis(self, keep_historical: bool = False):
        """Run complete analysis for all apps and generate JSON artifacts."""
        print("Starting AquaMind CI Metrics Collection...")
        print(f"Timestamp: {self.timestamp}")

        # Set the keep_historical flag
        self.keep_historical = keep_historical

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Clean up old files unless keeping historical data
        if not keep_historical:
            print("Cleaning up old metrics files...")
            self.cleanup_old_files("backend_radon_*.json")

        all_results = {
            'project': 'aquamind-backend',
            'timestamp': self.timestamp,
            'generated_at': datetime.now().isoformat(),
            'apps': []
        }

        # Analyze each app
        for app in DJANGO_APPS:
            print(f"Analyzing {app}...")
            try:
                app_metrics = self.analyze_app(app)
                all_results['apps'].append(app_metrics)

                # Save individual app results
                filename = f"backend_radon_{app}_{self.timestamp}.json" if self.keep_historical else f"backend_radon_{app}.json"
                app_output_file = self.output_dir / filename
                with open(app_output_file, 'w', encoding='utf-8') as f:
                    json.dump(app_metrics, f, indent=2, ensure_ascii=False)
                print(f"Saved {app} metrics to {app_output_file}")

            except Exception as e:
                print(f"Error analyzing {app}: {e}", file=sys.stderr)
                continue

        # Generate aggregated reports
        self._generate_aggregated_reports(all_results)

        print(f"CI Metrics collection completed. Artifacts saved to {self.output_dir}")
        return all_results

    def _generate_aggregated_reports(self, all_results):
        """Generate aggregated JSON reports for different metric types."""

        # Cyclomatic Complexity report
        cc_report = {
            'project': 'aquamind-backend',
            'timestamp': self.timestamp,
            'metric_type': 'cyclomatic_complexity',
            'apps': []
        }

        # Maintainability Index report
        mi_report = {
            'project': 'aquamind-backend',
            'timestamp': self.timestamp,
            'metric_type': 'maintainability_index',
            'apps': []
        }

        # Halstead Metrics report
        hal_report = {
            'project': 'aquamind-backend',
            'timestamp': self.timestamp,
            'metric_type': 'halstead',
            'apps': []
        }

        # Raw Metrics report
        raw_report = {
            'project': 'aquamind-backend',
            'timestamp': self.timestamp,
            'metric_type': 'raw',
            'apps': []
        }

        for app_data in all_results['apps']:
            # CC aggregation
            cc_summary = {
                'app': app_data['app'],
                'summary': app_data['summary']
            }
            cc_report['apps'].append(cc_summary)

            # MI aggregation
            mi_summary = {
                'app': app_data['app'],
                'mi_average': app_data['summary']['mi_average'],
                'mi_min': app_data['summary']['mi_min']
            }
            mi_report['apps'].append(mi_summary)

            # Halstead aggregation
            hal_summary = {
                'app': app_data['app'],
                'halstead_avg_volume': app_data['summary']['halstead_avg_volume'],
                'halstead_avg_difficulty': app_data['summary']['halstead_avg_difficulty'],
                'halstead_avg_effort': app_data['summary']['halstead_avg_effort']
            }
            hal_report['apps'].append(hal_summary)

            # Raw metrics aggregation
            total_loc = sum(f.get('raw', {}).get('loc', 0) for f in app_data['files'] if f.get('raw'))
            total_sloc = sum(f.get('raw', {}).get('sloc', 0) for f in app_data['files'] if f.get('raw'))
            total_comments = sum(f.get('raw', {}).get('comments', 0) for f in app_data['files'] if f.get('raw'))

            raw_summary = {
                'app': app_data['app'],
                'total_loc': total_loc,
                'total_sloc': total_sloc,
                'total_comments': total_comments,
                'total_files': app_data['summary']['total_files']
            }
            raw_report['apps'].append(raw_summary)

        # Save aggregated reports
        reports = [
            ('backend_radon_cc', cc_report),
            ('backend_radon_mi', mi_report),
            ('backend_radon_hal', hal_report),
            ('backend_radon_raw', raw_report)
        ]

        for filename, report in reports:
            full_filename = f"{filename}_{self.timestamp}.json" if self.keep_historical else f"{filename}.json"
            output_file = self.output_dir / full_filename
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"Saved {filename} report to {output_file}")


def main():
    """Main entry point for CI metrics collection."""
    import argparse

    parser = argparse.ArgumentParser(description='Run radon metrics collection for CI')
    parser.add_argument('--output-dir', default='aquamind/docs/metrics',
                       help='Output directory for JSON artifacts')
    parser.add_argument('--base-path', default='apps',
                       help='Base path for Django apps')
    parser.add_argument('--keep-historical', action='store_true',
                       help='Keep historical versions of metrics files instead of overwriting')

    args = parser.parse_args()

    collector = CIMetricsCollector(
        base_path=args.base_path,
        output_dir=args.output_dir
    )

    try:
        results = collector.run_analysis(keep_historical=args.keep_historical)
        print("✓ CI Metrics collection completed successfully")

        # Print summary
        print("\n📊 Summary:")
        for app_data in results['apps']:
            summary = app_data['summary']
            print(
                f"  {app_data['app']}: {summary['total_files']} files, "
                f"CC avg: {summary['cc_average']:.1f}, "
                f"CC max: {summary['cc_max']:.1f}, "
                f"MI avg: {summary['mi_average']:.1f}"
            )

        return 0

    except Exception as e:
        print(f"✗ CI Metrics collection failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
