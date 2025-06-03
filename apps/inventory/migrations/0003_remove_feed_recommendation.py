from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('inventory', '0002_feedrecommendation'),
    ]
    
    operations = [
        # Use SeparateDatabaseAndState to handle the model removal
        migrations.SeparateDatabaseAndState(
            # Database operations - use RunSQL for direct table operations
            database_operations=[
                migrations.RunSQL(
                    # SQL that works in both PostgreSQL and SQLite
                    sql='DROP TABLE IF EXISTS inventory_feedrecommendation;',
                    reverse_sql='', # No reverse operation needed
                ),
            ],
            # State operations - tell Django the model is gone
            state_operations=[
                migrations.DeleteModel(name='FeedRecommendation'),
            ],
        ),
    ]
