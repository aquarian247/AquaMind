#!/usr/bin/env python
"""
AquaMind Project Metrics Report Generator
Generates comprehensive complexity metrics for all Django apps
"""

import os
import json
import statistics
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Any

# Radon imports
from radon.complexity import cc_visit, cc_rank
from radon.metrics import h_visit, mi_visit
from radon.raw import analyze

# Django app directories
DJANGO_APPS = [
    'batch', 'broodstock', 'environmental', 'health', 
    'infrastructure', 'inventory', 'operational', 'scenario', 'users'
]

class MetricsCollector:
    def __init__(self, base_path: str = 'apps'):
        self.base_path = Path(base_path)
        self.metrics = defaultdict(lambda: defaultdict(list))
        
    def collect_file_metrics(self, file_path: Path) -> Dict[str, Any]:
        """Collect all metrics for a single Python file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # Raw metrics (LOC, SLOC, comments, etc.)
        raw = analyze(code)
        
        # Cyclomatic Complexity
        cc_results = cc_visit(code)
        cc_values = [result.complexity for result in cc_results]
        
        # Halstead Metrics
        try:
            h_results = h_visit(code)
            halstead = {
                'h1': h_results.h1,  # Distinct operators
                'h2': h_results.h2,  # Distinct operands
                'N1': h_results.N1,  # Total operators
                'N2': h_results.N2,  # Total operands
                'vocabulary': h_results.vocabulary,
                'length': h_results.length,
                'volume': h_results.volume,
                'difficulty': h_results.difficulty,
                'effort': h_results.effort,
                'time': h_results.time,
                'bugs': h_results.bugs
            }
        except:
            halstead = None
        
        # Maintainability Index
        try:
            mi_score = mi_visit(code, multi=False)
        except:
            mi_score = None
        
        return {
            'file': str(file_path),
            'loc': raw.loc,
            'sloc': raw.sloc,
            'comments': raw.comments,
            'multi': raw.multi,
            'blank': raw.blank,
            'cyclomatic_complexity': cc_values,
            'cc_average': statistics.mean(cc_values) if cc_values else 0,
            'cc_max': max(cc_values) if cc_values else 0,
            'halstead': halstead,
            'maintainability_index': mi_score,
            'functions': len(cc_results)
        }
    
    def analyze_app(self, app_name: str) -> Dict[str, Any]:
        """Analyze all Python files in a Django app."""
        app_path = self.base_path / app_name
        app_metrics = {
            'files': [],
            'total_loc': 0,
            'total_sloc': 0,
            'total_comments': 0,
            'total_blank': 0,
            'total_functions': 0,
            'cc_values': [],
            'mi_values': [],
            'halstead_volume': [],
            'halstead_difficulty': [],
            'halstead_effort': []
        }
        
        # Walk through all Python files
        for py_file in app_path.rglob('*.py'):
            # Skip migrations and __pycache__
            if 'migrations' in str(py_file) or '__pycache__' in str(py_file):
                continue
                
            try:
                file_metrics = self.collect_file_metrics(py_file)
                app_metrics['files'].append(file_metrics)
                
                # Aggregate metrics
                app_metrics['total_loc'] += file_metrics['loc']
                app_metrics['total_sloc'] += file_metrics['sloc']
                app_metrics['total_comments'] += file_metrics['comments']
                app_metrics['total_blank'] += file_metrics['blank']
                app_metrics['total_functions'] += file_metrics['functions']
                
                app_metrics['cc_values'].extend(file_metrics['cyclomatic_complexity'])
                
                if file_metrics['maintainability_index'] is not None:
                    app_metrics['mi_values'].append(file_metrics['maintainability_index'])
                
                if file_metrics['halstead']:
                    app_metrics['halstead_volume'].append(file_metrics['halstead']['volume'])
                    app_metrics['halstead_difficulty'].append(file_metrics['halstead']['difficulty'])
                    app_metrics['halstead_effort'].append(file_metrics['halstead']['effort'])
            except Exception as e:
                print(f"Error analyzing {py_file}: {e}")
        
        # Calculate aggregates
        if app_metrics['cc_values']:
            app_metrics['cc_average'] = statistics.mean(app_metrics['cc_values'])
            app_metrics['cc_max'] = max(app_metrics['cc_values'])
        else:
            app_metrics['cc_average'] = 0
            app_metrics['cc_max'] = 0
            
        if app_metrics['mi_values']:
            app_metrics['mi_average'] = statistics.mean(app_metrics['mi_values'])
            app_metrics['mi_min'] = min(app_metrics['mi_values'])
        else:
            app_metrics['mi_average'] = 0
            app_metrics['mi_min'] = 0
            
        if app_metrics['halstead_volume']:
            app_metrics['halstead_avg_volume'] = statistics.mean(app_metrics['halstead_volume'])
            app_metrics['halstead_avg_difficulty'] = statistics.mean(app_metrics['halstead_difficulty'])
            app_metrics['halstead_avg_effort'] = statistics.mean(app_metrics['halstead_effort'])
        else:
            app_metrics['halstead_avg_volume'] = 0
            app_metrics['halstead_avg_difficulty'] = 0
            app_metrics['halstead_avg_effort'] = 0
        
        return app_metrics
    
    def generate_markdown_report(self, output_file: str = 'METRICS_REPORT.md'):
        """Generate a comprehensive markdown report."""
        report = []
        report.append("# AquaMind Project Metrics Report")
        report.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("\n## Executive Summary")
        
        # Collect metrics for all apps
        all_metrics = {}
        total_project_metrics = {
            'total_loc': 0,
            'total_sloc': 0,
            'total_files': 0,
            'total_functions': 0,
            'cc_values': [],
            'mi_values': []
        }
        
        for app in DJANGO_APPS:
            print(f"Analyzing {app}...")
            metrics = self.analyze_app(app)
            all_metrics[app] = metrics
            
            # Aggregate project-wide
            total_project_metrics['total_loc'] += metrics['total_loc']
            total_project_metrics['total_sloc'] += metrics['total_sloc']
            total_project_metrics['total_files'] += len(metrics['files'])
            total_project_metrics['total_functions'] += metrics['total_functions']
            total_project_metrics['cc_values'].extend(metrics['cc_values'])
            total_project_metrics['mi_values'].extend(metrics['mi_values'])
        
        # Project-wide summary
        report.append("\n### Project-Wide Metrics")
        report.append(f"- **Total Lines of Code:** {total_project_metrics['total_loc']:,}")
        report.append(f"- **Total Source Lines of Code (SLOC):** {total_project_metrics['total_sloc']:,}")
        report.append(f"- **Total Python Files Analyzed:** {total_project_metrics['total_files']}")
        report.append(f"- **Total Functions/Methods:** {total_project_metrics['total_functions']}")
        
        if total_project_metrics['cc_values']:
            report.append(f"- **Average Cyclomatic Complexity:** {statistics.mean(total_project_metrics['cc_values']):.2f}")
            report.append(f"- **Maximum Cyclomatic Complexity:** {max(total_project_metrics['cc_values'])}")
        
        if total_project_metrics['mi_values']:
            report.append(f"- **Average Maintainability Index:** {statistics.mean(total_project_metrics['mi_values']):.2f}")
        
        # App-level summary table
        report.append("\n### App Complexity Overview")
        report.append("\n| App | LOC | SLOC | Files | Avg CC | Max CC | Avg MI | Risk Level |")
        report.append("|-----|-----|------|-------|--------|--------|--------|------------|")
        
        for app in DJANGO_APPS:
            metrics = all_metrics[app]
            risk = self._assess_risk(metrics['cc_average'], metrics['mi_average'])
            report.append(f"| {app} | {metrics['total_loc']:,} | {metrics['total_sloc']:,} | "
                         f"{len(metrics['files'])} | {metrics['cc_average']:.2f} | "
                         f"{metrics['cc_max']} | {metrics['mi_average']:.2f} | {risk} |")
        
        # Detailed app analysis
        report.append("\n## Detailed App Analysis")
        
        for app in DJANGO_APPS:
            metrics = all_metrics[app]
            report.append(f"\n### {app.capitalize()} App")
            
            # Complexity Assessment
            report.append("\n#### Complexity Assessment")
            risk = self._assess_risk(metrics['cc_average'], metrics['mi_average'])
            report.append(f"- **Overall Risk Level:** {risk}")
            report.append(f"- **Total Lines of Code:** {metrics['total_loc']:,}")
            report.append(f"- **Source Lines of Code:** {metrics['total_sloc']:,}")
            report.append(f"- **Comment Lines:** {metrics['total_comments']:,}")
            report.append(f"- **Blank Lines:** {metrics['total_blank']:,}")
            report.append(f"- **Number of Files:** {len(metrics['files'])}")
            report.append(f"- **Number of Functions/Methods:** {metrics['total_functions']}")
            
            # Cyclomatic Complexity
            report.append("\n#### Cyclomatic Complexity")
            report.append(f"- **Average:** {metrics['cc_average']:.2f}")
            report.append(f"- **Maximum:** {metrics['cc_max']}")
            report.append(f"- **Interpretation:** {self._interpret_cc(metrics['cc_average'])}")
            
            # Find most complex functions
            complex_functions = self._find_complex_functions(metrics['files'])
            if complex_functions:
                report.append("\n**Most Complex Functions:**")
                for func in complex_functions[:5]:  # Top 5
                    report.append(f"- `{func['name']}` in `{func['file']}`: CC = {func['complexity']}")
            
            # Halstead Metrics
            if metrics['halstead_avg_volume'] > 0:
                report.append("\n#### Halstead Metrics (Averages)")
                report.append(f"- **Volume:** {metrics['halstead_avg_volume']:.2f} bits")
                report.append(f"- **Difficulty:** {metrics['halstead_avg_difficulty']:.2f}")
                report.append(f"- **Effort:** {metrics['halstead_avg_effort']:.2f}")
                report.append(f"- **Interpretation:** Higher values indicate more complex code that requires more effort to understand and maintain.")
            
            # Maintainability Index
            report.append("\n#### Maintainability Index")
            report.append(f"- **Average:** {metrics['mi_average']:.2f}")
            report.append(f"- **Minimum:** {metrics['mi_min']:.2f}")
            report.append(f"- **Interpretation:** {self._interpret_mi(metrics['mi_average'])}")
            
            # Recommendations
            report.append("\n#### Recommendations")
            recommendations = self._generate_recommendations(metrics)
            for rec in recommendations:
                report.append(f"- {rec}")
        
        # Overall recommendations
        report.append("\n## Overall Recommendations")
        report.append("\n### High Priority Refactoring Targets")
        
        # Find apps with highest complexity
        high_risk_apps = [(app, all_metrics[app]) for app in DJANGO_APPS 
                         if all_metrics[app]['cc_average'] > 10 or all_metrics[app]['mi_average'] < 65]
        
        if high_risk_apps:
            for app, metrics in sorted(high_risk_apps, key=lambda x: x[1]['cc_average'], reverse=True):
                report.append(f"- **{app}**: Average CC of {metrics['cc_average']:.2f}, MI of {metrics['mi_average']:.2f}")
        else:
            report.append("- All apps are within acceptable complexity thresholds.")
        
        # Methodology section
        report.append("\n## Methodology")
        report.append("\n### Metrics Explained")
        report.append("\n#### Cyclomatic Complexity (CC)")
        report.append("- **1-10:** Simple, low risk")
        report.append("- **11-20:** Moderate complexity, medium risk")
        report.append("- **21-50:** Complex, high risk")
        report.append("- **>50:** Very complex, untestable, very high risk")
        
        report.append("\n#### Maintainability Index (MI)")
        report.append("- **>85:** Highly maintainable")
        report.append("- **65-85:** Moderately maintainable")
        report.append("- **<65:** Difficult to maintain")
        
        report.append("\n#### Halstead Metrics")
        report.append("- **Volume:** Measures the size of the implementation")
        report.append("- **Difficulty:** Indicates how difficult the code is to write or understand")
        report.append("- **Effort:** Represents the mental effort required to develop or maintain the code")
        
        # Write report
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))
        
        print(f"\nReport generated: {output_file}")
    
    def _assess_risk(self, avg_cc: float, avg_mi: float) -> str:
        """Assess overall risk level based on metrics."""
        if avg_cc <= 5 and avg_mi >= 80:
            return "🟢 Low"
        elif avg_cc <= 10 and avg_mi >= 65:
            return "🟡 Medium"
        elif avg_cc <= 20 or avg_mi >= 50:
            return "🟠 High"
        else:
            return "🔴 Very High"
    
    def _interpret_cc(self, cc: float) -> str:
        """Interpret cyclomatic complexity value."""
        if cc <= 5:
            return "Simple, easy to test and maintain"
        elif cc <= 10:
            return "Moderate complexity, relatively easy to understand"
        elif cc <= 20:
            return "Complex, consider refactoring"
        else:
            return "Very complex, high priority for refactoring"
    
    def _interpret_mi(self, mi: float) -> str:
        """Interpret maintainability index."""
        if mi >= 85:
            return "Highly maintainable code"
        elif mi >= 65:
            return "Moderately maintainable"
        elif mi >= 50:
            return "Difficult to maintain, consider refactoring"
        else:
            return "Very difficult to maintain, high priority for refactoring"
    
    def _find_complex_functions(self, files: List[Dict]) -> List[Dict]:
        """Find the most complex functions across all files."""
        complex_funcs = []
        
        for file_metrics in files:
            with open(file_metrics['file'], 'r', encoding='utf-8') as f:
                code = f.read()
            
            cc_results = cc_visit(code)
            for result in cc_results:
                if result.complexity > 10:  # Only include complex functions
                    complex_funcs.append({
                        'name': result.name,
                        'file': Path(file_metrics['file']).name,
                        'complexity': result.complexity
                    })
        
        return sorted(complex_funcs, key=lambda x: x['complexity'], reverse=True)
    
    def _generate_recommendations(self, metrics: Dict) -> List[str]:
        """Generate specific recommendations based on metrics."""
        recommendations = []
        
        if metrics['cc_average'] > 10:
            recommendations.append("Consider breaking down complex functions into smaller, more manageable pieces")
        
        if metrics['cc_max'] > 20:
            recommendations.append(f"Priority refactoring needed for functions with CC > 20")
        
        if metrics['mi_average'] < 65:
            recommendations.append("Improve code documentation and reduce complexity to increase maintainability")
        
        if metrics['total_sloc'] / len(metrics['files']) > 300 and len(metrics['files']) > 0:
            recommendations.append("Consider splitting large modules into smaller, focused files")
        
        comment_ratio = metrics['total_comments'] / metrics['total_sloc'] if metrics['total_sloc'] > 0 else 0
        if comment_ratio < 0.1:
            recommendations.append("Increase code documentation - current comment ratio is below 10%")
        
        if not recommendations:
            recommendations.append("Code quality is good - maintain current standards")
        
        return recommendations


if __name__ == "__main__":
    collector = MetricsCollector()
    collector.generate_markdown_report() 