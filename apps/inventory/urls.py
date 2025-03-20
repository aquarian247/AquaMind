from django.urls import path, include

app_name = 'inventory'

urlpatterns = [
    # Include the API URLs
    path('api/v1/inventory/', include('apps.inventory.api.routers')),
]