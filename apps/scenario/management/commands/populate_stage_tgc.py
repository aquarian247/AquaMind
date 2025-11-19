"""
Management command to populate stage-specific TGC values for existing TGC models.

Applies industry-standard stage-specific TGC values matching Event Engine implementation.

Usage:
    python manage.py populate_stage_tgc --all
    python manage.py populate_stage_tgc --model 42
"""
from django.core.management.base import BaseCommand, CommandError
from apps.scenario.models import TGCModel, TGCModelStage
from apps.batch.models import LifeCycleStage


class Command(BaseCommand):
    help = 'Populate stage-specific TGC values for TGC models'

    # Standard stage-specific TGC values (matches Event Engine)
    # Values are per 1000 degree-days
    STAGE_TGC_VALUES = {
        'Egg&Alevin': 0.0,      # No growth (yolk sac feeding)
        'Fry': 2.25,            # Early freshwater growth
        'Parr': 2.75,           # Freshwater growth phase
        'Smolt': 2.75,          # Smoltification
        'Post-Smolt': 3.25,     # Early seawater growth
        'Adult': 3.1,           # Grow-out to harvest
    }

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Populate stage TGC for all models',
        )
        parser.add_argument(
            '--model',
            type=int,
            help='TGC Model ID to populate',
        )
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='Overwrite existing stage overrides',
        )

    def handle(self, *args, **options):
        if options['all']:
            tgc_models = TGCModel.objects.all()
            self.stdout.write(f"Found {tgc_models.count()} TGC models")
        elif options['model']:
            try:
                tgc_model = TGCModel.objects.get(model_id=options['model'])
                tgc_models = [tgc_model]
            except TGCModel.DoesNotExist:
                raise CommandError(f"TGC Model {options['model']} does not exist")
        else:
            raise CommandError("Must specify either --all or --model <id>")

        # Get all lifecycle stages
        lifecycle_stages = {
            stage.name: stage
            for stage in LifeCycleStage.objects.all()
        }

        success_count = 0
        skip_count = 0
        
        for tgc_model in tgc_models:
            self.stdout.write(f"\nProcessing: {tgc_model.name}")
            
            # Check existing overrides
            existing_count = tgc_model.stage_overrides.count()
            
            if existing_count > 0 and not options['overwrite']:
                self.stdout.write(
                    self.style.WARNING(
                        f"  ⚠️  Skipped - {existing_count} stage overrides exist (use --overwrite to replace)"
                    )
                )
                skip_count += 1
                continue
            
            # Delete existing if overwrite
            if options['overwrite'] and existing_count > 0:
                tgc_model.stage_overrides.all().delete()
                self.stdout.write(f"  🗑️  Deleted {existing_count} existing overrides")
            
            # Create stage-specific TGC values
            created_count = 0
            for stage_name, tgc_value in self.STAGE_TGC_VALUES.items():
                if stage_name not in lifecycle_stages:
                    self.stdout.write(
                        self.style.WARNING(f"  ⚠️  Stage '{stage_name}' not found in database")
                    )
                    continue
                
                TGCModelStage.objects.create(
                    tgc_model=tgc_model,
                    lifecycle_stage=stage_name,
                    tgc_value=tgc_value,
                    temperature_exponent=1.0,  # Standard (not used in calculation)
                    weight_exponent=0.333      # Standard (not used in calculation)
                )
                created_count += 1
                self.stdout.write(f"    + {stage_name}: TGC {tgc_value}")
            
            self.stdout.write(self.style.SUCCESS(f"  ✅ Created {created_count} stage overrides"))
            success_count += 1

        # Summary
        self.stdout.write("\n" + "="*60)
        self.stdout.write(f"Total models processed: {success_count + skip_count}")
        self.stdout.write(self.style.SUCCESS(f"  ✅ Updated: {success_count}"))
        if skip_count > 0:
            self.stdout.write(self.style.WARNING(f"  ⚠️  Skipped: {skip_count}"))
        self.stdout.write("="*60)

