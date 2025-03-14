from django.contrib.auth.models import User
from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from django.shortcuts import get_object_or_404
from .serializers import (
    UserSerializer, 
    UserCreateSerializer,
    UserProfileSerializer,
    CustomTokenObtainPairSerializer,
    UserProfileUpdateSerializer,
    PasswordChangeSerializer
)
from .models import UserProfile, Geography, Subsidiary, Role


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom JWT token view that returns user information with tokens.
    
    Extends the standard JWT token endpoint to include user information
    in the response.
    """
    serializer_class = CustomTokenObtainPairSerializer


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed, created, edited or deleted.
    
    Provides CRUD operations for users with appropriate permission checks.
    """
    queryset = User.objects.all().order_by('username')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        """
        Return appropriate serializer based on the action.
        
        Returns UserCreateSerializer for create action, otherwise default to
        UserSerializer.
        """
        if self.action == 'create':
            return UserCreateSerializer
        return self.serializer_class
    
    def get_permissions(self):
        """
        Set permissions based on action.
        
        - Allow anyone to register if ALLOW_PUBLIC_REGISTRATION setting is True
        - Require authentication for all other endpoints
        - Require admin privileges for list, destroy actions
        """
        if self.action == 'create':
            return [permissions.IsAdminUser()]
        elif self.action in ['retrieve', 'update', 'partial_update']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]
    
    def get_queryset(self):
        """
        Filter queryset based on user's role.
        
        - Admins can see all users
        - Regular users can only see themselves
        
        Returns:
            QuerySet: Filtered User objects
        """
        user = self.request.user
        
        # Allow admin users to see all users
        if user.is_superuser or (hasattr(user, 'profile') and user.profile.role == Role.ADMIN):
            return User.objects.all().order_by('username')
        
        # Regular users can only see themselves
        return User.objects.filter(id=user.id)
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        """
        Endpoint to retrieve the currently authenticated user.
        
        Returns:
            Response: Serialized data of the current user
        """
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['put'], permission_classes=[permissions.IsAuthenticated])
    def change_password(self, request):
        """
        Endpoint to change user's password.
        
        Validates old password and updates with new password.
        
        Returns:
            Response: Success or error message
        """
        user = request.user
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({'detail': 'Password updated successfully'}, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    API endpoint to view and update the user's profile.
    
    Allows users to view and update their own profile information.
    """
    serializer_class = UserProfileUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        """
        Retrieve the UserProfile for the authenticated user.
        
        Returns:
            UserProfile: The profile of the current user
        """
        return UserProfile.objects.get(user=self.request.user)
    
    def get_serializer_class(self):
        """
        Return appropriate serializer based on the request method.
        
        Returns UserProfileSerializer for GET, UserProfileUpdateSerializer for PUT/PATCH.
        """
        if self.request.method == 'GET':
            return UserProfileSerializer
        return UserProfileUpdateSerializer