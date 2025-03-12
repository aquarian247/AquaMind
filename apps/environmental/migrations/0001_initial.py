# Generated by Django 4.2.11 on 2025-03-12 13:57

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("batch", "0001_initial"),
        ("infrastructure", "0003_alter_area_max_biomass"),
    ]

    operations = [
        migrations.CreateModel(
            name="EnvironmentalParameter",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100)),
                ("unit", models.CharField(max_length=20)),
                ("description", models.TextField(blank=True)),
                (
                    "min_value",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Minimum acceptable value for this parameter",
                        max_digits=10,
                        null=True,
                    ),
                ),
                (
                    "max_value",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Maximum acceptable value for this parameter",
                        max_digits=10,
                        null=True,
                    ),
                ),
                (
                    "optimal_min",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Minimum optimal value for this parameter",
                        max_digits=10,
                        null=True,
                    ),
                ),
                (
                    "optimal_max",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Maximum optimal value for this parameter",
                        max_digits=10,
                        null=True,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="StageTransitionEnvironmental",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "temperature",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Water temperature in °C",
                        max_digits=5,
                        null=True,
                    ),
                ),
                (
                    "oxygen",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Dissolved oxygen in mg/L",
                        max_digits=5,
                        null=True,
                    ),
                ),
                (
                    "salinity",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Salinity in ppt",
                        max_digits=5,
                        null=True,
                    ),
                ),
                (
                    "ph",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="pH level",
                        max_digits=4,
                        null=True,
                    ),
                ),
                (
                    "additional_parameters",
                    models.JSONField(
                        blank=True,
                        help_text="Additional environmental parameters",
                        null=True,
                    ),
                ),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "batch_transfer",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="environmental_conditions",
                        to="batch.batchtransfer",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="WeatherData",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("timestamp", models.DateTimeField()),
                (
                    "temperature",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Air temperature in °C",
                        max_digits=5,
                        null=True,
                    ),
                ),
                (
                    "wind_speed",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Wind speed in m/s",
                        max_digits=6,
                        null=True,
                    ),
                ),
                (
                    "wind_direction",
                    models.IntegerField(
                        blank=True,
                        help_text="Wind direction in degrees (0-360)",
                        null=True,
                        validators=[
                            django.core.validators.MinValueValidator(0),
                            django.core.validators.MaxValueValidator(360),
                        ],
                    ),
                ),
                (
                    "precipitation",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Precipitation in mm",
                        max_digits=6,
                        null=True,
                    ),
                ),
                (
                    "wave_height",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Wave height in meters",
                        max_digits=5,
                        null=True,
                    ),
                ),
                (
                    "wave_period",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Wave period in seconds",
                        max_digits=5,
                        null=True,
                    ),
                ),
                (
                    "wave_direction",
                    models.IntegerField(
                        blank=True,
                        help_text="Wave direction in degrees (0-360)",
                        null=True,
                        validators=[
                            django.core.validators.MinValueValidator(0),
                            django.core.validators.MaxValueValidator(360),
                        ],
                    ),
                ),
                (
                    "cloud_cover",
                    models.IntegerField(
                        blank=True,
                        help_text="Cloud cover percentage (0-100)",
                        null=True,
                        validators=[
                            django.core.validators.MinValueValidator(0),
                            django.core.validators.MaxValueValidator(100),
                        ],
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "area",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="weather_data",
                        to="infrastructure.area",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["area", "timestamp"],
                        name="environment_area_id_7e45b9_idx",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="PhotoperiodData",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("date", models.DateField()),
                (
                    "day_length_hours",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Day length in hours (0-24)",
                        max_digits=5,
                        validators=[
                            django.core.validators.MinValueValidator(0),
                            django.core.validators.MaxValueValidator(24),
                        ],
                    ),
                ),
                (
                    "light_intensity",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Light intensity in lux",
                        max_digits=10,
                        null=True,
                    ),
                ),
                (
                    "is_interpolated",
                    models.BooleanField(
                        default=False,
                        help_text="Whether this data point was interpolated rather than measured",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "area",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="photoperiod_data",
                        to="infrastructure.area",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["area", "date"], name="environment_area_id_9c8f82_idx"
                    )
                ],
                "unique_together": {("area", "date")},
            },
        ),
        migrations.CreateModel(
            name="EnvironmentalReading",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("value", models.DecimalField(decimal_places=4, max_digits=10)),
                ("reading_time", models.DateTimeField()),
                (
                    "is_manual",
                    models.BooleanField(
                        default=False,
                        help_text="Whether this reading was entered manually",
                    ),
                ),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "batch",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="environmental_readings",
                        to="batch.batch",
                    ),
                ),
                (
                    "container",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="environmental_readings",
                        to="infrastructure.container",
                    ),
                ),
                (
                    "parameter",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="environmental.environmentalparameter",
                    ),
                ),
                (
                    "recorded_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "sensor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="readings",
                        to="infrastructure.sensor",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["container", "parameter", "reading_time"],
                        name="environment_contain_a6622f_idx",
                    ),
                    models.Index(
                        fields=["batch", "parameter", "reading_time"],
                        name="environment_batch_i_e1fe9c_idx",
                    ),
                ],
            },
        ),
    ]
