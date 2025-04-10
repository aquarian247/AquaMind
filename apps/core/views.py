from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from django.views import View
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

@method_decorator(ensure_csrf_cookie, name='dispatch')
class CSRFTokenView(View):
    """
    View to provide a CSRF token to the frontend.
    This endpoint sets a CSRF cookie that can be used for subsequent requests.
    """
    def get(self, request, *args, **kwargs):
        return JsonResponse({"detail": "CSRF cookie set"})


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Simple health check endpoint to verify the API is running.
    This endpoint doesn't require authentication and is used by the frontend
    to check backend availability during initialization.
    """
    return Response({
        "status": "healthy",
        "api_version": "v1",
        "environment": "development"
    })
