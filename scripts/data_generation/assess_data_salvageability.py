#!/usr/bin/env python3
"""
Data Salvageability Assessment

Quick script to assess which data can be salvaged vs needs regeneration.
Provides concrete metrics for decision-making.
"""

import os
import sys
from datetime import datetime, date
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
import django
django.setup()

from apps.batch.models import Batch, BatchContainerAssignment, LifeCycleStage
from apps.infrastructure.models import Container, Sensor, Area, FreshwaterStation
from apps.inventory.models import FeedingEvent, FeedPurchase
from apps.environmental.models import EnvironmentalReading
from apps.health.models import JournalEntry

class DataSalvageabilityAssessor:
    """Assess which data can be salvaged vs needs regeneration."""

    def __init__(self):
        self.assessment = {}

    def assess_infrastructure_salvageability(self):
        """Assess infrastructure data salvageability."""
        print("🏗️  ASSESSING INFRASTRUCTURE SALVAGEABILITY")

        # Container hierarchy integrity
        total_containers = Container.objects.count()
        containers_in_halls = Container.objects.filter(hall__isnull=False).count()
        containers_in_areas = Container.objects.filter(area__isnull=False).count()
        orphaned_containers = Container.objects.filter(
            hall__isnull=True, area__isnull=True
        ).count()

        hierarchy_integrity = (containers_in_halls + containers_in_areas) / total_containers * 100

        # Sensor coverage
        containers_with_sensors = Container.objects.filter(sensors__isnull=False).distinct().count()
        sensor_coverage = containers_with_sensors / total_containers * 100

        self.assessment['infrastructure'] = {
            'total_containers': total_containers,
            'hierarchy_integrity': hierarchy_integrity,
            'sensor_coverage': sensor_coverage,
            'orphaned_containers': orphaned_containers,
            'salvageable': hierarchy_integrity > 95,  # 95% integrity threshold
            'notes': f"{orphaned_containers} containers not properly assigned"
        }

        print(f"   Hierarchy Integrity: {hierarchy_integrity:.1f}%")
        print(f"   Sensor Coverage: {sensor_coverage:.1f}%")
        print(f"   Salvageable: {'✅ YES' if self.assessment['infrastructure']['salvageable'] else '❌ NO'}")

    def assess_batch_data_salvageability(self):
        """Assess batch data salvageability."""
        print("\n🐟 ASSESSING BATCH DATA SALVAGEABILITY")

        # Date validity assessment
        total_assignments = BatchContainerAssignment.objects.count()
        future_assignments = BatchContainerAssignment.objects.filter(
            assignment_date__gt=date.today()
        ).count()

        date_validity = (total_assignments - future_assignments) / total_assignments * 100

        # Stage progression assessment
        assignments_by_stage = {}
        for assignment in BatchContainerAssignment.objects.select_related('batch__lifecycle_stage'):
            stage = assignment.batch.lifecycle_stage.name
            assignments_by_stage[stage] = assignments_by_stage.get(stage, 0) + 1

        # Calculate stage distribution
        stage_distribution = "\\n".join([
            f"      {stage}: {count} assignments"
            for stage, count in sorted(assignments_by_stage.items())
        ])

        self.assessment['batch_data'] = {
            'total_assignments': total_assignments,
            'future_assignments': future_assignments,
            'date_validity': date_validity,
            'stage_distribution': stage_distribution,
            'salvageable': date_validity > 95,  # 95% date validity threshold
            'notes': f"{future_assignments} assignments have future dates"
        }

        print(f"   Date Validity: {date_validity:.1f}%")
        print(f"   Stage Distribution:\\n{stage_distribution}")
        print(f"   Salvageable: {'✅ YES' if self.assessment['batch_data']['salvageable'] else '❌ NO'}")

    def assess_feed_data_salvageability(self):
        """Assess feed data salvageability."""
        print("\n🍽️  ASSESSING FEED DATA SALVAGEABILITY")

        # Feed balance calculation
        purchases = FeedPurchase.objects.all()
        feeding_events = FeedingEvent.objects.all()

        total_purchased = sum(purchase.quantity_kg for purchase in purchases)
        total_consumed = sum(event.amount_kg for event in feeding_events)

        if total_purchased > 0:
            balance_ratio = float(total_consumed) / float(total_purchased)
            balance_discrepancy = abs(balance_ratio - 1.0) * 100
        else:
            balance_discrepancy = 100

        # Realistic FCR check (should be 1.0-1.5 for salmon)
        realistic_events = feeding_events.filter(
            amount_kg__gt=0,
            batch_assignment__isnull=False
        )

        fcr_realistic_count = 0
        for event in realistic_events[:1000]:  # Sample for performance
            if event.batch_assignment and event.batch_assignment.biomass_kg:
                biomass = float(event.batch_assignment.biomass_kg)
                feed_amount = float(event.amount_kg)
                fcr = feed_amount / biomass * 100  # Daily percentage

                if 0.5 <= fcr <= 3.0:  # Realistic daily feed percentage
                    fcr_realistic_count += 1

        fcr_realism = fcr_realistic_count / len(realistic_events) * 100 if realistic_events else 0

        self.assessment['feed_data'] = {
            'total_purchased': total_purchased,
            'total_consumed': total_consumed,
            'balance_discrepancy': balance_discrepancy,
            'fcr_realism': fcr_realism,
            'salvageable': balance_discrepancy < 20 and fcr_realism > 50,  # 20% discrepancy and 50% realistic FCR
            'notes': f"Balance discrepancy: {balance_discrepancy:.1f}%, FCR realism: {fcr_realism:.1f}%"
        }

        print(f"   Purchased: {total_purchased:,.0f} kg")
        print(f"   Consumed: {total_consumed:,.0f} kg")
        print(f"   Balance Discrepancy: {balance_discrepancy:.1f}%")
        print(f"   FCR Realism: {fcr_realism:.1f}%")
        print(f"   Salvageable: {'✅ YES' if self.assessment['feed_data']['salvageable'] else '❌ NO'}")

    def assess_environmental_data_salvageability(self):
        """Assess environmental data salvageability."""
        print("\n🌡️  ASSESSING ENVIRONMENTAL DATA SALVAGEABILITY")

        # Reading coverage
        total_containers = Container.objects.count()
        containers_with_readings = EnvironmentalReading.objects.values(
            'container'
        ).distinct().count()

        reading_coverage = containers_with_readings / total_containers * 100 if total_containers > 0 else 0

        # Data volume and quality
        total_readings = EnvironmentalReading.objects.count()
        recent_readings = EnvironmentalReading.objects.filter(
            reading_time__date=date.today()
        ).count()

        # Parameter diversity
        parameters = EnvironmentalReading.objects.values_list(
            'parameter__name', flat=True
        ).distinct()

        self.assessment['environmental_data'] = {
            'total_readings': total_readings,
            'reading_coverage': reading_coverage,
            'parameters_count': len(parameters),
            'parameters_list': list(parameters),
            'salvageable': reading_coverage > 70,  # 70% coverage threshold
            'notes': f"{reading_coverage:.1f}% containers have readings, {len(parameters)} parameters monitored"
        }

        print(f"   Total Readings: {total_readings:,}")
        print(f"   Reading Coverage: {reading_coverage:.1f}%")
        print(f"   Parameters: {', '.join(parameters)}")
        print(f"   Salvageable: {'✅ YES' if self.assessment['environmental_data']['salvageable'] else '❌ NO'}")

    def generate_salvageability_report(self):
        """Generate comprehensive salvageability report."""
        print("\n" + "="*80)
        print("📊 DATA SALVAGEABILITY ASSESSMENT REPORT")
        print("="*80)

        # Overall assessment
        salvageable_components = sum(
            1 for component in self.assessment.values()
            if component.get('salvageable', False)
        )
        total_components = len(self.assessment)

        print(f"\n🏆 OVERALL ASSESSMENT:")
        print(f"   Salvageable Components: {salvageable_components}/{total_components}")

        if salvageable_components == total_components:
            print("   Recommendation: ✅ FULL SALVAGE POSSIBLE")
        elif salvageable_components >= total_components * 0.7:
            print("   Recommendation: ⚠️  PARTIAL SALVAGE WITH TARGETED FIXES")
        else:
            print("   Recommendation: ❌ FULL REGENERATION REQUIRED")

        # Component breakdown
        print(f"\n🔍 COMPONENT BREAKDOWN:")
        for component_name, data in self.assessment.items():
            status = "✅ SALVAGEABLE" if data.get('salvageable') else "❌ NEEDS REGENERATION"
            print(f"   {component_name.replace('_', ' ').title()}: {status}")
            if data.get('notes'):
                print(f"      → {data['notes']}")

        # Action plan
        print(f"\n🎯 RECOMMENDED ACTION PLAN:")

        if not self.assessment.get('batch_data', {}).get('salvageable'):
            print("   1. 🚨 PRIORITY: Regenerate Session 4 batch assignments")
            print("      → Fix date calculation bugs in BatchManager")
            print("      → Clear future-dated assignments")

        if not self.assessment.get('feed_data', {}).get('salvageable'):
            print("   2. ⚠️  Fix feed mass balance")
            print("      → Recalibrate FCR values to realistic ranges")
            print("      → Adjust feeding event calculations")

        if not self.assessment.get('infrastructure', {}).get('salvageable'):
            print("   3. 🏗️  Fix infrastructure hierarchy")
            print("      → Reassign orphaned containers")
            print("      → Complete sensor coverage")

        print(f"\n📋 ESTIMATED TIMELINE:")
        print("   Assessment: Complete ✅")
        print("   Targeted Fixes: 4-6 hours")
        print("   Session Regeneration: 8-12 hours")
        print("   Validation: 2-4 hours")
        print("   Total: 14-22 hours")

        print("\n" + "="*80)

def main():
    """Main assessment function."""
    assessor = DataSalvageabilityAssessor()

    print("🔍 AquaMind Data Salvageability Assessment")
    print("==========================================")

    assessor.assess_infrastructure_salvageability()
    assessor.assess_batch_data_salvageability()
    assessor.assess_feed_data_salvageability()
    assessor.assess_environmental_data_salvageability()

    assessor.generate_salvageability_report()

if __name__ == "__main__":
    main()
