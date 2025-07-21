#!/usr/bin/env python
"""
Test script to verify Schemathesis hooks are working correctly.

This script:
1. Sets up the environment to load our hooks
2. Runs schemathesis on just a few endpoints
3. Shows debug output to confirm hooks are being applied
4. Tests specifically the dev-auth endpoint that was failing
"""
import os
import sys
import subprocess
import tempfile
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_schemathesis_hooks")

# Ensure we're in the project root
project_root = Path(__file__).parent
os.chdir(project_root)

def get_ci_token():
    """Get a CI token for authentication."""
    logger.info("Getting CI auth token...")
    result = subprocess.run(
        [sys.executable, "manage.py", "get_ci_token", "--settings=aquamind.settings_ci"],
        capture_output=True,
        text=True,
        check=True
    )
    token = result.stdout.strip()
    logger.info(f"Token obtained (length: {len(token)})")
    return token

def run_django_server():
    """Start the Django server for testing."""
    logger.info("Starting Django server...")
    # Apply migrations first
    subprocess.run(
        [sys.executable, "manage.py", "migrate", "--settings=aquamind.settings_ci", "--noinput"],
        check=True
    )
    
    # Start the server
    server_process = subprocess.Popen(
        [sys.executable, "manage.py", "runserver", "0.0.0.0:8000", "--settings=aquamind.settings_ci"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    
    # Wait a moment for the server to start
    import time
    time.sleep(3)
    
    return server_process

def run_schemathesis_test(token, endpoints=None):
    """Run schemathesis against specified endpoints."""
    logger.info("Running schemathesis tests...")
    
    # Set environment variable for hooks
    # Use Python dotted-path notation so Schemathesis can import the module
    # correctly on any platform / runner.
    os.environ["SCHEMATHESIS_HOOKS"] = "aquamind.utils.schemathesis_hooks"
    logger.info(f"SCHEMATHESIS_HOOKS set to: {os.environ.get('SCHEMATHESIS_HOOKS')}")
    
    # Resolve the schemathesis executable from the same venv that is running
    # this script.  This avoids the “package … cannot be directly executed”
    # error we observed when trying to use ``python -m schemathesis``.
    schemathesis_exe = Path(sys.executable).with_name("schemathesis.exe")

    # Create command with base arguments
    cmd = [
        str(schemathesis_exe),
        "run",
        "--base-url=http://127.0.0.1:8000",
        "--checks", "all",
        "--hypothesis-max-examples=3",  # Minimal number for faster testing
        "--hypothesis-suppress-health-check=filter_too_much,data_too_large",
        "--hypothesis-derandomize",
        "--show-errors-tracebacks",
        "--header", f"Authorization: Token {token}",
    ]
    
    # Add specific endpoints if provided
    if endpoints:
        for endpoint in endpoints:
            cmd.extend(["--endpoint", endpoint])
    
    # Add the schema file
    cmd.append("api/openapi.yaml")
    
    # Run schemathesis and capture output
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt') as output_file:
        logger.info(f"Saving output to {output_file.name}")
        
        process = subprocess.Popen(
            cmd,
            stdout=output_file,
            stderr=subprocess.STDOUT,
            text=True
        )
        process.wait()
        
        # Read and display output
        output_file.seek(0)
        output = output_file.read()
        
    return output, process.returncode

def main():
    """Main test function."""
    try:
        # Get auth token
        token = get_ci_token()
        
        # Start Django server
        server_process = run_django_server()
        
        try:
            # Test specific problematic endpoints
            endpoints = [
                "/api/v1/auth/dev-auth/",  # The dev-auth endpoint that was failing
                "/api/v1/scenario/scenarios/",  # A scenario endpoint with 401 issues
                "/api/v1/environmental/readings/recent/"  # An endpoint that needs response type fixing
            ]
            
            output, return_code = run_schemathesis_test(token, endpoints)
            
            # Print summary of results
            logger.info("\n" + "="*80)
            logger.info("SCHEMATHESIS TEST RESULTS")
            logger.info("="*80)
            
            # Check for hook activation messages
            hook_loaded = "AquaMind Schemathesis hooks loaded" in output
            dev_auth_fixed = "Fixing dev-auth response" in output
            action_response_fixed = "Fixing action response type" in output
            
            logger.info(f"Hooks loaded: {'✅' if hook_loaded else '❌'}")
            logger.info(f"Dev-auth hook applied: {'✅' if dev_auth_fixed else '❌'}")
            logger.info(f"Action response type hook applied: {'✅' if action_response_fixed else '❌'}")
            logger.info(f"Return code: {return_code} {'✅' if return_code == 0 else '❌'}")
            
            # Print the first 20 lines and last 20 lines of output
            lines = output.splitlines()
            logger.info("\nFirst 20 lines of output:")
            for line in lines[:20]:
                print(line)
                
            logger.info("\nLast 20 lines of output:")
            for line in lines[-20:]:
                print(line)
                
            # Save full output to a file
            with open("schemathesis_test_output.txt", "w") as f:
                f.write(output)
            logger.info(f"\nFull output saved to schemathesis_test_output.txt")
            
            return return_code
            
        finally:
            # Always stop the server
            logger.info("Stopping Django server...")
            server_process.terminate()
            server_process.wait()
            
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
