from rest_framework.authtoken.models import Token
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from django.conf import settings
from django.contrib.auth.models import User
from drf_spectacular.utils import extend_schema

# Local serializers for request / response documentation
from .serializers import AuthTokenSerializer, AuthTokenResponseSerializer

# --------------------------------------------------------------------------- #
# Authentication Views                                                       #
# --------------------------------------------------------------------------- #

@extend_schema(
    request=AuthTokenSerializer,
    responses={200: AuthTokenResponseSerializer},
    tags=["auth"],
)
class CustomObtainAuthToken(GenericAPIView):
    """
    Custom view for obtaining auth tokens that also returns user info
    """
    permission_classes = [AllowAny]
    serializer_class = AuthTokenSerializer
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]
        
        if not username or not password:
            return Response({'error': 'Please provide both username and password'}, 
                            status=status.HTTP_400_BAD_REQUEST)
                            
        user = authenticate(username=username, password=password)
        
        if not user:
            return Response({'error': 'Invalid credentials'}, 
                           status=status.HTTP_401_UNAUTHORIZED)
        
        token, created = Token.objects.get_or_create(user=user)
        
        # Return token and basic user info
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'username': user.username,
            'email': user.email
        })


@extend_schema(
    responses={200: AuthTokenResponseSerializer},
    description="Development-only endpoint that returns an auth token without "
                "credentials. **Disabled in production.**",
    tags=["auth"],
)
@api_view(['GET'])
@permission_classes([AllowAny])
def dev_auth(request):
    """
    Development-only endpoint to get a valid auth token automatically.
    This endpoint is disabled in production environments.
    
    Returns:
        Response: A response containing a valid token and user information
    """
    if not settings.DEBUG:
        return Response(
            {"error": "This endpoint is only available in development environments"}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get or create a development user
    username = 'devuser'
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            'is_staff': True,
            'is_active': True,
            'email': 'dev@example.com'
        }
    )
    
    if created:
        user.set_password('devpassword')
        user.save()
    
    # Get or create token
    token, _ = Token.objects.get_or_create(user=user)
    
    return Response({
        'token': token.key,
        'user_id': user.pk,
        'username': user.username,
        'email': user.email
    })
