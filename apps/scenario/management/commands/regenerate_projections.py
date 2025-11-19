"""
Management command to regenerate scenario projections with corrected TGC formula.

Usage:
    python manage.py regenerate_projections --all
    python manage.py regenerate_projections --scenario 42
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from apps.scenario.models import Scenario
from apps.scenario.services.calculations.projection_engine import ProjectionEngine


class Command(BaseCommand):
    help = 'Regenerate scenario projections with corrected TGC formula'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Regenerate projections for all scenarios',
        )
        parser.add_argument(
            '--scenario',
            type=int,
            help='Scenario ID to regenerate',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Validate scenarios without saving projections',
        )

    def handle(self, *args, **options):
        if options['all']:
            scenarios = Scenario.objects.select_related(
                'tgc_model',
                'fcr_model',
                'mortality_model',
                'tgc_model__profile'
            ).all()
            self.stdout.write(f"Found {scenarios.count()} scenarios to regenerate")
        elif options['scenario']:
            try:
                scenario = Scenario.objects.select_related(
                    'tgc_model',
                    'fcr_model',
                    'mortality_model',
                    'tgc_model__profile'
                ).get(scenario_id=options['scenario'])
                scenarios = [scenario]
            except Scenario.DoesNotExist:
                raise CommandError(f"Scenario {options['scenario']} does not exist")
        else:
            raise CommandError("Must specify either --all or --scenario <id>")

        success_count = 0
        error_count = 0
        
        for scenario in scenarios:
            self.stdout.write(f"\nProcessing: {scenario.name} (ID: {scenario.scenario_id})")
            
            try:
                engine = ProjectionEngine(scenario)
                
                if engine.errors:
                    self.stdout.write(
                        self.style.ERROR(f"  ❌ Validation errors: {', '.join(engine.errors)}")
                    )
                    error_count += 1
                    continue
                
                result = engine.run_projection(
                    save_results=not options['dry_run'],
                    progress_callback=lambda p, msg: None  # Silent progress
                )
                
                if result['success']:
                    summary = result['summary']
                    
                    self.stdout.write(self.style.SUCCESS(f"  ✅ Success"))
                    self.stdout.write(f"     Duration: {summary['duration_days']} days")
                    self.stdout.write(
                        f"     Growth: {summary['initial_conditions']['weight']:.2f}g → "
                        f"{summary['final_conditions']['weight']:.2f}g"
                    )
                    self.stdout.write(
                        f"     Population: {summary['initial_conditions']['population']:,} → "
                        f"{summary['final_conditions']['population']:,}"
                    )
                    self.stdout.write(f"     Total Feed: {summary['feed_metrics']['total_feed_kg']:,.1f} kg")
                    self.stdout.write(f"     Average FCR: {summary['feed_metrics']['average_fcr']:.2f}")
                    
                    if result['warnings']:
                        self.stdout.write(self.style.WARNING(f"     Warnings: {len(result['warnings'])}"))
                        for warning in result['warnings'][:3]:  # Show first 3
                            self.stdout.write(f"       - {warning}")
                    
                    if not options['dry_run']:
                        projection_count = scenario.projections.count()
                        self.stdout.write(f"     Saved {projection_count} projection records")
                    
                    success_count += 1
                else:
                    self.stdout.write(
                        self.style.ERROR(f"  ❌ Failed: {', '.join(result['errors'])}")
                    )
                    error_count += 1
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"  ❌ Exception: {str(e)}")
                )
                error_count += 1

        # Summary
        self.stdout.write("\n" + "="*60)
        self.stdout.write(f"Total scenarios processed: {success_count + error_count}")
        self.stdout.write(self.style.SUCCESS(f"  ✅ Successful: {success_count}"))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f"  ❌ Failed: {error_count}"))
        
        if options['dry_run']:
            self.stdout.write(self.style.WARNING("\n⚠️  DRY RUN - No projections saved"))
        
        self.stdout.write("="*60)

