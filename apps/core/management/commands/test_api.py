from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from apps.infrastructure.models import Container
from apps.inventory.models import FeedRecommendation
from django.utils import timezone
import json

class Command(BaseCommand):
    help = 'Test API authentication and endpoints'

    def add_arguments(self, parser):
        parser.add_argument('--create-user', action='store_true', help='Create a test user if it does not exist')
        parser.add_argument('--username', type=str, default='testuser', help='Username for test user')
        parser.add_argument('--password', type=str, default='password123', help='Password for test user')
        parser.add_argument('--enable-recommendations', action='store_true', help='Enable feed recommendations for sample containers')

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== AquaMind API Test Tool ==='))
        
        username = options['username']
        password = options['password']
        
        # Create test user if requested and doesn't exist
        if options['create_user']:
            user, created = User.objects.get_or_create(username=username)
            if created:
                user.set_password(password)
                user.is_staff = True
                user.save()
                self.stdout.write(self.style.SUCCESS(f'Created test user: {username}'))
            else:
                self.stdout.write(self.style.WARNING(f'User {username} already exists'))
        
        # Get or create auth token
        try:
            user = User.objects.get(username=username)
            token, created = Token.objects.get_or_create(user=user)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created new token for {username}'))
            
            self.stdout.write(self.style.SUCCESS(f'API Token: {token.key}'))
            self.stdout.write(self.style.SUCCESS(f'For frontend testing, run in browser console:'))
            self.stdout.write(self.style.SUCCESS(f'localStorage.setItem("token", "{token.key}")'))
            
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User {username} does not exist. Use --create-user to create it.'))
            return
        
        # Display API URL information based on API URL Testing rule
        self.stdout.write('\n' + self.style.SUCCESS('=== API URL Information ==='))
        self.stdout.write('Following the API URL Testing rule pattern:')
        self.stdout.write('Base URL: /api/v1/{app_name}/{endpoint}/')
        self.stdout.write('Examples:')
        self.stdout.write('  - /api/v1/inventory/feed-recommendations/')
        self.stdout.write('  - /api/v1/infrastructure/containers/')
        
        # Enable feed recommendations for test containers if requested
        if options['enable_recommendations']:
            self.enable_feed_recommendations()
        
        # Display DB stats
        self.display_stats()
    
    def enable_feed_recommendations(self):
        """Enable feed recommendations for a sample of containers"""
        self.stdout.write('\n' + self.style.SUCCESS('=== Enabling Feed Recommendations ==='))
        
        # Get tanks/raceways
        containers = Container.objects.filter(type__in=['tank', 'raceway', 'cage'])[:5]
        
        if not containers:
            self.stdout.write(self.style.WARNING('No suitable containers found'))
            return
            
        for container in containers:
            container.feed_recommendations_enabled = True
            container.save()
            self.stdout.write(self.style.SUCCESS(f'Enabled feed recommendations for: {container.name}'))
    
    def display_stats(self):
        """Display database statistics relevant to feed recommendations"""
        self.stdout.write('\n' + self.style.SUCCESS('=== Database Statistics ==='))
        
        # Count containers with feed recommendations enabled
        total_containers = Container.objects.count()
        enabled_containers = Container.objects.filter(feed_recommendations_enabled=True).count()
        
        self.stdout.write(f'Total containers: {total_containers}')
        self.stdout.write(f'Containers with feed recommendations enabled: {enabled_containers}')
        
        # Check for existing feed recommendations
        recs = FeedRecommendation.objects.all()
        rec_count = recs.count()
        
        self.stdout.write(f'Total feed recommendations: {rec_count}')
        
        if rec_count > 0:
            recent_rec = recs.order_by('-recommended_date').first()
            self.stdout.write(f'Most recent recommendation date: {recent_rec.recommended_date}')
            
            # Display sample recommendation details
            self.stdout.write('\nSample recommendation:')
            self.stdout.write(f'  Container: {recent_rec.batch_container_assignment.container.name}')
            self.stdout.write(f'  Feed: {recent_rec.feed.name}')
            self.stdout.write(f'  Amount: {recent_rec.recommended_feed_kg} kg')
            self.stdout.write(f'  Is followed: {recent_rec.is_followed}')
