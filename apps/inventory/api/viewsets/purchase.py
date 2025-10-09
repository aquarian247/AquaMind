"""
Feed purchase viewset for the inventory app.
"""
from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend

from aquamind.utils.history_mixins import HistoryReasonMixin

from apps.inventory.models import FeedPurchase
from apps.inventory.api.serializers.purchase import FeedPurchaseSerializer


class FeedPurchaseViewSet(HistoryReasonMixin, viewsets.ModelViewSet):
    """
    ViewSet for FeedPurchase model.

    Provides CRUD operations for feed purchase records. Uses HistoryReasonMixin
    to capture audit change reasons.
    """
    queryset = FeedPurchase.objects.all()
    serializer_class = FeedPurchaseSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]
    filterset_fields = ['feed', 'supplier', 'purchase_date']
    search_fields = ['supplier', 'batch_number', 'notes']
    ordering_fields = ['purchase_date', 'quantity_kg', 'cost_per_kg']
    ordering = ['-purchase_date']
