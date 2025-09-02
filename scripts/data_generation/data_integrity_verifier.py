#!/usr/bin/env python3
"""
AquaMind Data Integrity Verifier

Comprehensive verification script for AquaMind aquaculture management system.
Validates all data relationships, foreign keys, and business logic integrity.
Designed to run after each data generation session.

Author: AquaMind Data Generation Team
"""

import os
import sys
import django
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Set, Any

# Setup Django
sys.path.append('/Users/aquarian247/Projects/AquaMind')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
django.setup()

# Import models
from apps.infrastructure.models import (
    Geography, Area, FreshwaterStation, Hall, Container, ContainerType,
    Sensor, FeedContainer
)
from apps.batch.models import (
    Batch, BatchContainerAssignment, LifeCycleStage, Species,
    MortalityEvent, GrowthSample
)
from apps.inventory.models import (
    Feed, FeedPurchase, FeedStock, FeedingEvent, FeedContainerStock
)
from apps.environmental.models import (
    EnvironmentalParameter, EnvironmentalReading, WeatherData
)
from apps.health.models import (
    JournalEntry, HealthSamplingEvent, IndividualFishObservation,
    MortalityRecord, Treatment, HealthLabSample
)

class DataIntegrityVerifier:
    """Comprehensive data integrity verification for AquaMind."""

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.stats = defaultdict(int)
        self.relationships = defaultdict(set)

    def log_error(self, message: str, details: Dict = None):
        """Log an error with optional details."""
        self.errors.append({
            'message': message,
            'details': details or {},
            'timestamp': datetime.now()
        })
        print(f"❌ ERROR: {message}")

    def log_warning(self, message: str, details: Dict = None):
        """Log a warning with optional details."""
        self.warnings.append({
            'message': message,
            'details': details or {},
            'timestamp': datetime.now()
        })
        print(f"⚠️  WARNING: {message}")

    def log_success(self, message: str):
        """Log a success message."""
        print(f"✅ {message}")

    def verify_geography_hierarchy(self):
        """Verify geography → freshwater stations → halls → containers hierarchy."""
        print("\n🏗️  VERIFYING GEOGRAPHY HIERARCHY")

        # Check geography exists
        geographies = Geography.objects.all()
        if not geographies.exists():
            self.log_error("No geographies found")
            return

        for geo in geographies:
            self.log_success(f"Geography: {geo.name}")

            # Check freshwater stations in geography
            stations = FreshwaterStation.objects.filter(geography=geo)
            self.stats['freshwater_stations'] += stations.count()

            for station in stations:
                self.log_success(f"  └─ Freshwater Station: {station.name}")

                # Check halls in station
                halls = Hall.objects.filter(freshwater_station=station)
                self.stats['halls'] += halls.count()

                for hall in halls:
                    self.log_success(f"    └─ Hall: {hall.name}")

                    # Check containers in hall
                    containers = Container.objects.filter(hall=hall)
                    self.stats['containers_in_halls'] += containers.count()

                    for container in containers:
                        self.log_success(f"      └─ Container: {container.name} ({container.container_type.name})")
                        self.relationships['hall_containers'].add(container.id)

    def verify_area_containers(self):
        """Verify areas contain containers."""
        print("\n🌊 VERIFYING AREA CONTAINERS")

        areas = Area.objects.all()
        if not areas.exists():
            self.log_warning("No areas found")
            return

        for area in areas:
            self.log_success(f"Area: {area.name} ({area.geography.name})")

            # Check containers in area
            containers = Container.objects.filter(area=area)
            self.stats['containers_in_areas'] += containers.count()

            for container in containers:
                self.log_success(f"  └─ Container: {container.name} ({container.container_type.name})")
                self.relationships['area_containers'].add(container.id)

    def verify_container_assignments(self):
        """Verify batch container assignments and lifecycle progression."""
        print("\n🐟 VERIFYING BATCH CONTAINER ASSIGNMENTS")

        assignments = BatchContainerAssignment.objects.select_related(
            'batch', 'container', 'lifecycle_stage'
        ).all()

        if not assignments.exists():
            self.log_error("No batch container assignments found")
            return

        batch_containers = defaultdict(set)
        batch_stages = defaultdict(set)

        for assignment in assignments:
            batch = assignment.batch
            container = assignment.container
            stage = assignment.lifecycle_stage

            # Track relationships
            batch_containers[batch.id].add(container.id)
            batch_stages[batch.id].add(stage.name)

            # Validate assignment dates
            if assignment.assignment_date > date.today():
                self.log_error(
                    f"Future assignment date: {batch.batch_number} assigned {assignment.assignment_date}",
                    {'batch': batch.batch_number, 'date': assignment.assignment_date}
                )

            # Validate weights
            if assignment.avg_weight_g and assignment.avg_weight_g <= 0:
                self.log_error(
                    f"Invalid weight: {batch.batch_number} has {assignment.avg_weight_g}g",
                    {'batch': batch.batch_number, 'weight': assignment.avg_weight_g}
                )

            # Validate population
            if assignment.population_count <= 0:
                self.log_error(
                    f"Invalid population: {batch.batch_number} has {assignment.population_count} fish",
                    {'batch': batch.batch_number, 'population': assignment.population_count}
                )

        # Check batch distribution
        for batch_id, containers in batch_containers.items():
            batch = Batch.objects.get(id=batch_id)
            self.log_success(f"Batch {batch.batch_number}: {len(containers)} containers, stages: {batch_stages[batch_id]}")

        self.stats['total_assignments'] = assignments.count()
        self.stats['unique_batches'] = len(batch_containers)

    def verify_feed_chain(self):
        """Verify feed purchase → stock → feeding events chain."""
        print("\n🍽️  VERIFYING FEED CHAIN")

        # Check feed purchases
        purchases = FeedPurchase.objects.select_related('feed').all()
        if not purchases.exists():
            self.log_warning("No feed purchases found")
            return

        total_purchased = Decimal('0')
        for purchase in purchases:
            total_purchased += purchase.quantity_kg
            self.log_success(f"Feed Purchase: {purchase.feed.name} - {purchase.quantity_kg}kg from {purchase.supplier}")

        # Check feed stock levels
        stocks = FeedStock.objects.select_related('feed', 'feed_container').all()
        total_stock = Decimal('0')

        for stock in stocks:
            total_stock += stock.current_quantity_kg
            self.log_success(f"Feed Stock: {stock.feed.name} in {stock.feed_container.name} - {stock.current_quantity_kg}kg")

            # Verify stock doesn't exceed container capacity
            if stock.current_quantity_kg > stock.feed_container.capacity_kg:
                self.log_error(
                    f"Stock exceeds capacity: {stock.feed_container.name} has {stock.current_quantity_kg}kg but capacity is {stock.feed_container.capacity_kg}kg",
                    {'container': stock.feed_container.name, 'stock': stock.current_quantity_kg, 'capacity': stock.feed_container.capacity_kg}
                )

        # Check feeding events
        feeding_events = FeedingEvent.objects.select_related(
            'batch', 'container', 'feed', 'batch_assignment'
        ).all()

        total_consumed = Decimal('0')
        for event in feeding_events:
            total_consumed += event.amount_kg
            self.log_success(f"Feeding Event: {event.batch.batch_number} fed {event.amount_kg}kg {event.feed.name}")

        # Verify mass balance
        expected_remaining = total_purchased - total_consumed
        discrepancy = abs(expected_remaining - total_stock)

        if discrepancy > Decimal('1'):  # Allow for small rounding differences
            self.log_warning(
                f"Feed mass balance issue: Purchased {total_purchased}kg, consumed {total_consumed}kg, remaining stock {total_stock}kg (discrepancy: {discrepancy}kg)",
                {'purchased': total_purchased, 'consumed': total_consumed, 'stock': total_stock, 'discrepancy': discrepancy}
            )
        else:
            self.log_success(f"Feed mass balance OK: {discrepancy}kg discrepancy")

        self.stats['feed_purchases'] = purchases.count()
        self.stats['feeding_events'] = feeding_events.count()
        self.stats['total_feed_purchased'] = total_purchased
        self.stats['total_feed_consumed'] = total_consumed

    def verify_environmental_monitoring(self):
        """Verify sensors and environmental readings."""
        print("\n🌡️  VERIFYING ENVIRONMENTAL MONITORING")

        # Check sensors
        sensors = Sensor.objects.select_related('container').all()
        if not sensors.exists():
            self.log_warning("No sensors found")
            return

        sensor_containers = set()
        for sensor in sensors:
            sensor_containers.add(sensor.container.id)
            self.log_success(f"Sensor: {sensor.name} ({sensor.sensor_type}) on {sensor.container.name}")

        # Check environmental readings
        readings = EnvironmentalReading.objects.select_related(
            'container', 'parameter'
        ).all()

        if readings.exists():
            # Check readings are linked to containers
            reading_containers = set()
            parameters = set()

            for reading in readings[:1000]:  # Sample first 1000 for performance
                reading_containers.add(reading.container.id)
                parameters.add(reading.parameter.name)

                # Validate reading values are reasonable
                if reading.parameter.name == 'temperature' and not (0 <= reading.value <= 40):
                    self.log_error(
                        f"Unrealistic temperature: {reading.value}°C in {reading.container.name}",
                        {'container': reading.container.name, 'value': reading.value}
                    )

                if reading.parameter.name == 'dissolved_oxygen' and not (0 <= reading.value <= 20):
                    self.log_error(
                        f"Unrealistic dissolved oxygen: {reading.value}mg/L in {reading.container.name}",
                        {'container': reading.container.name, 'value': reading.value}
                    )

            self.log_success(f"Environmental readings: {readings.count()} total")
            self.log_success(f"Parameters monitored: {', '.join(sorted(parameters))}")
            self.log_success(f"Containers with readings: {len(reading_containers)}")

            # Check if all sensor containers have readings
            containers_without_readings = sensor_containers - reading_containers
            if containers_without_readings:
                self.log_warning(
                    f"{len(containers_without_readings)} containers have sensors but no readings",
                    {'containers': list(containers_without_readings)}
                )

        self.stats['sensors'] = sensors.count()
        self.stats['environmental_readings'] = readings.count()

    def verify_health_records(self):
        """Verify health records and mortality events."""
        print("\n🏥 VERIFYING HEALTH RECORDS")

        # Check journal entries
        journals = JournalEntry.objects.select_related('batch', 'container').all()
        for journal in journals[:500]:  # Sample for performance
            self.log_success(f"Health Journal: {journal.category} for {journal.batch.batch_number}")

        # Check mortality records
        mortality_records = MortalityRecord.objects.select_related('batch', 'container').all()

        total_mortality = 0
        for record in mortality_records[:500]:
            total_mortality += record.count
            self.log_success(f"Mortality Record: {record.count} deaths in {record.batch.batch_number}")

        # Check lab samples
        lab_samples = HealthLabSample.objects.select_related('batch_container_assignment').all()
        for sample in lab_samples[:200]:
            self.log_success(f"Lab Sample: {sample.sample_type} for assignment {sample.batch_container_assignment.id}")

        # Verify mortality events vs batch populations
        assignments = BatchContainerAssignment.objects.filter(is_active=True)
        total_population = sum(assignment.population_count for assignment in assignments)

        if total_population > 0:
            mortality_rate = (total_mortality / total_population) * 100
            if mortality_rate > 20:  # More than 20% mortality is concerning
                self.log_warning(
                    f"High mortality rate: {mortality_rate:.1f}% ({total_mortality}/{total_population})",
                    {'mortality': total_mortality, 'population': total_population, 'rate': mortality_rate}
                )
            else:
                self.log_success(f"Mortality rate: {mortality_rate:.1f}%")

        self.stats['health_journals'] = journals.count()
        self.stats['mortality_records'] = mortality_records.count()
        self.stats['lab_samples'] = lab_samples.count()

    def verify_data_completeness(self):
        """Verify data completeness and relationships."""
        print("\n🔗 VERIFYING DATA COMPLETENESS")

        # Check for orphaned records
        orphaned_containers = Container.objects.filter(
            hall__isnull=True, area__isnull=True
        )
        if orphaned_containers.exists():
            self.log_error(
                f"{orphaned_containers.count()} containers not assigned to halls or areas",
                {'containers': [c.name for c in orphaned_containers]}
            )

        # Check assignments without active containers
        active_assignments = BatchContainerAssignment.objects.filter(is_active=True)
        inactive_assignments = BatchContainerAssignment.objects.filter(is_active=False)

        self.log_success(f"Active assignments: {active_assignments.count()}")
        self.log_success(f"Inactive assignments: {inactive_assignments.count()}")

        # Check feed containers without stock
        feed_containers = FeedContainer.objects.all()
        stocked_containers = FeedContainer.objects.filter(feed_stocks__isnull=False).distinct()

        empty_containers = feed_containers.exclude(id__in=stocked_containers.values_list('id', flat=True))
        if empty_containers.exists():
            self.log_warning(f"{empty_containers.count()} feed containers have no stock")

        # Check containers without sensors
        containers = Container.objects.all()
        containers_with_sensors = Container.objects.filter(sensors__isnull=False).distinct()

        sensorless_containers = containers.exclude(id__in=containers_with_sensors.values_list('id', flat=True))
        if sensorless_containers.exists():
            self.log_warning(f"{sensorless_containers.count()} containers have no sensors")

    def generate_report(self):
        """Generate comprehensive verification report."""
        print("\n" + "="*80)
        print("🎯 AQUAMIND DATA INTEGRITY VERIFICATION REPORT")
        print("="*80)

        # Summary statistics
        print("\n📊 SUMMARY STATISTICS:")
        print(f"   Geographies: {Geography.objects.count()}")
        print(f"   Areas: {Area.objects.count()}")
        print(f"   Freshwater Stations: {self.stats.get('freshwater_stations', 0)}")
        print(f"   Halls: {self.stats.get('halls', 0)}")
        print(f"   Containers: {Container.objects.count()}")
        print(f"   Sensors: {self.stats.get('sensors', 0)}")
        print(f"   Batches: {Batch.objects.count()}")
        print(f"   Batch Assignments: {self.stats.get('total_assignments', 0)}")
        print(f"   Environmental Readings: {self.stats.get('environmental_readings', 0)}")
        print(f"   Health Records: {self.stats.get('health_journals', 0)}")
        print(f"   Mortality Records: {self.stats.get('mortality_records', 0)}")
        print(f"   Feeding Events: {self.stats.get('feeding_events', 0)}")

        # Issues summary
        print(f"\n🚨 ISSUES FOUND:")
        print(f"   Errors: {len(self.errors)}")
        print(f"   Warnings: {len(self.warnings)}")

        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for i, error in enumerate(self.errors[:10], 1):  # Show first 10
                print(f"   {i}. {error['message']}")

        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for i, warning in enumerate(self.warnings[:10], 1):  # Show first 10
                print(f"   {i}. {warning['message']}")

        # Overall status
        if len(self.errors) == 0 and len(self.warnings) == 0:
            print(f"\n🎉 STATUS: PERFECT - All data integrity checks passed!")
        elif len(self.errors) == 0:
            print(f"\n✅ STATUS: GOOD - No errors, but {len(self.warnings)} warnings to review")
        else:
            print(f"\n❌ STATUS: ISSUES FOUND - {len(self.errors)} errors and {len(self.warnings)} warnings require attention")

        print("="*80)

    def run_full_verification(self):
        """Run complete data integrity verification."""
        print("🚀 Starting AquaMind Data Integrity Verification")
        print(f"Time: {datetime.now()}")

        try:
            # Run all verification checks
            self.verify_geography_hierarchy()
            self.verify_area_containers()
            self.verify_container_assignments()
            self.verify_feed_chain()
            self.verify_environmental_monitoring()
            self.verify_health_records()
            self.verify_data_completeness()

            # Generate final report
            self.generate_report()

            return len(self.errors) == 0

        except Exception as e:
            self.log_error(f"Verification failed with exception: {str(e)}")
            return False


def main():
    """Main verification function."""
    verifier = DataIntegrityVerifier()
    success = verifier.run_full_verification()

    if success:
        print("\n✅ Data integrity verification completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Data integrity verification found issues!")
        sys.exit(1)


if __name__ == "__main__":
    main()
