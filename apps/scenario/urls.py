"""
URL configuration for the Scenario Planning app.

Includes both traditional Django views and API endpoints.
"""
from django.urls import path, include
from .api.routers import router

app_name = 'scenario'

urlpatterns = [
    # API endpoints
    path('api/', include(router.urls)),
    
    # Traditional views can be added here later if needed
    # path('dashboard/', views.dashboard, name='dashboard'),
]
