"""
Operational app URL configuration.

Includes API endpoints for operational planning and analysis.
"""
from django.urls import path, include
from apps.operational.api import routers

app_name = 'operational'

urlpatterns = [
    # API endpoints
    path('', include((routers.router.urls, 'operational'), namespace='api')),
]
