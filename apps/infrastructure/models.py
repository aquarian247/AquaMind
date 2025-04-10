from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Geography(models.Model):
    """
    Define regions of operation (e.g., Faroe Islands, Scotland).
    Used for region-based access control and operations.
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Geographies"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Area(models.Model):
    """
    Sea areas with geo-positioning for farming operations.
    """
    name = models.CharField(max_length=100)
    geography = models.ForeignKey(Geography, on_delete=models.PROTECT, related_name='areas')
    latitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
        help_text="Latitude (automatically set when location is selected on map)"
    )
    longitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
        help_text="Longitude (automatically set when location is selected on map)"
    )
    max_biomass = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        help_text="Maximum biomass capacity in kg"
    )
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.geography.name})"


class FreshwaterStation(models.Model):
    """
    Freshwater stations with geo-positioning for early lifecycle stages.
    """
    STATION_TYPES = [
        ('FRESHWATER', 'Freshwater'),
        ('BROODSTOCK', 'Broodstock'),
    ]
    
    name = models.CharField(max_length=100)
    station_type = models.CharField(max_length=20, choices=STATION_TYPES)
    geography = models.ForeignKey(Geography, on_delete=models.PROTECT, related_name='stations')
    latitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
        help_text="Latitude (automatically set when location is selected on map)"
    )
    longitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
        help_text="Longitude (automatically set when location is selected on map)"
    )
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_station_type_display()})"


class Hall(models.Model):
    """
    Halls within stations that contain containers.
    """
    name = models.CharField(max_length=100)
    freshwater_station = models.ForeignKey(
        FreshwaterStation, 
        on_delete=models.CASCADE, 
        related_name='halls'
    )
    description = models.TextField(blank=True)
    area_sqm = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} (in {self.freshwater_station.name})"


class ContainerType(models.Model):
    """
    Types of containers used in aquaculture operations.
    Examples: tanks, pens, trays for eggs, etc.
    """
    CONTAINER_CATEGORIES = [
        ('TANK', 'Tank'),
        ('PEN', 'Pen'),
        ('TRAY', 'Tray'),
        ('OTHER', 'Other'),
    ]
    
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CONTAINER_CATEGORIES)
    max_volume_m3 = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"


class Container(models.Model):
    """
    Containers that hold fish, such as tanks, pens, or trays.
    Can be in a hall (within a station) or in a sea area.
    """
    name = models.CharField(max_length=100)
    container_type = models.ForeignKey(ContainerType, on_delete=models.PROTECT, related_name='containers')
    
    # A container can be in either a hall or a sea area, but not both
    hall = models.ForeignKey(Hall, on_delete=models.CASCADE, related_name='containers', null=True, blank=True)
    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name='containers', null=True, blank=True)
    
    volume_m3 = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(0.01)], 
        help_text="Container volume in cubic meters"
    )
    feed_recommendations_enabled = models.BooleanField(
        default=False,
        help_text="Whether feed recommendations should be generated for this container"
    )
    max_biomass_kg = models.DecimalField(max_digits=10, decimal_places=2, help_text="Maximum biomass in kg")
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(hall__isnull=False, area__isnull=True) | 
                    models.Q(hall__isnull=True, area__isnull=False)
                ),
                name="container_in_either_hall_or_area"
            )
        ]
    
    def clean(self):
        """Validate the container model:
        1. Ensure container is either in a hall or area (not both)
        2. Ensure container volume doesn't exceed container type's maximum volume
        
        Raises:
            ValidationError: If any validation constraints are violated
        """
        from django.core.exceptions import ValidationError
        
        # Validate location constraints
        if self.hall and self.area:
            raise ValidationError("Container cannot be in both a hall and a sea area")
        if not self.hall and not self.area:
            raise ValidationError("Container must be in either a hall or a sea area")
            
        # Validate that volume doesn't exceed container type's maximum volume
        if self.container_type and self.volume_m3:
            if self.volume_m3 > self.container_type.max_volume_m3:
                raise ValidationError({
                    'volume_m3': f'Container volume ({self.volume_m3} m³) cannot exceed the maximum volume '
                               f'for this container type ({self.container_type.max_volume_m3} m³)'
                })
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        location = self.hall.name if self.hall else self.area.name
        return f"{self.name} ({self.container_type.name} in {location})"


class Sensor(models.Model):
    """
    Sensors installed in containers for monitoring environmental conditions.
    """
    SENSOR_TYPES = [
        ('TEMPERATURE', 'Temperature'),
        ('OXYGEN', 'Oxygen'),
        ('PH', 'pH'),
        ('SALINITY', 'Salinity'),
        ('CO2', 'CO2'),
        ('OTHER', 'Other'),
    ]
    
    name = models.CharField(max_length=100)
    sensor_type = models.CharField(max_length=20, choices=SENSOR_TYPES)
    container = models.ForeignKey(Container, on_delete=models.CASCADE, related_name='sensors')
    serial_number = models.CharField(max_length=100, blank=True)
    manufacturer = models.CharField(max_length=100, blank=True)
    installation_date = models.DateField(null=True, blank=True)
    last_calibration_date = models.DateField(null=True, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_sensor_type_display()} in {self.container.name})"


class FeedContainer(models.Model):
    """
    Feed storage units linked to areas or halls.
    Examples: feed silos, feed barges, etc.
    """
    CONTAINER_TYPES = [
        ('SILO', 'Silo'),
        ('BARGE', 'Barge'),
        ('TANK', 'Tank'),
        ('OTHER', 'Other'),
    ]
    
    name = models.CharField(max_length=100)
    container_type = models.CharField(max_length=20, choices=CONTAINER_TYPES)
    
    # A feed container can be linked to either a hall or an area, but not both
    hall = models.ForeignKey(Hall, on_delete=models.CASCADE, related_name='feed_containers', null=True, blank=True)
    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name='feed_containers', null=True, blank=True)
    
    capacity_kg = models.DecimalField(max_digits=10, decimal_places=2, help_text="Capacity in kg")
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(hall__isnull=False, area__isnull=True) | 
                    models.Q(hall__isnull=True, area__isnull=False)
                ),
                name="feed_container_in_either_hall_or_area"
            )
        ]
    
    def clean(self):
        """Validate the feed container model.

        Ensures that the feed container is linked to either a hall or a sea area,
        but not both.

        Raises:
            ValidationError: If the container is linked to both or neither location.
        """
        from django.core.exceptions import ValidationError
        
        if self.hall and self.area:
            raise ValidationError("Feed container cannot be linked to both a hall and a sea area")
        if not self.hall and not self.area:
            raise ValidationError("Feed container must be linked to either a hall or a sea area")
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        location = self.hall.name if self.hall else self.area.name
        return f"{self.name} ({self.get_container_type_display()} at {location})"
