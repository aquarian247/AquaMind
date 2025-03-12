#!/bin/bash
# Script to create the app directory structure for AquaMind

# Create the apps directory
mkdir -p /workspaces/AquaMind/apps
touch /workspaces/AquaMind/apps/__init__.py

# Create all app directories
for app in infrastructure batch broodstock growth environmental inventory medical scenario operational users
do
    mkdir -p /workspaces/AquaMind/apps/$app
    # Create basic Django app files
    touch /workspaces/AquaMind/apps/$app/__init__.py
    touch /workspaces/AquaMind/apps/$app/models.py
    touch /workspaces/AquaMind/apps/$app/views.py
    touch /workspaces/AquaMind/apps/$app/urls.py
    touch /workspaces/AquaMind/apps/$app/admin.py
    touch /workspaces/AquaMind/apps/$app/apps.py
    touch /workspaces/AquaMind/apps/$app/serializers.py
    # Create tests directory
    mkdir -p /workspaces/AquaMind/apps/$app/tests
    touch /workspaces/AquaMind/apps/$app/tests/__init__.py
    touch /workspaces/AquaMind/apps/$app/tests/test_models.py
done

echo "App structure created successfully!"
