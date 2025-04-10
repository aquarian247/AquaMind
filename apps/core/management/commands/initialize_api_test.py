from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from apps.infrastructure.models import Container
from apps.batch.models import BatchContainerAssignment
from django.utils import timezone

class Command(BaseCommand):
    help = 'Initialize API testing setup for feed recommendations'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, default='testuser', help='Username for test user')
        parser.add_argument('--password', type=str, default='password123', help='Password for test user')

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== Initializing AquaMind API Test Environment ==='))
        
        username = options['username']
        password = options['password']
        
        # Create or update test user
        user, created = User.objects.get_or_create(username=username)
        user.set_password(password)
        user.is_staff = True
        user.save()
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created test user: {username}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Updated existing user: {username}'))
        
        # Get or create auth token
        token, created = Token.objects.get_or_create(user=user)
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created new token for {username}'))
        
        self.stdout.write(self.style.SUCCESS(f'API Token: {token.key}'))
        self.stdout.write(self.style.SUCCESS(f'For frontend testing, run in browser console:'))
        self.stdout.write(self.style.SUCCESS(f'localStorage.setItem("token", "{token.key}")'))
        
        # Enable feed recommendations for containers with active assignments
        enabled_count = self.enable_feed_recommendations()
        self.stdout.write(self.style.SUCCESS(f'Enabled feed recommendations for {enabled_count} containers'))
        
        # API URL information based on API URL Testing rule
        self.stdout.write('\n' + self.style.SUCCESS('=== API URL Information ==='))
        self.stdout.write('Following the URL pattern from the API URL Testing rule:')
        self.stdout.write('  /api/v1/{app_name}/{endpoint}/')
        
        self.stdout.write(f'\nKey endpoints for feed recommendations:')
        self.stdout.write(f'  - /api/v1/inventory/feed-recommendations/')
        self.stdout.write(f'  - /api/v1/infrastructure/containers/')
        
    def enable_feed_recommendations(self):
        """Enable feed recommendations for containers with active assignments"""
        # Find containers with active batch assignments
        active_assignments = BatchContainerAssignment.objects.filter(active=True)
        active_container_ids = active_assignments.values_list('container_id', flat=True).distinct()
        
        count = 0
        for container_id in active_container_ids:
            try:
                container = Container.objects.get(id=container_id)
                if not container.feed_recommendations_enabled:
                    container.feed_recommendations_enabled = True
                    container.save()
                    self.stdout.write(f'  - Enabled recommendations for: {container.name}')
                    count += 1
            except Container.DoesNotExist:
                continue
                
        # If no active assignments, enable some containers anyway
        if count == 0:
            tanks = Container.objects.filter(type__in=['tank', 'raceway', 'cage'])[:5]
            for container in tanks:
                container.feed_recommendations_enabled = True
                container.save()
                self.stdout.write(f'  - Enabled recommendations for: {container.name}')
                count += 1
                
        return count
