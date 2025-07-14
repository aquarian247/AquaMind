from rest_framework import serializers


class AuthTokenSerializer(serializers.Serializer):
    """
    Serializer for username and password authentication.
    Used by CustomObtainAuthToken and dev_auth views.
    """
    username = serializers.CharField(
        label="Username",
        write_only=False,
        required=True,
        help_text="Username for authentication"
    )
    password = serializers.CharField(
        label="Password",
        style={'input_type': 'password'},
        trim_whitespace=False,
        write_only=True,
        required=True,
        help_text="Password for authentication"
    )


class AuthTokenResponseSerializer(serializers.Serializer):
    """
    Serializer for token response data.
    Defines the structure of the response from authentication endpoints.
    """
    token = serializers.CharField(
        help_text="Authentication token for API access"
    )
    user_id = serializers.IntegerField(
        help_text="User ID associated with the token"
    )
    username = serializers.CharField(
        help_text="Username of the authenticated user"
    )
    email = serializers.CharField(
        help_text="Email of the authenticated user"
    )
