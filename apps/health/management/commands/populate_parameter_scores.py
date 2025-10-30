"""
Management command to populate ParameterScoreDefinition with 0-3 scale from existing parameters.

This command migrates the 9 standard health parameters from the legacy 1-5 scale
to the new normalized 0-3 scale using the ParameterScoreDefinition model.

Usage:
    python manage.py populate_parameter_scores
"""

from django.core.management.base import BaseCommand
from apps.health.models import HealthParameter, ParameterScoreDefinition


class Command(BaseCommand):
    help = 'Populate ParameterScoreDefinition with 0-3 scale from existing parameters'
    
    # Mapping of parameters with their 0-3 score definitions
    PARAMETERS = {
        'Gill Condition': [
            (0, 'Excellent', 'Healthy gills, pink color'),
            (1, 'Good', 'Slight mucus buildup'),
            (2, 'Fair', 'Moderate inflammation'),
            (3, 'Poor', 'Severe inflammation'),
        ],
        'Eye Condition': [
            (0, 'Excellent', 'Clear, bright eyes'),
            (1, 'Good', 'Slight cloudiness'),
            (2, 'Fair', 'Moderate cloudiness'),
            (3, 'Poor', 'Severe cloudiness/damage'),
        ],
        'Wounds/Lesions': [
            (0, 'Excellent', 'No wounds'),
            (1, 'Good', 'Minor abrasions'),
            (2, 'Fair', 'Moderate wounds'),
            (3, 'Poor', 'Severe wounds/ulcers'),
        ],
        'Fin Condition': [
            (0, 'Excellent', 'Intact, healthy fins'),
            (1, 'Good', 'Minor fraying'),
            (2, 'Fair', 'Moderate erosion'),
            (3, 'Poor', 'Severe erosion'),
        ],
        'Body Condition': [
            (0, 'Excellent', 'Robust, well-formed'),
            (1, 'Good', 'Slight deformities'),
            (2, 'Fair', 'Moderate deformities'),
            (3, 'Poor', 'Severe deformities'),
        ],
        'Swimming Behavior': [
            (0, 'Excellent', 'Active, normal swimming'),
            (1, 'Good', 'Slightly lethargic'),
            (2, 'Fair', 'Moderately lethargic'),
            (3, 'Poor', 'Severely impaired'),
        ],
        'Appetite': [
            (0, 'Excellent', 'Excellent feeding response'),
            (1, 'Good', 'Good appetite'),
            (2, 'Fair', 'Reduced appetite'),
            (3, 'Poor', 'Poor appetite'),
        ],
        'Mucous Membrane': [
            (0, 'Excellent', 'Normal mucus layer'),
            (1, 'Good', 'Slight excess mucus'),
            (2, 'Fair', 'Moderate excess mucus'),
            (3, 'Poor', 'Heavy excess mucus'),
        ],
        'Color/Pigmentation': [
            (0, 'Excellent', 'Normal coloration'),
            (1, 'Good', 'Slight color changes'),
            (2, 'Fair', 'Moderate discoloration'),
            (3, 'Poor', 'Severe discoloration'),
        ],
    }
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreation of score definitions even if they already exist',
        )
    
    def handle(self, *args, **options):
        force = options.get('force', False)
        
        self.stdout.write(self.style.WARNING('\n' + '='*70))
        self.stdout.write(self.style.WARNING('Populating Health Parameter Score Definitions'))
        self.stdout.write(self.style.WARNING('='*70 + '\n'))
        
        # Check if parameters exist
        existing_params = HealthParameter.objects.filter(
            name__in=self.PARAMETERS.keys()
        )
        
        if existing_params.count() != len(self.PARAMETERS):
            missing = set(self.PARAMETERS.keys()) - set(existing_params.values_list('name', flat=True))
            self.stdout.write(
                self.style.ERROR(
                    f'\n❌ ERROR: Missing {len(missing)} parameters: {", ".join(missing)}\n'
                    f'   Expected 9 parameters, found {existing_params.count()}\n'
                    f'   Please ensure all health parameters exist before running this command.\n'
                )
            )
            return
        
        self.stdout.write(f'✓ Found all 9 health parameters\n')
        
        # Track statistics
        params_updated = 0
        definitions_created = 0
        definitions_skipped = 0
        
        # Process each parameter
        for param_name, scores in self.PARAMETERS.items():
            try:
                param = HealthParameter.objects.get(name=param_name)
                
                # Update parameter to 0-3 range
                param.min_score = 0
                param.max_score = 3
                param.description = f"Visual assessment of {param_name.lower()}"
                param.save()
                
                params_updated += 1
                
                # Create or update score definitions
                for score_value, label, description in scores:
                    # Check if definition already exists
                    existing = ParameterScoreDefinition.objects.filter(
                        parameter=param,
                        score_value=score_value
                    ).first()
                    
                    if existing and not force:
                        definitions_skipped += 1
                        continue
                    
                    if existing and force:
                        # Update existing
                        existing.label = label
                        existing.description = description
                        existing.display_order = score_value
                        existing.save()
                        self.stdout.write(
                            f'  ↻ Updated {param_name} score {score_value}: {label}'
                        )
                    else:
                        # Create new
                        ParameterScoreDefinition.objects.create(
                            parameter=param,
                            score_value=score_value,
                            label=label,
                            description=description,
                            display_order=score_value
                        )
                        self.stdout.write(
                            f'  + Created {param_name} score {score_value}: {label}'
                        )
                    
                    definitions_created += 1
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Populated {param_name} with {len(scores)} score definitions'
                    )
                )
            
            except HealthParameter.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'❌ Parameter not found: {param_name}')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Error processing {param_name}: {e}')
                )
        
        # Summary
        self.stdout.write(self.style.WARNING('\n' + '='*70))
        self.stdout.write(self.style.SUCCESS('✅ Population Complete!\n'))
        self.stdout.write(f'   Parameters updated: {params_updated}/9')
        self.stdout.write(f'   Score definitions created: {definitions_created}')
        
        if definitions_skipped > 0:
            self.stdout.write(
                self.style.WARNING(
                    f'   Score definitions skipped (already exist): {definitions_skipped}'
                )
            )
            self.stdout.write(
                self.style.WARNING(
                    f'   Use --force to recreate existing definitions'
                )
            )
        
        self.stdout.write(self.style.WARNING('='*70 + '\n'))
        
        # Verification
        total_definitions = ParameterScoreDefinition.objects.count()
        expected_definitions = 36  # 9 parameters × 4 scores
        
        self.stdout.write('\n📊 Verification:')
        self.stdout.write(f'   Total score definitions in database: {total_definitions}')
        self.stdout.write(f'   Expected for 9 parameters (0-3 scale): {expected_definitions}')
        
        if total_definitions == expected_definitions:
            self.stdout.write(self.style.SUCCESS('   ✓ Count matches! All definitions created.\n'))
        else:
            self.stdout.write(
                self.style.WARNING(
                    f'   ⚠ Count mismatch. Expected {expected_definitions}, got {total_definitions}\n'
                )
            )
        
        # Display sample
        self.stdout.write('\n📋 Sample Data:')
        sample_param = HealthParameter.objects.filter(name='Gill Condition').first()
        if sample_param:
            self.stdout.write(f'\n   {sample_param.name}:')
            self.stdout.write(f'   - Range: {sample_param.min_score}-{sample_param.max_score}')
            self.stdout.write(f'   - Description: {sample_param.description}')
            self.stdout.write(f'   - Score definitions:')
            
            for definition in sample_param.score_definitions.all().order_by('score_value'):
                self.stdout.write(
                    f'     {definition.score_value}: {definition.label} - {definition.description}'
                )
        
        self.stdout.write('')

