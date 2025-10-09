#!/usr/bin/env python
"""
FishTalk to AquaMind Migration Validation Script
Version: 1.0
Date: December 2024

This script validates the migration by comparing source and target data.
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
import psycopg2
import pyodbc

# Add parent directory to path for Django imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')

import django
django.setup()

from django.db import connection
from django.db.models import Count, Sum, Q, F
from apps.batch.models import Batch, BatchContainerAssignment
from apps.inventory.models import FeedingEvent
from apps.health.models import JournalEntry, MortalityRecord

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('validation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MigrationValidator:
    """Validates FishTalk to AquaMind migration"""
    
    def __init__(self, config_file='migration_config.json'):
        """Initialize validator with configuration"""
        self.config = self.load_config(config_file)
        self.fishtalk_conn = None
        self.validation_results = {
            'passed': [],
            'failed': [],
            'warnings': []
        }
    
    def load_config(self, config_file):
        """Load configuration from JSON file"""
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Config file {config_file} not found")
            return {}
    
    def connect_fishtalk(self):
        """Connect to FishTalk database"""
        try:
            conn_str = (
                f"DRIVER={self.config['fishtalk']['driver']};"
                f"SERVER={self.config['fishtalk']['server']};"
                f"DATABASE={self.config['fishtalk']['database']};"
                f"UID={self.config['fishtalk']['uid']};"
                f"PWD={self.config['fishtalk']['pwd']}"
            )
            self.fishtalk_conn = pyodbc.connect(conn_str)
            logger.info("Connected to FishTalk database")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to FishTalk: {e}")
            return False
    
    def validate_record_counts(self):
        """Validate record counts between systems"""
        logger.info("Validating record counts...")
        
        cursor = self.fishtalk_conn.cursor()
        
        # Validate active batch counts
        cursor.execute("SELECT COUNT(*) FROM Project WHERE Status = 'Active'")
        fishtalk_batches = cursor.fetchone()[0]
        
        aquamind_batches = Batch.objects.filter(
            batch_number__startswith='FT-',
            status='ACTIVE'
        ).count()
        
        if fishtalk_batches == aquamind_batches:
            self.validation_results['passed'].append(
                f"Batch count matches: {fishtalk_batches}"
            )
        else:
            self.validation_results['failed'].append(
                f"Batch count mismatch - FishTalk: {fishtalk_batches}, AquaMind: {aquamind_batches}"
            )
        
        # Validate container assignment counts
        cursor.execute("""
            SELECT COUNT(*) 
            FROM Individual i
            JOIN Project p ON i.ProjectID = p.ProjectID
            WHERE p.Status = 'Active' AND i.Active = 1
        """)
        fishtalk_assignments = cursor.fetchone()[0]
        
        aquamind_assignments = BatchContainerAssignment.objects.filter(
            batch__batch_number__startswith='FT-',
            is_active=True
        ).count()
        
        tolerance = 0.05  # 5% tolerance
        if abs(fishtalk_assignments - aquamind_assignments) / fishtalk_assignments <= tolerance:
            self.validation_results['passed'].append(
                f"Container assignments within tolerance: FT={fishtalk_assignments}, AM={aquamind_assignments}"
            )
        else:
            self.validation_results['failed'].append(
                f"Container assignments exceed tolerance - FishTalk: {fishtalk_assignments}, AquaMind: {aquamind_assignments}"
            )
    
    def validate_biomass_totals(self):
        """Validate total biomass calculations"""
        logger.info("Validating biomass totals...")
        
        cursor = self.fishtalk_conn.cursor()
        
        # Get FishTalk total biomass
        cursor.execute("""
            SELECT SUM(TotalBiomass) 
            FROM Individual i
            JOIN Project p ON i.ProjectID = p.ProjectID
            WHERE p.Status = 'Active' AND i.Active = 1
        """)
        fishtalk_biomass = cursor.fetchone()[0] or 0
        
        # Get AquaMind total biomass
        aquamind_biomass = BatchContainerAssignment.objects.filter(
            batch__batch_number__startswith='FT-',
            is_active=True
        ).aggregate(total=Sum('biomass_kg'))['total'] or 0
        
        # Check within 2% tolerance
        tolerance = 0.02
        if fishtalk_biomass > 0:
            variance = abs(float(fishtalk_biomass) - float(aquamind_biomass)) / float(fishtalk_biomass)
            if variance <= tolerance:
                self.validation_results['passed'].append(
                    f"Biomass totals within {tolerance*100}% tolerance: "
                    f"FT={fishtalk_biomass:.2f}kg, AM={aquamind_biomass:.2f}kg"
                )
            else:
                self.validation_results['failed'].append(
                    f"Biomass variance {variance*100:.2f}% exceeds tolerance: "
                    f"FT={fishtalk_biomass:.2f}kg, AM={aquamind_biomass:.2f}kg"
                )
    
    def validate_feed_data(self):
        """Validate feed and feeding event data"""
        logger.info("Validating feed data...")
        
        cursor = self.fishtalk_conn.cursor()
        cutoff_date = self.config.get('migration', {}).get('cutoff_date', '2023-01-01')
        
        # Validate feeding event counts
        cursor.execute("""
            SELECT COUNT(*), SUM(Amount) 
            FROM Feeding
            WHERE FeedDate >= ?
        """, cutoff_date)
        fishtalk_count, fishtalk_amount = cursor.fetchone()
        
        aquamind_data = FeedingEvent.objects.filter(
            batch__batch_number__startswith='FT-',
            feeding_date__gte=cutoff_date
        ).aggregate(
            count=Count('id'),
            total=Sum('amount_kg')
        )
        
        # Check counts
        if fishtalk_count == aquamind_data['count']:
            self.validation_results['passed'].append(
                f"Feeding event count matches: {fishtalk_count}"
            )
        else:
            self.validation_results['warnings'].append(
                f"Feeding event count differs - FT: {fishtalk_count}, AM: {aquamind_data['count']}"
            )
        
        # Check total feed amount (within 1% tolerance)
        if fishtalk_amount and aquamind_data['total']:
            variance = abs(float(fishtalk_amount) - float(aquamind_data['total'])) / float(fishtalk_amount)
            if variance <= 0.01:
                self.validation_results['passed'].append(
                    f"Feed amounts within tolerance: {variance*100:.2f}%"
                )
            else:
                self.validation_results['warnings'].append(
                    f"Feed amount variance: {variance*100:.2f}%"
                )
    
    def validate_health_records(self):
        """Validate health and medical records"""
        logger.info("Validating health records...")
        
        cursor = self.fishtalk_conn.cursor()
        cutoff_date = self.config.get('migration', {}).get('cutoff_date', '2023-01-01')
        
        # Validate journal entries
        cursor.execute("""
            SELECT COUNT(*) 
            FROM HealthLog
            WHERE LogDate >= ?
        """, cutoff_date)
        fishtalk_logs = cursor.fetchone()[0]
        
        aquamind_logs = JournalEntry.objects.filter(
            batch__batch_number__startswith='FT-',
            entry_date__gte=cutoff_date
        ).count()
        
        if abs(fishtalk_logs - aquamind_logs) <= 10:  # Allow small variance
            self.validation_results['passed'].append(
                f"Health logs within tolerance: FT={fishtalk_logs}, AM={aquamind_logs}"
            )
        else:
            self.validation_results['warnings'].append(
                f"Health log variance: FT={fishtalk_logs}, AM={aquamind_logs}"
            )
    
    def validate_data_integrity(self):
        """Validate data integrity and relationships"""
        logger.info("Validating data integrity...")
        
        # Check for orphaned container assignments
        orphaned = BatchContainerAssignment.objects.filter(
            batch__batch_number__startswith='FT-'
        ).exclude(
            container__isnull=False
        ).count()
        
        if orphaned == 0:
            self.validation_results['passed'].append(
                "No orphaned container assignments found"
            )
        else:
            self.validation_results['failed'].append(
                f"Found {orphaned} orphaned container assignments"
            )
        
        # Check for batches without assignments
        unassigned = Batch.objects.filter(
            batch_number__startswith='FT-',
            status='ACTIVE'
        ).exclude(
            container_assignments__isnull=False
        ).count()
        
        if unassigned == 0:
            self.validation_results['passed'].append(
                "All active batches have container assignments"
            )
        else:
            self.validation_results['warnings'].append(
                f"Found {unassigned} batches without container assignments"
            )
    
    def validate_business_rules(self):
        """Validate business rules and constraints"""
        logger.info("Validating business rules...")
        
        # Check FCR values are reasonable
        unreasonable_fcr = BatchContainerAssignment.objects.filter(
            batch__batch_number__startswith='FT-'
        ).filter(
            Q(biomass_kg__lt=0) | Q(population_count__lt=0)
        ).count()
        
        if unreasonable_fcr == 0:
            self.validation_results['passed'].append(
                "All biomass and population values are valid"
            )
        else:
            self.validation_results['failed'].append(
                f"Found {unreasonable_fcr} assignments with invalid values"
            )
        
        # Check date consistency
        invalid_dates = Batch.objects.filter(
            batch_number__startswith='FT-',
            expected_end_date__lt=F('start_date')
        ).count()
        
        if invalid_dates == 0:
            self.validation_results['passed'].append(
                "All batch dates are consistent"
            )
        else:
            self.validation_results['failed'].append(
                f"Found {invalid_dates} batches with invalid date ranges"
            )
    
    def generate_validation_report(self):
        """Generate validation report"""
        logger.info("Generating validation report...")
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'passed': len(self.validation_results['passed']),
                'failed': len(self.validation_results['failed']),
                'warnings': len(self.validation_results['warnings'])
            },
            'details': self.validation_results,
            'recommendation': self.get_recommendation()
        }
        
        # Save report
        report_file = f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        print("\n" + "="*60)
        print("VALIDATION SUMMARY")
        print("="*60)
        print(f"✓ Passed:   {report['summary']['passed']}")
        print(f"✗ Failed:   {report['summary']['failed']}")
        print(f"⚠ Warnings: {report['summary']['warnings']}")
        print(f"\nRecommendation: {report['recommendation']}")
        print(f"\nDetailed report saved to: {report_file}")
        print("="*60)
        
        return report
    
    def get_recommendation(self):
        """Get migration recommendation based on validation results"""
        failed_count = len(self.validation_results['failed'])
        warning_count = len(self.validation_results['warnings'])
        
        if failed_count == 0:
            if warning_count == 0:
                return "Migration validated successfully. Ready for production cutover."
            elif warning_count < 5:
                return "Migration validated with minor warnings. Review warnings and proceed."
            else:
                return "Migration has several warnings. Review and address before cutover."
        elif failed_count < 3:
            return "Migration has critical issues. Address failures before proceeding."
        else:
            return "Migration validation failed. Do not proceed with cutover."
    
    def run_validation(self):
        """Execute all validation checks"""
        logger.info("="*60)
        logger.info("Starting Migration Validation")
        logger.info("="*60)
        
        try:
            # Connect to FishTalk
            if not self.connect_fishtalk():
                logger.error("Cannot proceed without FishTalk connection")
                return False
            
            # Run validation checks
            self.validate_record_counts()
            self.validate_biomass_totals()
            self.validate_feed_data()
            self.validate_health_records()
            self.validate_data_integrity()
            self.validate_business_rules()
            
            # Generate report
            report = self.generate_validation_report()
            
            # Return success if no critical failures
            return len(self.validation_results['failed']) == 0
            
        except Exception as e:
            logger.error(f"Validation failed: {e}", exc_info=True)
            return False
        
        finally:
            if self.fishtalk_conn:
                self.fishtalk_conn.close()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate FishTalk to AquaMind Migration')
    parser.add_argument('--config', default='migration_config.json',
                       help='Path to configuration file')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Run validation
    validator = MigrationValidator(args.config)
    success = validator.run_validation()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

