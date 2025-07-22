# test_ci_auth.ps1 - Test Schemathesis authentication flow in CI-like environment
# 
# This script simulates the CI environment to test the Schemathesis authentication
# flow with the hooks-based approach. It validates that the authentication token
# is properly injected by the hooks rather than passed via command-line arguments.

# Stop on first error
$ErrorActionPreference = "Stop"

# Variables
$djangoSettings = "aquamind.settings_ci"
$serverJob = $null
$serverPID = $null

# Cleanup function to ensure server is always killed
function Cleanup {
    Write-Host "🧹 Cleaning up..."
    if ($serverJob -ne $null) {
        Write-Host "Stopping Django server job"
        Stop-Job -Job $serverJob
        Remove-Job -Job $serverJob -Force
    }
    if ($serverPID -ne $null) {
        Write-Host "Killing Django server process (PID: $serverPID)"
        Stop-Process -Id $serverPID -Force -ErrorAction SilentlyContinue
    }
    Write-Host "Done."
}

try {
    # Activate virtual environment (already handled by caller)
    Write-Host "🔄 Applying migrations using CI settings..."
    python manage.py migrate --settings=$djangoSettings --noinput

    Write-Host "🔑 Getting CI auth token..."
    # First run with debug to see any issues
    python manage.py get_ci_token --settings=$djangoSettings --debug
    
    # Now capture the actual token
    $token = python manage.py get_ci_token --settings=$djangoSettings
    
    # Validate token
    if ([string]::IsNullOrEmpty($token)) {
        throw "Failed to obtain CI auth token"
    }
    
    Write-Host "✅ CI auth token ready (length: $($token.Length))"
    
    # Export environment variables for Schemathesis hooks
    Write-Host "🔌 Setting up Schemathesis hooks..."
    $env:SCHEMATHESIS_AUTH_TOKEN = $token
    $env:SCHEMATHESIS_HOOKS = "aquamind.utils.schemathesis_hooks"
    
    Write-Host "🚀 Starting Django server in background..."
    $serverJob = Start-Job -ScriptBlock {
        param($settings)
        python manage.py runserver 0.0.0.0:8000 --settings=$settings
    } -ArgumentList $djangoSettings
    
    # Get the PID of the Python process
    Start-Sleep -Seconds 2
    $serverPID = (Get-WmiObject Win32_Process -Filter "CommandLine LIKE '%runserver 0.0.0.0:8000%'").ProcessId
    Write-Host "Django server started with PID: $serverPID"
    
    Write-Host "⏳ Waiting for server to be ready..."
    $attempts = 0
    $maxAttempts = 30
    $ready = $false
    
    while (-not $ready -and $attempts -lt $maxAttempts) {
        $attempts++
        try {
            $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/" -UseBasicParsing -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200 -or $response.StatusCode -eq 302) {
                $ready = $true
            }
        } catch {
            Write-Host "  Still waiting... (attempt $attempts/$maxAttempts)"
            Start-Sleep -Seconds 2
        }
    }
    
    if (-not $ready) {
        throw "Server did not start in time after $maxAttempts attempts"
    }
    
    Write-Host "✅ Django server is up and running"
    
    Write-Host "🧪 Running Schemathesis tests..."
    Write-Host "Note: No --header parameter is used - auth should be injected by hooks"
    
    # Run Schemathesis with hooks but WITHOUT explicit auth header
    schemathesis run `
        --base-url=http://127.0.0.1:8000 `
        --checks all `
        --hypothesis-max-examples=3 `
        --hypothesis-suppress-health-check=filter_too_much,data_too_large `
        --show-errors-tracebacks `
        api/openapi.yaml
    
    $status = $LASTEXITCODE
    
    if ($status -eq 0) {
        Write-Host "✅ Schemathesis tests passed successfully!"
    } else {
        Write-Host "❌ Schemathesis detected contract test failures"
    }
    
    Write-Host "Test complete with status: $status"
    exit $status

} catch {
    Write-Host "❌ Error: $_" -ForegroundColor Red
    exit 1
} finally {
    # Always run cleanup
    Cleanup
}
