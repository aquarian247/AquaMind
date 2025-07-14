from django.db import migrations
from django.conf import settings
import os


def create_ci_test_user(apps, schema_editor):
    """
    Create a test user for CI environments that can be used for API testing.
    This ensures the user exists in the same database that the dev server uses.
    """
    # Only create the user when running in CI environment
    if 'settings_ci' not in os.environ.get('DJANGO_SETTINGS_MODULE', ''):
        return
        
    # Get the user model - we need to use the historical version from apps
    User = apps.get_model('auth', 'User')
    
    # Check if the user already exists
    if User.objects.filter(username='schemathesis_ci').exists():
        return
        
    # Create the CI test user
    user = User.objects.create(
        username='schemathesis_ci',
        email='ci@example.com',
        is_active=True,
    )
    
    # Set password - note: set_password is not available in migrations
    # We need to use the make_password function
    from django.contrib.auth.hashers import make_password
    user.password = make_password('testpass123')
    user.save()
    
    # Create auth token for the user
    Token = apps.get_model('authtoken', 'Token')
    Token.objects.create(user=user)
    
    print("✅ Created CI test user 'schemathesis_ci' with auth token")


def remove_ci_test_user(apps, schema_editor):
    """Remove the CI test user if it exists."""
    # Only remove when in CI environment
    if 'settings_ci' not in os.environ.get('DJANGO_SETTINGS_MODULE', ''):
        return
        
    User = apps.get_model('auth', 'User')
    User.objects.filter(username='schemathesis_ci').delete()


class Migration(migrations.Migration):
    """
    Create a CI test user with auth token for API testing.
    This ensures the user exists in the in-memory database used by the dev server.
    """
    
    dependencies = [
        ('users', '0002_userprofile_full_name_userprofile_geography_and_more'),
        ('authtoken', '0001_initial'),  # Ensure authtoken is installed
    ]

    operations = [
        migrations.RunPython(create_ci_test_user, remove_ci_test_user),
    ]
