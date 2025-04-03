from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from django.views import View

@method_decorator(ensure_csrf_cookie, name='dispatch')
class CSRFTokenView(View):
    """
    View to provide a CSRF token to the frontend.
    This endpoint sets a CSRF cookie that can be used for subsequent requests.
    """
    def get(self, request, *args, **kwargs):
        return JsonResponse({"detail": "CSRF cookie set"})
