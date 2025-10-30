"""
Generate realistic health assessment test data.

This command creates HealthSamplingEvent records with IndividualFishObservation
and FishParameterScore data using the new normalized parameter scoring system.

Usage:
    python manage.py generate_health_assessments --count=40
    python manage.py generate_health_assessments --count=40 --include-biometrics
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
from random import randint, uniform, choices, random
from datetime import timedelta

from apps.health.models import (
    HealthParameter, HealthSamplingEvent, 
    IndividualFishObservation, FishParameterScore
)
from apps.batch.models import BatchContainerAssignment


class Command(BaseCommand):
    help = 'Generate realistic health assessment test data with parameter scoring'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=30,
            help='Number of assessment events to create (default: 30)'
        )
        parser.add_argument(
            '--fish-per-event',
            type=int,
            default=10,
            help='Average number of fish per assessment event (default: 10)'
        )
        parser.add_argument(
            '--include-biometrics',
            action='store_true',
            help='Include weight/length measurements in 30%% of assessments'
        )
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing health sampling events before generating new ones'
        )
    
    def handle(self, *args, **options):
        count = options['count']
        avg_fish = options['fish_per_event']
        include_biometrics_flag = options['include_biometrics']
        clear_existing = options['clear_existing']
        
        self.stdout.write(self.style.WARNING('\n' + '='*70))
        self.stdout.write(self.style.WARNING('Generating Health Assessment Test Data'))
        self.stdout.write(self.style.WARNING('='*70 + '\n'))
        
        # Clear existing data if requested
        if clear_existing:
            self.stdout.write('🗑️  Clearing existing health sampling events...')
            deleted_count = HealthSamplingEvent.objects.all().delete()[0]
            self.stdout.write(f'   Deleted {deleted_count} existing events\n')
        
        self.stdout.write('🔍 Fetching active batch assignments...')
        
        assignments = list(
            BatchContainerAssignment.objects.filter(
                is_active=True
            ).select_related('batch', 'container', 'lifecycle_stage')
            .order_by('-assignment_date')[:count]
        )
        
        if not assignments:
            self.stdout.write(self.style.ERROR('❌ No active batch assignments found'))
            return
        
        self.stdout.write(f'✓ Found {len(assignments)} assignments\n')
        
        # Verify parameters exist
        parameters = list(HealthParameter.objects.filter(is_active=True))
        if not parameters:
            self.stdout.write(self.style.ERROR(
                '❌ No health parameters found. Run: python manage.py populate_parameter_scores'
            ))
            return
        
        self.stdout.write(f'✓ Found {len(parameters)} active health parameters\n')
        
        self.stdout.write(f'🏥 Generating {len(assignments)} health assessments...\n')
        
        # Generate assessments
        created_count = 0
        total_fish = 0
        total_scores = 0
        
        for assignment in assignments:
            num_fish = randint(avg_fish - 5, avg_fish + 5)
            num_fish = max(5, num_fish)  # Minimum 5 fish
            
            # Weighted health profiles (most batches healthy)
            profile = choices(
                ['healthy', 'moderate', 'stressed'],
                weights=[0.70, 0.20, 0.10]
            )[0]
            
            # Maybe include biometrics
            include_bio = random() < 0.3 if include_biometrics_flag else False
            
            try:
                event = self._generate_event(
                    assignment, num_fish, parameters, profile, include_bio
                )
                
                created_count += 1
                total_fish += num_fish
                total_scores += num_fish * len(parameters)
                
                self.stdout.write(
                    f'  ✓ {assignment.batch.batch_number} / {assignment.container.name}: '
                    f'{num_fish} fish, {profile}'
                    f'{" (with biometrics)" if include_bio else ""}'
                )
            
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f'  ❌ {assignment.batch.batch_number}: {e}'
                ))
        
        # Summary
        self.stdout.write(self.style.WARNING('\n' + '='*70))
        self.stdout.write(self.style.SUCCESS('✅ Generation Complete!\n'))
        self.stdout.write(f'   Events created: {created_count}')
        self.stdout.write(f'   Fish assessed: {total_fish}')
        self.stdout.write(f'   Parameter scores: {total_scores}')
        self.stdout.write(f'   Avg scores per fish: {total_scores / total_fish if total_fish > 0 else 0:.1f}')
        self.stdout.write(self.style.WARNING('='*70 + '\n'))
    
    def _generate_event(self, assignment, num_fish, parameters, profile, include_bio):
        """Generate a single assessment event with fish observations and parameter scores."""
        
        # Create event
        days_ago = randint(1, 60)
        event = HealthSamplingEvent.objects.create(
            assignment=assignment,
            sampling_date=timezone.now().date() - timedelta(days=days_ago),
            number_of_fish_sampled=num_fish,
            notes=f'Veterinary assessment - {profile} batch'
        )
        
        # Score weights by profile
        weights_map = {
            'healthy':  [0.70, 0.25, 0.04, 0.01],  # Mostly 0s and 1s
            'moderate': [0.40, 0.40, 0.15, 0.05],  # Balanced
            'stressed': [0.10, 0.30, 0.40, 0.20],  # Higher scores
        }
        base_weights = weights_map[profile]
        
        # Generate fish observations
        for i in range(1, num_fish + 1):
            obs = IndividualFishObservation.objects.create(
                sampling_event=event,
                fish_identifier=str(i),
                weight_g=Decimal(uniform(150, 400)) if include_bio else None,
                length_cm=Decimal(uniform(18, 32)) if include_bio else None
            )
            
            # Score each parameter
            for param in parameters:
                score_range = list(range(param.min_score, param.max_score + 1))
                param_weights = base_weights[:len(score_range)]
                
                # Normalize weights
                total = sum(param_weights)
                param_weights = [w/total for w in param_weights]
                
                score = choices(score_range, weights=param_weights)[0]
                
                FishParameterScore.objects.create(
                    individual_fish_observation=obs,
                    parameter=param,
                    score=score
                )
        
        # Calculate aggregates if biometrics present
        if include_bio:
            event.calculate_aggregate_metrics()
        
        return event

