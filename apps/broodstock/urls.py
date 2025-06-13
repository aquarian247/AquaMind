"""
URL configuration for the Broodstock Management app.
"""

from django.urls import path, include
from apps.broodstock.api.routers import router

app_name = 'broodstock'

urlpatterns = [
    path('api/', include(router.urls)),
]
