# Generated by Django 4.2.11 on 2025-03-14 09:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="full_name",
            field=models.CharField(
                blank=True, max_length=150, verbose_name="full name"
            ),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="geography",
            field=models.CharField(
                choices=[
                    ("FO", "Faroe Islands"),
                    ("SC", "Scotland"),
                    ("ALL", "All Geographies"),
                ],
                default="ALL",
                help_text="Geographic region access level",
                max_length=3,
            ),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="phone",
            field=models.CharField(
                blank=True, max_length=20, null=True, verbose_name="phone number"
            ),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="role",
            field=models.CharField(
                choices=[
                    ("ADMIN", "Administrator"),
                    ("MGR", "Manager"),
                    ("OPR", "Operator"),
                    ("VET", "Veterinarian"),
                    ("QA", "Quality Assurance"),
                    ("FIN", "Finance"),
                    ("VIEW", "Viewer"),
                ],
                default="VIEW",
                help_text="User role and permission level",
                max_length=5,
            ),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="subsidiary",
            field=models.CharField(
                choices=[
                    ("BS", "Broodstock"),
                    ("FW", "Freshwater"),
                    ("FM", "Farming"),
                    ("LG", "Logistics"),
                    ("ALL", "All Subsidiaries"),
                ],
                default="ALL",
                help_text="Subsidiary access level",
                max_length=3,
            ),
        ),
        migrations.DeleteModel(
            name="User",
        ),
    ]
