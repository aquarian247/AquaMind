"""
Management command to generate feed recommendations for testing purposes.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
import datetime

from apps.batch.models import BatchContainerAssignment
from apps.inventory.models import FeedRecommendation
from apps.inventory.services.feed_recommendation_service import FeedRecommendationService


class Command(BaseCommand):
    help = 'Generate feed recommendations for all active batch container assignments'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Target date for recommendations (YYYY-MM-DD)',
            required=False
        )
        parser.add_argument(
            '--container',
            type=int,
            help='Container ID to generate recommendations for (optional)',
            required=False
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force generation even if recommendations are disabled for the container',
            required=False
        )

    def handle(self, *args, **options):
        # Determine target date
        target_date = None
        if options['date']:
            try:
                target_date = datetime.datetime.strptime(options['date'], '%Y-%m-%d').date()
            except ValueError:
                self.stdout.write(self.style.ERROR(f"Invalid date format: {options['date']}. Use YYYY-MM-DD"))
                return
        else:
            target_date = timezone.now().date()

        container_id = options.get('container')
        
        self.stdout.write(
            self.style.WARNING(f"Generating feed recommendations for {target_date}")
        )

        # Use our service to generate recommendations
        if container_id:
            # Get container and check if feed recommendations are enabled
            from apps.infrastructure.models import Container
            try:
                container = Container.objects.get(id=container_id)
                if not container.feed_recommendations_enabled:
                    self.stdout.write(
                        self.style.ERROR(f"Feed recommendations are disabled for container ID {container_id}")
                    )
                    self.stdout.write(
                        self.style.WARNING(f"Use --force flag to override or enable recommendations for this container in the admin interface")
                    )
                    if not options.get('force'):
                        return
            except Container.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"Container with ID {container_id} not found")
                )
                return
                
            # Generate for a specific container
            assignments = BatchContainerAssignment.objects.filter(
                container_id=container_id,
                active=True
            )
            
            if not assignments.exists():
                self.stdout.write(
                    self.style.ERROR(f"No active batch assignments found for container ID {container_id}")
                )
                return
                
            self.stdout.write(
                self.style.WARNING(f"Generating recommendations for container ID {container_id}")
            )
            
            recommendations = FeedRecommendationService.create_recommendations_for_container(
                container_id, 
                target_date
            )
            
            self.stdout.write(
                self.style.SUCCESS(f"Generated {len(recommendations)} recommendations for container {container_id}")
            )
        else:
            # Generate for all active assignments that have recommendations enabled
            count = FeedRecommendationService.generate_all_recommendations(target_date)
            
            self.stdout.write(
                self.style.SUCCESS(f"Generated {count} recommendations for enabled containers with active assignments")
            )
            
            # Count how many containers have recommendations disabled
            from apps.infrastructure.models import Container
            disabled_count = Container.objects.filter(feed_recommendations_enabled=False).count()
            if disabled_count > 0:
                self.stdout.write(
                    self.style.WARNING(f"{disabled_count} containers have feed recommendations disabled")
                )
            
        # Print summary of recommendations
        recommendations = FeedRecommendation.objects.filter(recommended_date=target_date)
        
        if recommendations.exists():
            self.stdout.write(self.style.WARNING("\nRecommendation summary:"))
            for rec in recommendations:
                self.stdout.write(
                    f"- {rec.batch_container_assignment}: {rec.recommended_feed_kg} kg "
                    f"of {rec.feed.name} ({rec.feeding_percentage}% of biomass)"
                )
        else:
            self.stdout.write(self.style.WARNING("No recommendations were generated. Check if there are active assignments."))
