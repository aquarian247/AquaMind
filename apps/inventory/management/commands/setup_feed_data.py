from django.core.management.base import BaseCommand
from apps.infrastructure.models import Container
from apps.batch.models import Batch, BatchContainerAssignment
from apps.inventory.models import Feed
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token


class Command(BaseCommand):
    """
    Command to set up data for testing the feed recommendations feature.
    This ensures we have properly configured containers and relationships.
    """
    help = 'Sets up test data for feed recommendations feature'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== Setting up Feed Recommendations Data ==='))

        # 1. Check authentication
        self._setup_auth()
        
        # 2. Check containers and enable feed recommendations
        container_count = self._setup_containers()
        
        # 3. Check feeds
        feed_count = self._check_feeds()
        
        # 4. Check active assignments
        assignment_count = self._check_assignments()
        
        # Summary
        self.stdout.write('\n=== Setup Summary ===')
        self.stdout.write(f'Containers with feed recommendations enabled: {container_count}')
        self.stdout.write(f'Available feeds: {feed_count}')
        self.stdout.write(f'Active batch-container assignments: {assignment_count}')
        
        # Test instructions
        self.stdout.write('\n=== Testing Instructions ===')
        self.stdout.write('1. Log in with username: testuser, password: password123')
        self.stdout.write('2. Go to Inventory Management → Feed Recommendations tab')
        self.stdout.write('3. Click "Generate Recommendations"')
        self.stdout.write('4. Select a container or batch from the dropdown (if available)')
        self.stdout.write('5. Complete the form and click "Generate"')

    def _setup_auth(self):
        """Create test user with authentication token"""
        self.stdout.write('Checking authentication...')
        
        user, created = User.objects.get_or_create(
            username='testuser',
            defaults={'is_staff': True}
        )
        
        if created:
            user.set_password('password123')
            user.save()
            self.stdout.write(self.style.SUCCESS('  Created test user: testuser'))
        
        token, _ = Token.objects.get_or_create(user=user)
        self.stdout.write(self.style.SUCCESS(f'  Authentication token: {token.key}'))
        self.stdout.write('  For frontend testing, run in browser console:')
        self.stdout.write(f'  localStorage.setItem("token", "{token.key}")')

    def _setup_containers(self):
        """Enable feed recommendations on active containers"""
        self.stdout.write('Setting up containers...')
        
        # Find containers that have active assignments
        assignments = BatchContainerAssignment.objects.filter(active=True)
        enabled_count = 0
        
        if assignments.exists():
            container_ids = assignments.values_list('container_id', flat=True).distinct()
            containers = Container.objects.filter(id__in=container_ids)
            
            for container in containers:
                container.feed_recommendations_enabled = True
                container.save()
                enabled_count += 1
                self.stdout.write(f'  Enabled feed recommendations for: {container.name}')
        
        # If no containers had assignments, enable for any active containers
        if enabled_count == 0:
            containers = Container.objects.filter(active=True)[:5]
            for container in containers:
                container.feed_recommendations_enabled = True
                container.save()
                enabled_count += 1
                self.stdout.write(f'  Enabled feed recommendations for: {container.name}')
        
        return enabled_count

    def _check_feeds(self):
        """Check available feeds in the system"""
        self.stdout.write('Checking available feeds...')
        
        feeds = Feed.objects.all()
        if feeds.exists():
            for feed in feeds:
                self.stdout.write(f'  Available feed: {feed.name}')
            return feeds.count()
        else:
            self.stdout.write(self.style.WARNING('  No feeds found in the system'))
            return 0

    def _check_assignments(self):
        """Check active batch-container assignments"""
        self.stdout.write('Checking active batch-container assignments...')
        
        assignments = BatchContainerAssignment.objects.filter(active=True)
        if assignments.exists():
            for assignment in assignments:
                self.stdout.write(
                    f'  Active assignment: Batch {assignment.batch.name} → '
                    f'Container {assignment.container.name}'
                )
            return assignments.count()
        else:
            self.stdout.write(
                self.style.WARNING('  No active batch-container assignments found')
            )
            return 0
