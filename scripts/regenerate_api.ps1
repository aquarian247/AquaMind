# scripts/regenerate_api.ps1
#
# Regenerates the OpenAPI specification from Django models/serializers
# and optionally triggers frontend TypeScript client generation.
#
# Usage:
#   .\scripts\regenerate_api.ps1 [-Frontend] [-Validate] [-Watch]
#
# Parameters:
#   -Frontend    Also regenerate the frontend TypeScript client
#   -Validate    Validate the generated OpenAPI spec
#   -Watch       Watch for changes and regenerate (requires PowerShell 5.1+)
#
# This script is designed to be used by Factory workspace file watchers
# to automatically regenerate API specs when Django models/serializers change.

param (
    [switch]$Frontend = $false,
    [switch]$Validate = $false,
    [switch]$Watch = $false
)

# Configuration
$BackendDir = "."
$FrontendDir = "..\AquaMind-Frontend"
$OpenApiOutput = "api\openapi.yaml"
$FrontendScript = "npm run generate:api"

# Function to check if a command exists
function Test-CommandExists {
    param ($Command)
    
    $exists = $null -ne (Get-Command $Command -ErrorAction SilentlyContinue)
    return $exists
}

# Function to regenerate the OpenAPI spec
function Regenerate-Spec {
    Write-Host "`nRegenerating OpenAPI specification..." -ForegroundColor White -BackgroundColor Black
    
    # Check if we're in the right directory
    if (-not (Test-Path "manage.py")) {
        Write-Host "Error: manage.py not found. Please run this script from the Django project root." -ForegroundColor Red
        exit 1
    }
    
    # Generate the OpenAPI spec
    python manage.py spectacular --file "$OpenApiOutput"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ OpenAPI spec generated successfully at $OpenApiOutput" -ForegroundColor Green
    } else {
        Write-Host "✗ Failed to generate OpenAPI spec" -ForegroundColor Red
        exit 1
    }
    
    # Validate if requested
    if ($Validate) {
        Write-Host "`nValidating OpenAPI specification..." -ForegroundColor White -BackgroundColor Black
        python manage.py spectacular --file "$OpenApiOutput" --validate
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ OpenAPI spec validation passed" -ForegroundColor Green
        } else {
            Write-Host "✗ OpenAPI spec validation failed" -ForegroundColor Red
            exit 1
        }
    }
}

# Function to regenerate the frontend TypeScript client
function Regenerate-Frontend {
    if ($Frontend) {
        Write-Host "`nRegenerating frontend TypeScript client..." -ForegroundColor White -BackgroundColor Black
        
        # Check if frontend directory exists
        if (-not (Test-Path $FrontendDir)) {
            Write-Host "⚠ Frontend directory not found at $FrontendDir" -ForegroundColor Yellow
            Write-Host "⚠ Skipping frontend client generation" -ForegroundColor Yellow
            return
        }
        
        # Copy OpenAPI spec to frontend if needed
        $FrontendOpenApiDir = Join-Path $FrontendDir "api"
        if (-not (Test-Path $FrontendOpenApiDir)) {
            New-Item -Path $FrontendOpenApiDir -ItemType Directory | Out-Null
        }
        
        Copy-Item "$OpenApiOutput" -Destination "$FrontendOpenApiDir\"
        
        # Change to frontend directory and run generation script
        $CurrentLocation = Get-Location
        Set-Location $FrontendDir
        
        if (Test-Path "package.json") {
            Write-Host "Running: $FrontendScript" -ForegroundColor Yellow
            Invoke-Expression $FrontendScript
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✓ Frontend TypeScript client generated successfully" -ForegroundColor Green
            } else {
                Write-Host "✗ Failed to generate frontend TypeScript client" -ForegroundColor Red
                Set-Location $CurrentLocation
                exit 1
            }
        } else {
            Write-Host "✗ package.json not found in frontend directory" -ForegroundColor Red
            Set-Location $CurrentLocation
            exit 1
        }
        
        Set-Location $CurrentLocation
    }
}

# Main execution
if ($Watch) {
    Write-Host "Watching for changes in apps/ directory..." -ForegroundColor White -BackgroundColor Black
    Write-Host "Press Ctrl+C to stop watching`n" -ForegroundColor Yellow
    
    $Watcher = New-Object System.IO.FileSystemWatcher
    $Watcher.Path = "apps"
    $Watcher.IncludeSubdirectories = $true
    $Watcher.EnableRaisingEvents = $true
    $Watcher.Filter = "*.py"
    
    # Define action to take when changes are detected
    $Action = {
        Write-Host "`nChange detected in apps/ directory..." -ForegroundColor Yellow
        Regenerate-Spec
        Regenerate-Frontend
    }
    
    # Register the event
    $onChange = Register-ObjectEvent -InputObject $Watcher -EventName Changed -Action $Action
    $onCreated = Register-ObjectEvent -InputObject $Watcher -EventName Created -Action $Action
    $onDeleted = Register-ObjectEvent -InputObject $Watcher -EventName Deleted -Action $Action
    $onRenamed = Register-ObjectEvent -InputObject $Watcher -EventName Renamed -Action $Action
    
    try {
        Write-Host "Watching for changes. Press Ctrl+C to exit."
        # Keep the script running
        while ($true) { Start-Sleep -Seconds 1 }
    } finally {
        # Clean up
        Unregister-Event -SourceIdentifier $onChange.Name
        Unregister-Event -SourceIdentifier $onCreated.Name
        Unregister-Event -SourceIdentifier $onDeleted.Name
        Unregister-Event -SourceIdentifier $onRenamed.Name
        $Watcher.Dispose()
    }
} else {
    # Single run mode
    Regenerate-Spec
    Regenerate-Frontend
    
    Write-Host "`n✓ API regeneration complete!" -ForegroundColor Green
}
