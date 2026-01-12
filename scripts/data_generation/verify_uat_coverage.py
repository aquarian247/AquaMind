#!/usr/bin/env python3
"""
UAT Test Data Coverage Verification

Validates that generated test data has proper stage distribution for UAT testing.

Checks:
- Active batches per lifecycle stage
- Batches near stage transition points
- Data freshness (events up to today)
- Coverage gaps

Usage:
    python verify_uat_coverage.py
    python verify_uat_coverage.py --verbose
"""
import os
import sys
import django
import argparse
from datetime import date, timedelta
from pathlib import Path
from collections import defaultdict

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
django.setup()

from apps.batch.models import Batch, ActualDailyAssignmentState, BatchContainerAssignment
from apps.batch.models import LifeCycleStage
from apps.inventory.models import FeedingEvent
from apps.environmental.models import EnvironmentalReading


# Stage boundaries (days from batch start)
STAGE_BOUNDARIES = {
    'Egg&Alevin': (1, 90),
    'Fry': (91, 180),
    'Parr': (181, 270),
    'Smolt': (271, 360),
    'Post-Smolt': (361, 450),
    'Adult': (451, 900),
}

# Transition points (near end of each stage)
TRANSITION_WINDOWS = {
    'Egg&Alevin→Fry': (82, 95),
    'Fry→Parr': (172, 185),
    'Parr→Smolt': (262, 275),
    'Smolt→Post-Smolt': (352, 365),  # Critical FW→Sea
    'Post-Smolt→Adult': (442, 455),
    'Adult→Harvest': (780, 900),
}

# UAT requirements
UAT_REQUIREMENTS = {
    'min_batches_per_stage': 4,
    'min_near_transition': 2,
    'max_data_staleness_days': 3,
    'min_total_active_batches': 30,
}


class UATCoverageVerifier:
    """Verifies UAT test data coverage."""
    
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.today = date.today()
        self.issues = []
        self.warnings = []
        
    def verify(self):
        """Run all verification checks."""
        print("\n" + "="*80)
        print("UAT TEST DATA COVERAGE VERIFICATION")
        print("="*80)
        print(f"\nToday's date: {self.today}")
        print()
        
        # Run checks
        self._check_batch_counts()
        self._check_stage_distribution()
        self._check_transition_coverage()
        self._check_data_freshness()
        self._check_growth_analysis_data()
        self._check_planned_activities()
        
        # Print summary
        self._print_summary()
        
        return len(self.issues) == 0
    
    def _check_batch_counts(self):
        """Check overall batch counts."""
        print("📊 Batch Counts")
        print("-" * 40)
        
        total = Batch.objects.count()
        active = Batch.objects.filter(status='ACTIVE').count()
        completed = Batch.objects.filter(status='COMPLETED').count()
        
        print(f"  Total batches: {total}")
        print(f"  Active: {active}")
        print(f"  Completed: {completed}")
        print()
        
        if active < UAT_REQUIREMENTS['min_total_active_batches']:
            self.issues.append(
                f"Insufficient active batches: {active} < {UAT_REQUIREMENTS['min_total_active_batches']}"
            )
    
    def _check_stage_distribution(self):
        """Check distribution of active batches across stages."""
        print("📍 Stage Distribution (Active Batches)")
        print("-" * 40)
        
        stage_counts = defaultdict(list)
        
        for batch in Batch.objects.filter(status='ACTIVE').select_related('lifecycle_stage'):
            # Calculate current lifecycle day
            days_elapsed = (self.today - batch.start_date).days
            stage_name = batch.lifecycle_stage.name if batch.lifecycle_stage else "Unknown"
            stage_counts[stage_name].append({
                'batch': batch.batch_number,
                'days': days_elapsed,
            })
        
        # Print distribution
        for stage_name in ['Egg&Alevin', 'Fry', 'Parr', 'Smolt', 'Post-Smolt', 'Adult']:
            batches = stage_counts.get(stage_name, [])
            count = len(batches)
            status = "✅" if count >= UAT_REQUIREMENTS['min_batches_per_stage'] else "⚠️"
            
            if self.verbose and batches:
                days_list = [b['days'] for b in batches]
                days_range = f"(Days: {min(days_list)}-{max(days_list)})"
            else:
                days_range = ""
            
            print(f"  {status} {stage_name}: {count} batches {days_range}")
            
            if count < UAT_REQUIREMENTS['min_batches_per_stage']:
                self.warnings.append(
                    f"Low batch count for {stage_name}: {count} < {UAT_REQUIREMENTS['min_batches_per_stage']}"
                )
        
        print()
    
    def _check_transition_coverage(self):
        """Check batches positioned near stage transitions."""
        print("🔄 Transition Coverage")
        print("-" * 40)
        
        transition_counts = defaultdict(list)
        
        for batch in Batch.objects.filter(status='ACTIVE'):
            days_elapsed = (self.today - batch.start_date).days
            
            # Check each transition window
            for transition, (start, end) in TRANSITION_WINDOWS.items():
                if start <= days_elapsed <= end:
                    transition_counts[transition].append({
                        'batch': batch.batch_number,
                        'days': days_elapsed,
                    })
        
        # Print transition coverage
        for transition, window in TRANSITION_WINDOWS.items():
            batches = transition_counts.get(transition, [])
            count = len(batches)
            status = "✅" if count >= UAT_REQUIREMENTS['min_near_transition'] else "⚠️"
            
            print(f"  {status} {transition}: {count} batches (Day {window[0]}-{window[1]})")
            
            if self.verbose and batches:
                for b in batches[:3]:
                    print(f"      - {b['batch']} (Day {b['days']})")
            
            if count < UAT_REQUIREMENTS['min_near_transition']:
                if 'Smolt→Post-Smolt' in transition:
                    self.issues.append(f"Critical FW→Sea transition needs more batches: {count}")
                else:
                    self.warnings.append(f"Low coverage for {transition}: {count}")
        
        print()
    
    def _check_data_freshness(self):
        """Check how recent the data is."""
        print("📅 Data Freshness")
        print("-" * 40)
        
        # Check ActualDailyAssignmentState
        try:
            latest_state = ActualDailyAssignmentState.objects.order_by('-date').first()
            if latest_state:
                staleness = (self.today - latest_state.date).days
                status = "✅" if staleness <= UAT_REQUIREMENTS['max_data_staleness_days'] else "❌"
                print(f"  {status} ActualDailyAssignmentState: {latest_state.date} ({staleness} days old)")
                
                if staleness > UAT_REQUIREMENTS['max_data_staleness_days']:
                    self.issues.append(f"Growth Analysis data is stale: {staleness} days old")
            else:
                print(f"  ❌ ActualDailyAssignmentState: No data")
                self.issues.append("No Growth Analysis data found")
        except Exception as e:
            print(f"  ⚠️ ActualDailyAssignmentState: Error checking - {e}")
        
        # Check FeedingEvent
        try:
            latest_feed = FeedingEvent.objects.order_by('-feeding_date').first()
            if latest_feed:
                staleness = (self.today - latest_feed.feeding_date).days
                status = "✅" if staleness <= UAT_REQUIREMENTS['max_data_staleness_days'] else "⚠️"
                print(f"  {status} FeedingEvent: {latest_feed.feeding_date} ({staleness} days old)")
            else:
                print(f"  ⚠️ FeedingEvent: No data")
        except Exception as e:
            print(f"  ⚠️ FeedingEvent: Error checking - {e}")
        
        # Check EnvironmentalReading
        try:
            latest_env = EnvironmentalReading.objects.order_by('-reading_time').first()
            if latest_env:
                staleness = (self.today - latest_env.reading_time.date()).days
                status = "✅" if staleness <= UAT_REQUIREMENTS['max_data_staleness_days'] else "⚠️"
                print(f"  {status} EnvironmentalReading: {latest_env.reading_time.date()} ({staleness} days old)")
            else:
                print(f"  ⚠️ EnvironmentalReading: No data")
        except Exception as e:
            print(f"  ⚠️ EnvironmentalReading: Error checking - {e}")
        
        print()
    
    def _check_growth_analysis_data(self):
        """Check Growth Analysis data per active batch."""
        print("📈 Growth Analysis Data")
        print("-" * 40)
        
        batches_with_data = 0
        batches_without_data = []
        
        for batch in Batch.objects.filter(status='ACTIVE')[:20]:  # Sample first 20
            state_count = ActualDailyAssignmentState.objects.filter(batch=batch).count()
            
            if state_count > 0:
                batches_with_data += 1
            else:
                batches_without_data.append(batch.batch_number)
        
        total_checked = min(20, Batch.objects.filter(status='ACTIVE').count())
        coverage = batches_with_data / total_checked * 100 if total_checked > 0 else 0
        
        status = "✅" if coverage >= 80 else "⚠️"
        print(f"  {status} Growth Analysis coverage: {batches_with_data}/{total_checked} batches ({coverage:.0f}%)")
        
        if batches_without_data and self.verbose:
            print(f"      Missing: {', '.join(batches_without_data[:5])}")
        
        if coverage < 80:
            self.warnings.append(f"Low Growth Analysis coverage: {coverage:.0f}%")
        
        print()
    
    def _check_planned_activities(self):
        """Check PlannedActivity records."""
        print("📋 Planned Activities")
        print("-" * 40)
        
        try:
            from apps.planning.models import PlannedActivity
            
            total = PlannedActivity.objects.count()
            pending = PlannedActivity.objects.filter(status='PENDING').count()
            
            # Check for overdue (pending past due date)
            overdue = PlannedActivity.objects.filter(
                status='PENDING',
                due_date__lt=self.today
            ).count()
            
            print(f"  Total activities: {total}")
            print(f"  Pending: {pending}")
            print(f"  Overdue: {overdue}")
            
            if total == 0:
                self.warnings.append("No PlannedActivity records - run seed_planned_activities.py")
            
        except Exception as e:
            print(f"  ⚠️ Could not check PlannedActivity: {e}")
        
        print()
    
    def _print_summary(self):
        """Print verification summary."""
        print("="*80)
        print("VERIFICATION SUMMARY")
        print("="*80)
        print()
        
        if self.issues:
            print("❌ ISSUES (must fix):")
            for issue in self.issues:
                print(f"   • {issue}")
            print()
        
        if self.warnings:
            print("⚠️ WARNINGS (review recommended):")
            for warning in self.warnings:
                print(f"   • {warning}")
            print()
        
        if not self.issues and not self.warnings:
            print("✅ All checks passed! Data is ready for UAT testing.")
        elif not self.issues:
            print("✅ No critical issues. Review warnings if needed.")
        else:
            print("❌ Critical issues found. Data may not be suitable for UAT.")
        
        print()


def main():
    parser = argparse.ArgumentParser(
        description='Verify UAT test data coverage'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed information'
    )
    
    args = parser.parse_args()
    
    verifier = UATCoverageVerifier(verbose=args.verbose)
    success = verifier.verify()
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
