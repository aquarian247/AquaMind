from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import UserProfile, Geography, Subsidiary, Role


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for the UserProfile model.
    
    Handles serialization of UserProfile instances for GET requests,
    including all profile information and RBAC fields. All fields are
    read-only to ensure profile updates use the appropriate update serializers.
    """
    
    class Meta:
        model = UserProfile
        fields = [
            'full_name', 'phone', 'profile_picture', 'job_title',
            'department', 'geography', 'subsidiary', 'role',
            'language_preference', 'date_format_preference',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'full_name', 'phone', 'profile_picture', 'job_title',
            'department', 'geography', 'subsidiary', 'role',
            'language_preference', 'date_format_preference',
            'created_at', 'updated_at'
        ]


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for the User model.
    
    Handles user registration, updates, and provides profile data
    nested within the user data.
    """
    
    profile = UserProfileSerializer(read_only=True)
    password = serializers.CharField(write_only=True, required=False)
    full_name = serializers.CharField(
        source='profile.full_name', required=False)
    phone = serializers.CharField(source='profile.phone', required=False)
    geography = serializers.ChoiceField(
        source='profile.geography',
        choices=Geography.choices,
        required=False
    )
    subsidiary = serializers.ChoiceField(
        source='profile.subsidiary',
        choices=Subsidiary.choices,
        required=False
    )
    role = serializers.ChoiceField(
        source='profile.role',
        choices=Role.choices,
        required=False
    )

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'full_name', 'phone',
            'geography', 'subsidiary', 'role', 'password',
            'is_active', 'profile', 'date_joined'
        ]
        read_only_fields = ['id', 'date_joined']
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'required': True}
        }
    
    def validate_password(self, value):
        """
        Validate password using Django's password validators.
        
        Args:
            value: The password to validate
            
        Returns:
            str: The validated password
            
        Raises:
            serializers.ValidationError: If password doesn't meet validation criteria
        """
        validate_password(value)
        return value
    
    def create(self, validated_data):
        """
        Create and return a new user with encrypted password.
        
        Args:
            validated_data: Validated form/JSON data
            
        Returns:
            User: The newly created User instance
        """
        profile_payload = validated_data.pop('profile', {}) or {}
        profile_data = {
            field: profile_payload[field]
            for field in ['full_name', 'phone', 'geography', 'subsidiary', 'role']
            if field in profile_payload
        }
        for field in ['full_name', 'phone', 'geography', 'subsidiary', 'role']:
            dotted_key = f'profile.{field}'
            if dotted_key in validated_data:
                profile_data[field] = validated_data.pop(dotted_key)
        
        password = validated_data.pop('password', None)
        email = validated_data.get('email')
        
        # Django User model requires a username, so use email if not provided
        if 'username' not in validated_data and email:
            validated_data['username'] = email
            
        user = User.objects.create(**validated_data)
        
        if password:
            user.set_password(password)
            user.save()
        
        # Update profile fields if provided
        if profile_data and hasattr(user, 'profile'):
            for field, value in profile_data.items():
                setattr(user.profile, field, value)
            user.profile.save()
            
        return user
    
    def update(self, instance, validated_data):
        """
        Update and return an existing user instance.

        Server-side enforcement: RBAC fields (role, geography, subsidiary)
        are ignored unless the requester is staff/superuser to prevent
        privilege escalation.
        
        Args:
            instance: The User instance to update
            validated_data: Validated form/JSON data
            
        Returns:
            User: The updated User instance
        """
        # Get the request user from context
        request = self.context.get('request')
        is_admin = request and (request.user.is_staff or request.user.is_superuser)
        
        profile_payload = validated_data.pop('profile', {}) or {}
        profile_data = {
            field: profile_payload[field]
            for field in ['full_name', 'phone', 'geography', 'subsidiary', 'role']
            if field in profile_payload
        }
        for field in ['full_name', 'phone', 'geography', 'subsidiary', 'role']:
            dotted_key = f'profile.{field}'
            if dotted_key in validated_data:
                profile_data[field] = validated_data.pop(dotted_key)
        
        # Server-side enforcement: Remove RBAC fields if not admin
        rbac_fields = ['geography', 'subsidiary', 'role']
        if not is_admin:
            for field in rbac_fields:
                profile_data.pop(field, None)
        
        # Handle password update if provided
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)
        
        # Update user fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        
        # Update profile fields if provided
        if profile_data and hasattr(instance, 'profile'):
            for field, value in profile_data.items():
                setattr(instance.profile, field, value)
            instance.profile.save()
        
        return instance


class UserCreateSerializer(UserSerializer):
    """
    Serializer for user registration that requires password.
    
    Extends UserSerializer but makes password field required.
    """
    
    password = serializers.CharField(write_only=True, required=True)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom token serializer that adds user data to token response.
    
    Extends the JWT TokenObtainPairSerializer to include additional user
    information in the token response.
    """
    
    def validate(self, attrs):
        """
        Validate credentials and add extra data to token payload.
        
        Args:
            attrs: Credentials data
            
        Returns:
            dict: Token data including access, refresh tokens and user data
        """
        data = super().validate(attrs)
        user = self.user
        
        # Add user data to response
        data.update({
            'id': user.id,
            'username': user.username,
            'email': user.email,
        })
        
        # Add profile data if available
        if hasattr(user, 'profile'):
            profile = user.profile
            data.update({
                'full_name': profile.full_name,
                'role': profile.role,
                'geography': profile.geography,
                'subsidiary': profile.subsidiary,
            })
        
        return data


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating UserProfile information.
    
    Provides a dedicated serializer for profile updates separate from user data.
    Allows users to update their own profile information excluding RBAC fields
    (role, geography, subsidiary) which require admin privileges.
    """
    
    class Meta:
        model = UserProfile
        fields = ['full_name', 'phone', 'profile_picture', 'job_title', 'department',
                 'language_preference', 'date_format_preference']
        read_only_fields = ['created_at', 'updated_at']


class UserProfileAdminUpdateSerializer(serializers.ModelSerializer):
    """
    Admin-only serializer for updating UserProfile information including RBAC fields.
    
    This serializer includes role, geography, and subsidiary fields that should only
    be modifiable by administrators to prevent privilege escalation.
    """
    
    class Meta:
        model = UserProfile
        fields = ['full_name', 'phone', 'profile_picture', 'job_title', 'department',
                 'geography', 'subsidiary', 'role', 'language_preference', 'date_format_preference']
        read_only_fields = ['created_at', 'updated_at']


class PasswordChangeSerializer(serializers.Serializer):
    """
    Serializer for password change endpoint.
    
    Validates old password and ensures new password meets requirements.
    """
    
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    
    def validate_old_password(self, value):
        """
        Validate that the old password is correct.
        
        Args:
            value: The old password to validate
            
        Returns:
            str: The validated old password
            
        Raises:
            serializers.ValidationError: If old password is incorrect
        """
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Old password is incorrect')
        return value
    
    def validate_new_password(self, value):
        """
        Validate new password using Django's password validators.
        
        Args:
            value: The new password to validate
            
        Returns:
            str: The validated new password
            
        Raises:
            serializers.ValidationError: If password doesn't meet validation criteria
        """
        validate_password(value)
        return value