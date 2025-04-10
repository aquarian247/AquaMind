"""
Setup Feed Recommendations Test Data

This command sets up all required test data for properly testing the feed recommendations feature.
It ensures containers, batches, assignments, and feed types are all properly configured.

Run with: python manage.py setup_feed_recommendations
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from django.utils import timezone
from django.db import transaction
import random
from datetime import timedelta

from apps.infrastructure.models import Container, ContainerType, Hall
from apps.batch.models import Batch, BatchContainerAssignment, LifeCycleStage
from apps.inventory.models import Feed


class Command(BaseCommand):
    help = 'Setup test data for feed recommendations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username', 
            default='testuser',
            help='Username for test user'
        )
        parser.add_argument(
            '--password', 
            default='password123',
            help='Password for test user'
        )
        parser.add_argument(
            '--force', 
            action='store_true',
            help='Force recreation of data even if it exists'
        )

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== Setting up Feed Recommendations Test Data ==='))
        
        # Setup user and authentication first
        username = options['username']
        password = options['password']
        force = options['force']
        
        # Create test user and token
        user = self._create_test_user(username, password)
        token = self._create_auth_token(user)
        
        # Setup test data
        container_count = self._setup_containers(force)
        feed_count = self._setup_feeds(force)
        stages = self._setup_lifecycle_stages(force)
        batch_count = self._setup_batches(force)
        assignment_count = self._setup_assignments(force)
        
        # Summary and test instructions
        self.stdout.write('\n' + self.style.SUCCESS('=== Setup Summary ==='))
        self.stdout.write(f'Test user: {username}')
        self.stdout.write(f'Auth token: {token.key[:10]}...')
        self.stdout.write(f'Containers enabled for recommendations: {container_count}')
        self.stdout.write(f'Feed types available: {feed_count}')
        self.stdout.write(f'Active batches: {batch_count}')
        self.stdout.write(f'Active assignments: {assignment_count}')
        
        self.stdout.write('\n' + self.style.SUCCESS('=== Testing Instructions ==='))
        self.stdout.write('1. Set the authentication token in your browser:')
        self.stdout.write(f'   localStorage.setItem("token", "{token.key}")')
        self.stdout.write('2. Go to the Feed Recommendations page in the UI')
        self.stdout.write('3. Click "Generate Recommendations"')
        self.stdout.write('4. Select a container or batch from the dropdown')
        self.stdout.write('5. Complete the form and generate recommendations')
    
    def _create_test_user(self, username, password):
        """Create a test user for API access"""
        self.stdout.write('Creating test user...')
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'is_staff': True,
                'is_active': True
            }
        )
        
        # Always update password to ensure it's correct
        user.set_password(password)
        user.save()
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'  Created new user: {username}'))
        else:
            self.stdout.write(f'  Updated existing user: {username}')
        
        return user
    
    def _create_auth_token(self, user):
        """Create or get authentication token"""
        self.stdout.write('Setting up authentication token...')
        token, created = Token.objects.get_or_create(user=user)
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'  Created new token for {user.username}'))
        else:
            self.stdout.write(f'  Using existing token for {user.username}')
        
        return token
    
    def _setup_containers(self, force=False):
        """Ensure we have containers with feed recommendations enabled"""
        self.stdout.write('Setting up containers...')
        
        # Get active containers
        containers = Container.objects.filter(active=True)
        
        # If no containers or force is true, create test containers
        if not containers.exists() or force:
            self.stdout.write('  Creating test containers...')
            
            # Create container types if needed
            container_types = ContainerType.objects.all()
            if not container_types.exists():
                type_names = ["Tank", "Raceway", "Cage"]
                for name in type_names:
                    ContainerType.objects.create(
                        name=name,
                        category="production",
                        max_volume_m3=random.uniform(50, 2000)
                    )
                    self.stdout.write(f'  Created container type: {name}')
                container_types = ContainerType.objects.all()
            
            # Get or create a hall
            hall = Hall.objects.first()
            if not hall:
                hall = Hall.objects.create(
                    name="Test Hall",
                    area_sqm=500,
                    active=True
                )
                self.stdout.write(f'  Created hall: {hall.name}')
            
            # Create test containers
            for i in range(1, 6):
                container_type = random.choice(list(container_types))
                container = Container.objects.create(
                    name=f"Test Container {i}",
                    container_type=container_type,
                    volume_m3=random.uniform(10, 500),
                    max_biomass_kg=random.uniform(100, 5000),
                    hall=hall,
                    active=True,
                    feed_recommendations_enabled=True
                )
                self.stdout.write(f'  Created container: {container.name}')
            
            containers = Container.objects.filter(active=True)
        
        # Ensure feed recommendations are enabled
        enabled_count = 0
        for container in containers:
            if not container.feed_recommendations_enabled:
                container.feed_recommendations_enabled = True
                container.save()
                enabled_count += 1
                self.stdout.write(f'  Enabled feed recommendations for: {container.name}')
        
        return containers.filter(feed_recommendations_enabled=True).count()
    
    def _setup_feeds(self, force=False):
        """Ensure we have feed types available"""
        self.stdout.write('Setting up feed types...')
        
        feeds = Feed.objects.all()
        
        if not feeds.exists() or force:
            feed_data = [
                {"name": "Premium Starter", "protein_content": 55, "lipid_content": 18, "carb_content": 12, "size_mm": 0.5},
                {"name": "Growth Formula", "protein_content": 48, "lipid_content": 22, "carb_content": 15, "size_mm": 2.0},
                {"name": "Standard Diet", "protein_content": 42, "lipid_content": 25, "carb_content": 18, "size_mm": 3.0},
                {"name": "Finishing Feed", "protein_content": 38, "lipid_content": 30, "carb_content": 20, "size_mm": 4.5}
            ]
            
            for data in feed_data:
                feed = Feed.objects.create(
                    name=data["name"],
                    protein_content=data["protein_content"],
                    lipid_content=data["lipid_content"],
                    carb_content=data["carb_content"],
                    size_mm=data["size_mm"],
                    stock_kg=1000,
                    price_per_kg=random.uniform(1.5, 4.5)
                )
                self.stdout.write(f'  Created feed: {feed.name}')
        
        return Feed.objects.count()
    
    def _setup_lifecycle_stages(self, force=False):
        """Ensure we have lifecycle stages defined"""
        self.stdout.write('Setting up lifecycle stages...')
        
        stages = LifeCycleStage.objects.all()
        
        if not stages.exists() or force:
            stage_names = ["Egg & Alevin", "Fry", "Parr", "Smolt", "Post-Smolt", "Adult"]
            for name in stage_names:
                stage = LifeCycleStage.objects.create(name=name)
                self.stdout.write(f'  Created lifecycle stage: {name}')
        
        return list(LifeCycleStage.objects.all())
    
    def _setup_batches(self, force=False):
        """Ensure we have active batches available"""
        self.stdout.write('Setting up batches...')
        
        batches = Batch.objects.filter(active=True)
        
        if not batches.exists() or force:
            try:
                # Check required fields for Batch model
                batch_fields = [f.name for f in Batch._meta.fields]
                self.stdout.write(f'  Batch model fields: {batch_fields}')
                
                for i in range(1, 4):
                    # Create with minimal required fields
                    batch_data = {
                        'name': f"Test Batch {i}",
                        'active': True,
                    }
                    
                    # Add optional fields if they exist in the model
                    if 'species' in batch_fields:
                        batch_data['species'] = "Atlantic Salmon"
                    if 'initial_count' in batch_fields:
                        batch_data['initial_count'] = random.randint(1000, 5000)
                    if 'current_count' in batch_fields:
                        batch_data['current_count'] = random.randint(900, 4800)
                    if 'origin_date' in batch_fields:
                        batch_data['origin_date'] = timezone.now() - timedelta(days=random.randint(30, 180))
                        
                    batch = Batch.objects.create(**batch_data)
                    self.stdout.write(f'  Created batch: {batch.name}')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  Error creating batches: {str(e)}'))
        else:
            for batch in batches[:5]:  # List up to 5 existing batches
                self.stdout.write(f'  Found existing batch: {batch.name}')
        
        return Batch.objects.filter(active=True).count()
    
    def _setup_assignments(self, force=False):
        """Create batch-container assignments if needed"""
        self.stdout.write('Setting up batch-container assignments...')
        
        # Check if we have active assignments
        assignments = BatchContainerAssignment.objects.filter(active=True)
        
        if not assignments.exists() or force:
            try:
                # Get available containers, batches, and lifecycle stages
                containers = Container.objects.filter(feed_recommendations_enabled=True, active=True)
                batches = Batch.objects.filter(active=True)
                stages = LifeCycleStage.objects.all()
                
                # Log what we found
                self.stdout.write(f'  Found {containers.count()} enabled containers')
                self.stdout.write(f'  Found {batches.count()} active batches')
                self.stdout.write(f'  Found {stages.count()} lifecycle stages')
                
                if not containers.exists():
                    self.stdout.write(self.style.ERROR('  No enabled containers available'))
                    return 0
                    
                if not batches.exists():
                    self.stdout.write(self.style.ERROR('  No active batches available'))
                    return 0
                    
                if not stages.exists():
                    self.stdout.write(self.style.ERROR('  No lifecycle stages defined'))
                    return 0
                
                # Check required fields for BatchContainerAssignment model
                assignment_fields = [f.name for f in BatchContainerAssignment._meta.fields]
                self.stdout.write(f'  Assignment model fields: {assignment_fields}')
                
                # Create assignments
                for batch in batches[:3]:  # Limit to 3 batches for testing
                    # Get a container that doesn't already have an active assignment
                    assigned_container_ids = BatchContainerAssignment.objects.filter(
                        active=True
                    ).values_list('container_id', flat=True)
                    
                    available_containers = containers.exclude(id__in=assigned_container_ids)
                    
                    if not available_containers.exists():
                        self.stdout.write(self.style.WARNING(f'  No available containers for batch {batch.name}'))
                        continue
                    
                    container = available_containers.first()
                    stage = random.choice(list(stages))
                    
                    # Create with minimal required fields
                    assignment_data = {
                        'batch': batch,
                        'container': container,
                        'active': True,
                    }
                    
                    # Add lifecycle_stage - this is required based on the memory
                    assignment_data['lifecycle_stage'] = stage
                    
                    # Add optional fields if they exist in the model
                    if 'assignment_date' in assignment_fields:
                        assignment_data['assignment_date'] = timezone.now() - timedelta(days=random.randint(1, 30))
                    if 'population_count' in assignment_fields:
                        # Use batch.current_count if it exists, otherwise random value
                        if hasattr(batch, 'current_count') and batch.current_count:
                            assignment_data['population_count'] = batch.current_count
                        else:
                            assignment_data['population_count'] = random.randint(500, 5000)
                    if 'biomass_kg' in assignment_fields:
                        assignment_data['biomass_kg'] = random.uniform(50, 500)
                    
                    assignment = BatchContainerAssignment.objects.create(**assignment_data)
                    
                    self.stdout.write(
                        f'  Created assignment: {batch.name} → {container.name} ({stage.name})'
                    )
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  Error creating assignments: {str(e)}'))
        else:
            for assignment in assignments[:5]:  # List up to 5 existing assignments
                self.stdout.write(
                    f'  Found existing assignment: {assignment.batch.name} → '
                    f'{assignment.container.name} '
                    f'({assignment.lifecycle_stage.name if hasattr(assignment, "lifecycle_stage") else "Unknown stage"})'
                )
        
        return BatchContainerAssignment.objects.filter(active=True).count()
