# Audit Trail HistoryReasonMixin

## Overview

The `HistoryReasonMixin` is a reusable Django REST Framework mixin that automatically captures human-readable change reasons for all Create/Update/Delete (CUD) operations performed through API endpoints. It integrates seamlessly with `django-simple-history` to provide comprehensive audit trails.

## Purpose

This mixin addresses the audit trail requirement by:

1. **Capturing Change Reasons**: Automatically generates standardized change reason messages for API-driven CUD operations
2. **User Attribution**: Ensures `history_user` is properly set via the existing `HistoryRequestMiddleware`
3. **Consistency**: Provides uniform change reason patterns across all API endpoints
4. **Audit Compliance**: Supports the comprehensive audit trail requirements for AquaMind

## Usage

### Basic Implementation

```python
from aquamind.utils.history_mixins import HistoryReasonMixin
from rest_framework import viewsets

class YourModelViewSet(HistoryReasonMixin, viewsets.ModelViewSet):
    """
    Your ViewSet with automatic change reason capture.
    """
    # Your existing ViewSet code...
```

### Complete Example

```python
from aquamind.utils.history_mixins import HistoryReasonMixin
from rest_framework import viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated

class ContainerViewSet(HistoryReasonMixin, viewsets.ModelViewSet):
    """
    API endpoint for managing Containers.

    This ViewSet automatically captures change reasons for all CUD operations:
    - POST (create): "created via API by {username}"
    - PUT/PATCH (update): "updated via API by {username}"
    - DELETE (delete): "deleted via API by {username}"
    """
    authentication_classes = [TokenAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = Container.objects.all()
    serializer_class = ContainerSerializer
    # ... rest of your ViewSet configuration
```

## How It Works

### Change Reason Format

The mixin generates standardized change reasons using the pattern:
```
"{action} via API by {username}"
```

Where:
- `{action}` is one of: "created", "updated", "deleted"
- `{username}` is the authenticated user's username

### Integration with django-simple-history

1. **User Attribution**: Leverages `HistoryRequestMiddleware` to automatically set `history_user`
2. **Change Reasons**: Uses `simple_history.utils.update_change_reason()` to capture the reason
3. **Historical Records**: Creates `Historical{ModelName}` records with:
   - `history_type`: "+" (create), "~" (update), "-" (delete)
   - `history_user`: The authenticated user who performed the action
   - `history_date`: Timestamp of the operation
   - `history_change_reason`: Human-readable reason for the change

## Testing

### Test Pattern

```python
from simple_history.models import HistoricalYourModel
from rest_framework.test import APITestCase

class YourModelHistoryTest(APITestCase):
    def test_create_captures_change_reason(self):
        """Test that creating an instance captures the change reason."""
        # Create instance via API
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, 201)

        # Verify historical record
        instance = YourModel.objects.get(id=response.data['id'])
        historical_records = HistoricalYourModel.objects.filter(id=instance.id)

        # Should have historical record with correct attributes
        self.assertEqual(historical_records.count(), 1)
        record = historical_records.first()
        self.assertEqual(record.history_type, '+')
        self.assertEqual(record.history_user, self.user)
        self.assertIn('created via API by', record.history_change_reason)
```

### Comprehensive Test Coverage

Test all three operations (Create, Update, Delete) to ensure complete audit trail coverage:

```python
def test_update_captures_change_reason(self):
    # Test update operations capture change reasons

def test_delete_captures_change_reason(self):
    # Test delete operations capture change reasons
```

## Implementation Checklist

When adding `HistoryReasonMixin` to a new ViewSet:

- [ ] Import the mixin: `from aquamind.utils.history_mixins import HistoryReasonMixin`
- [ ] Inherit from the mixin: `class YourViewSet(HistoryReasonMixin, viewsets.ModelViewSet):`
- [ ] Ensure the model has `history = HistoricalRecords()` in its Meta class
- [ ] Add tests for CUD operations to verify change reason capture
- [ ] Document the audit trail capability in the ViewSet docstring

## Requirements

### Dependencies
- `django-simple-history>=3.8.0`
- `djangorestframework>=3.14.0`

### Configuration
Ensure the following are properly configured in `settings.py`:

```python
INSTALLED_APPS = [
    # ... other apps
    'simple_history',
]

MIDDLEWARE = [
    # ... other middleware
    "simple_history.middleware.HistoryRequestMiddleware",
]
```

### Model Setup
The associated model must have historical records enabled:

```python
from simple_history import HistoricalRecords

class YourModel(models.Model):
    # ... your fields

    class Meta:
        # ... your meta options

    # Enable historical tracking
    history = HistoricalRecords()
```

## Best Practices

### 1. Consistent Adoption
Apply `HistoryReasonMixin` to all ViewSets that handle business-critical models to ensure complete audit trail coverage.

### 2. Custom Change Reasons
For special cases requiring custom change reasons, override the mixin's methods:

```python
class CustomViewSet(HistoryReasonMixin, viewsets.ModelViewSet):
    def _reason(self, action):
        """Override to provide custom change reasons."""
        if action == "created":
            return f"Custom creation reason for {self.request.user}"
        return super()._reason(action)
```

### 3. Performance Considerations
The mixin has minimal performance impact as it only executes during CUD operations, not reads.

### 4. Security
Change reasons are automatically attributed to the authenticated user, ensuring proper accountability.

## Troubleshooting

### Common Issues

1. **No Historical Records Created**
   - Ensure the model has `history = HistoricalRecords()` in its Meta class
   - Verify `HistoryRequestMiddleware` is properly configured in settings

2. **Missing Change Reasons**
   - Confirm the ViewSet inherits from `HistoryReasonMixin`
   - Check that the user is properly authenticated
   - Verify the request goes through the DRF ViewSet methods (not bypassing them)

3. **Incorrect User Attribution**
   - Ensure `HistoryRequestMiddleware` is positioned correctly in MIDDLEWARE
   - Check that authentication is working properly

### Debug Tips

1. Check historical records in Django admin
2. Verify middleware order in settings
3. Test with authenticated vs. anonymous requests
4. Review test authentication setup

## Related Documentation

- [django-simple-history Documentation](https://django-simple-history.readthedocs.io/)
- [AquaMind Audit Trail Implementation Plan](../docs/progress/AUDIT_TRAIL_IMPLEMENTATION_PLAN.md)
- [AquaMind Audit Trail Assessment](../docs/progress/AUDIT_TRAIL_ASSESSMENT.md)

---

**Last Updated**: Phase 0 Foundations - September 10, 2025
