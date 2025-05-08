from django.urls import path, include
from .routers import router

app_name = 'health_api'

urlpatterns = [
    path('', include(router.urls)),
]
