from django.urls import path
from . import views

app_name = 'health'

urlpatterns = [
    path('ajax/load-batch-assignments/', views.load_batch_assignments, name='ajax_load_batch_assignments'),
    # Add other health app-specific URLs here as needed
]
