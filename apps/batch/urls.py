"""URL configuration for the batch app.

This module includes the router configuration with URL patterns for the batch app.
"""
from django.urls import path, include

from apps.batch.api.routers import router

app_name = 'batch'

urlpatterns = [
    path('', include(router.urls)),
]