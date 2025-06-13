# Code Organization Guidelines

## Overview

This document outlines the code organization principles and best practices for the AquaMind project. Following these guidelines ensures a consistent, maintainable, and scalable codebase that adheres to our established coding standards.

## General Principles

### Code Structure

- **Python Version**: All code must be compatible with Python 3.11
- **Django Version**: The project uses Django 4.2.11
- **PEP 8**: Follow PEP 8 style guide for Python code
- **PEP 257**: Document all functions and classes with docstrings following PEP 257
- **Linting**: Use flake8 for linting Python code

### File and Module Organization

```
AquaMind/
├── apps/                   # Application modules
│   ├── core/               # Core functionality and utilities
│   ├── users/              # User authentication and permissions
│   ├── infrastructure/     # Physical assets management
│   ├── batch/              # Fish batch lifecycle management
│   ├── environmental/      # Environmental monitoring
│   ├── operational/        # Daily operations and planning
│   ├── inventory/          # Resource and feed management
│   └── health/             # Health tracking and records
├── aquamind/               # Project settings
├── docs/                   # Documentation
├── scripts/                # Utility scripts
└── tests/                  # Test suite
```

## Code Organization Rules

### File Size Limits

- **Maximum File Size**: Keep files under 200-300 lines of code
- **When to Split**: Consider refactoring when a file approaches 300 lines
- **How to Split**: Extract logical components into separate modules or classes

### Function Size Limits

- **Maximum Function Size**: Keep functions under 50 lines of code
- **When to Split**: Consider refactoring when a function exceeds 30 lines
- **How to Split**: Extract reusable logic into helper functions

### Class Organization

- **Single Responsibility**: Each class should have a single responsibility
- **Maximum Methods**: Aim for no more than 10-15 methods per class
- **Method Order**:
  1. Class methods (`@classmethod`)
  2. Static methods (`@staticmethod`)
  3. Properties (`@property`)
  4. Initialization methods (`__init__`, etc.)
  5. Public methods
  6. Protected methods (prefixed with `_`)
  7. Private methods (prefixed with `__`)

### Django-Specific Organization

#### Models

- Organize model fields in a logical order:
  1. Primary key fields
  2. Foreign key fields
  3. Required fields
  4. Optional fields
  5. Calculated fields
  6. Metadata fields (created_at, updated_at)
- Place `Meta` class immediately after field definitions
- Group related methods together
- Define `__str__` method for all models
- Example:

```python
class Batch(models.Model):
    # Primary key
    id = models.AutoField(primary_key=True)
    
    # Foreign keys
    species = models.ForeignKey('Species', on_delete=models.PROTECT)
    lifecycle_stage = models.ForeignKey('LifeCycleStage', on_delete=models.PROTECT)
    
    # Required fields
    batch_number = models.CharField(max_length=50, unique=True)
    start_date = models.DateField()
    population_count = models.IntegerField()
    
    # Optional fields
    notes = models.TextField(blank=True, null=True)
    
    # Calculated fields
    biomass_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Metadata fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Batch"
        verbose_name_plural = "Batches"
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.batch_number} ({self.species.name})"
    
    # Lifecycle methods
    def advance_lifecycle_stage(self):
        # Method implementation
        pass
    
    # Calculation methods
    def calculate_biomass(self):
        # Method implementation
        pass
```

#### Views and ViewSets

- Organize ViewSet methods in the standard order:
  1. `get_queryset`
  2. `get_serializer_class`
  3. `get_permissions`
  4. Standard actions (`list`, `retrieve`, `create`, `update`, `destroy`)
  5. Custom actions (decorated with `@action`)
- Extract complex filtering logic into separate methods
- Example:

```python
class BatchViewSet(viewsets.ModelViewSet):
    serializer_class = BatchSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Batch.objects.all()
        queryset = self._filter_by_geography(queryset)
        return queryset
    
    def _filter_by_geography(self, queryset):
        # Filtering implementation
        return queryset
    
    @action(detail=True, methods=['post'])
    def transfer(self, request, pk=None):
        # Custom action implementation
        pass
```

#### Serializers

- Organize serializer fields in the same order as model fields
- Group validation methods together
- Example:

```python
class BatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Batch
        fields = ['id', 'batch_number', 'species', 'lifecycle_stage', 'population_count', 'biomass_kg']
    
    def validate_population_count(self, value):
        # Validation implementation
        return value
    
    def validate(self, data):
        # Cross-field validation
        return data
```

#### URLs

- Group related URLs together
- Use consistent naming patterns
- Example:

```python
urlpatterns = [
    # Batch endpoints
    path('batches/', BatchListCreateView.as_view(), name='batch-list'),
    path('batches/<int:pk>/', BatchDetailView.as_view(), name='batch-detail'),
    
    # Container endpoints
    path('containers/', ContainerListCreateView.as_view(), name='container-list'),
    path('containers/<int:pk>/', ContainerDetailView.as_view(), name='container-detail'),
]
```

## Refactoring Guidelines

### When to Refactor

- When a file exceeds 200-300 lines of code
- When a function exceeds 50 lines of code
- When a class has more than 15 methods
- When there is duplicated code across multiple files
- When a function or method has too many parameters (more than 5)
- When a function or method has too many levels of nesting (more than 3)

### How to Refactor

#### Splitting Large Files

1. **Identify Logical Components**: Look for groups of related functions or classes
2. **Create New Modules**: Move related components to new files
3. **Update Imports**: Adjust import statements in all affected files
4. **Example**:

Before:
```
infrastructure/models.py (500 lines with Geography, Area, Container, Sensor models)
```

After:
```
infrastructure/models/
  __init__.py (imports and exports all models)
  geography.py (Geography model)
  area.py (Area model)
  container.py (Container model)
  sensor.py (Sensor model)
```

#### Splitting Large Functions

1. **Identify Logical Steps**: Break the function into discrete steps
2. **Extract Helper Functions**: Create helper functions for each step
3. **Example**:

Before:
```python
def process_batch_transfer(batch, new_container, transfer_date):
    # 50+ lines of code handling validation, old container updates,
    # new container assignment, and event logging
```

After:
```python
def process_batch_transfer(batch, new_container, transfer_date):
    validate_transfer(batch, new_container)
    deactivate_old_assignment(batch)
    create_new_assignment(batch, new_container, transfer_date)
    log_transfer_event(batch, new_container, transfer_date)
    
def validate_transfer(batch, new_container):
    # Validation logic
    
def deactivate_old_assignment(batch):
    # Deactivation logic
    
def create_new_assignment(batch, new_container, transfer_date):
    # Assignment creation logic
    
def log_transfer_event(batch, new_container, transfer_date):
    # Event logging logic
```

#### Extracting Reusable Components

1. **Identify Common Patterns**: Look for code that appears in multiple places
2. **Create Utility Functions/Classes**: Move common code to the core app
3. **Example**:

Before (repeated in multiple views):
```python
# In multiple view files
def get_filtered_queryset(self):
    queryset = self.model.objects.all()
    user_geography = self.request.user.profile.geography
    if user_geography:
        queryset = queryset.filter(geography=user_geography)
    return queryset
```

After:
```python
# In core/mixins.py
class GeographyFilterMixin:
    def get_queryset(self):
        queryset = super().get_queryset()
        user_geography = self.request.user.profile.geography
        if user_geography:
            queryset = queryset.filter(geography=user_geography)
        return queryset

# In views
class BatchViewSet(GeographyFilterMixin, viewsets.ModelViewSet):
    # View implementation
```

## Best Practices

### Code Reuse

- **Look for Existing Solutions**: Before writing new code, check if similar functionality already exists
- **Avoid Duplication**: Extract common code into shared utilities
- **Use Inheritance and Mixins**: Leverage Django's class-based views and mixins

### Code Simplicity

- **Prefer Simple Solutions**: Choose the simplest approach that meets requirements
- **Early Returns**: Use early returns to reduce nesting and improve readability
- **Avoid Premature Optimization**: Focus on clear, correct code first

### Environment Awareness

- **Environment-Specific Code**: Write code that works across dev, test, and prod environments
- **Configuration**: Use settings and environment variables for environment-specific values
- **Feature Flags**: Use feature flags for functionality that varies by environment

### Testing Considerations

- **Testable Code**: Organize code to facilitate unit testing
- **Dependency Injection**: Design classes and functions to accept dependencies
- **Mock Boundaries**: Structure code so external dependencies can be easily mocked in tests

## Examples

### Good Code Organization Example

```python
# batch/services.py
from decimal import Decimal
from django.db import transaction
from apps.batch.models import Batch, BatchContainerAssignment
from apps.core.exceptions import InvalidTransferError

class BatchTransferService:
    """Service for handling batch transfers between containers."""
    
    @classmethod
    def transfer_batch(cls, batch, new_container, transfer_date, user=None):
        """
        Transfer a batch to a new container.
        
        Args:
            batch: The batch to transfer
            new_container: The destination container
            transfer_date: The date of transfer
            user: Optional user performing the transfer
            
        Returns:
            BatchContainerAssignment: The new assignment
            
        Raises:
            InvalidTransferError: If the transfer is not valid
        """
        cls._validate_transfer(batch, new_container)
        
        with transaction.atomic():
            old_assignment = cls._deactivate_current_assignment(batch)
            new_assignment = cls._create_new_assignment(
                batch, new_container, transfer_date, old_assignment
            )
            cls._log_transfer(batch, old_assignment, new_assignment, user)
            
        return new_assignment
    
    @staticmethod
    def _validate_transfer(batch, new_container):
        """Validate that the transfer is allowed."""
        if not new_container.is_active:
            raise InvalidTransferError("Cannot transfer to inactive container")
        
        if batch.lifecycle_stage not in new_container.compatible_stages.all():
            raise InvalidTransferError(
                f"Container not compatible with {batch.lifecycle_stage.name} stage"
            )
    
    @staticmethod
    def _deactivate_current_assignment(batch):
        """Deactivate the current batch assignment."""
        current_assignment = BatchContainerAssignment.objects.filter(
            batch=batch, is_active=True
        ).first()
        
        if current_assignment:
            current_assignment.is_active = False
            current_assignment.save()
            
        return current_assignment
    
    @staticmethod
    def _create_new_assignment(batch, container, date, old_assignment=None):
        """Create a new batch container assignment."""
        # Copy values from old assignment if available
        population = batch.population_count
        biomass = batch.biomass_kg
        
        return BatchContainerAssignment.objects.create(
            batch=batch,
            container=container,
            assignment_date=date,
            population_count=population,
            biomass_kg=biomass,
            is_active=True,
            lifecycle_stage=batch.lifecycle_stage
        )
    
    @staticmethod
    def _log_transfer(batch, old_assignment, new_assignment, user):
        """Log the transfer event."""
        from apps.core.models import AuditLog
        
        old_container = old_assignment.container if old_assignment else None
        new_container = new_assignment.container
        
        AuditLog.objects.create(
            content_object=batch,
            action="TRANSFER",
            user=user,
            details={
                "from_container": old_container.id if old_container else None,
                "to_container": new_container.id,
                "population": new_assignment.population_count,
                "biomass_kg": float(new_assignment.biomass_kg)
            }
        )
```

### Bad Code Organization (Anti-Pattern)

```python
# DON'T DO THIS: Everything in one large function
def transfer_batch(batch_id, container_id, date, user_id=None):
    # 100+ lines of code with validation, database operations,
    # logging, notifications, all mixed together with complex
    # conditional logic and no clear structure
    
    # Validation
    batch = Batch.objects.get(id=batch_id)
    container = Container.objects.get(id=container_id)
    
    if not container.is_active:
        raise Exception("Container inactive")
    
    # Database operations mixed with business logic
    old_assignment = BatchContainerAssignment.objects.filter(
        batch=batch, is_active=True
    ).first()
    
    if old_assignment:
        old_assignment.is_active = False
        old_assignment.save()
    
    # More database operations
    new_assignment = BatchContainerAssignment.objects.create(
        batch=batch,
        container=container,
        assignment_date=date,
        population_count=batch.population_count,
        biomass_kg=batch.biomass_kg,
        is_active=True
    )
    
    # Logging mixed in
    if user_id:
        user = User.objects.get(id=user_id)
        AuditLog.objects.create(
            content_object=batch,
            action="TRANSFER",
            user=user,
            details={"some": "details"}
        )
    
    # Notification logic mixed in
    emails = []
    for manager in container.area.managers.all():
        emails.append(manager.email)
    
    if emails:
        send_mail(
            "Batch Transfer",
            f"Batch {batch.batch_number} transferred to {container.name}",
            "noreply@example.com",
            emails
        )
    
    return new_assignment
```

## Conclusion

Following these code organization guidelines will help maintain a clean, maintainable, and scalable codebase. When in doubt, prioritize readability and simplicity over cleverness. Remember that code is read much more often than it is written, so optimize for readability and maintainability.
