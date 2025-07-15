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
    
    # ------------------------------------------------------------------
    # Get or create the CI user **and** its token.
    # - If the user already exists (migrations applied earlier) we still
    #   need to fetch / create the token so that it can be printed below.
    # - If the user is newly-created we must set a deterministic password
    #   because `User.set_password` isn’t available in migrations.
    # ------------------------------------------------------------------
    from django.contrib.auth.hashers import make_password

    user, created = User.objects.get_or_create(
        username='schemathesis_ci',
        defaults={
            'email': 'ci@example.com',
            'is_active': True,
            'password': make_password('testpass123'),
        },
    )

    # Ensure password is consistent even if the user already existed
    if not created:
        user.password = make_password('testpass123')
        user.is_active = True  # make sure it wasn't disabled
        user.save(update_fields=['password', 'is_active'])

    # Create (or fetch) auth token for the user
    Token = apps.get_model('authtoken', 'Token')
    token, created = Token.objects.get_or_create(user=user)
    
    # Ensure token has a valid key – handle both freshly-created and
    # pre-existing (but empty) token rows
    if not token.key:
        # This shouldn't happen with DRF's Token model, but let's be safe
        token.delete()
        token = Token.objects.create(user=user)
    
    # ------------------------------------------------------------------
    # Expose the token so the CI helper script can read it from stdout.
    # Use a simple, grep-friendly prefix that is unlikely to appear
    # elsewhere in the migration output.
    # ------------------------------------------------------------------
    print(f"CI_AUTH_TOKEN:{token.key}")


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
