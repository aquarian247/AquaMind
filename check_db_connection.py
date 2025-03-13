#!/usr/bin/env python
"""
Simple script to test PostgreSQL connection with multiple configurations.
"""
import psycopg2
import sys
import socket

def check_connection(host, port="5432", user="postgres", password="postgres", dbname="postgres"):
    """Test connection to PostgreSQL."""
    print(f"Attempting to connect to PostgreSQL at {host}:{port}...")
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            dbname=dbname,
            connect_timeout=3  # Add a timeout to avoid long waits
        )
        cur = conn.cursor()
        cur.execute('SELECT version();')
        version = cur.fetchone()
        print(f"Connection successful to {host}: {version[0]}")
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Connection failed to {host}: {e}")
        return False

def get_container_ip(container_name):
    """Try to resolve container name to IP address."""
    try:
        return socket.gethostbyname(container_name)
    except socket.gaierror:
        return None

if __name__ == "__main__":
    # Try multiple connection configurations
    hosts_to_try = [
        "timescale-db",  # Container name
        "localhost",     # Local connection
        "0.0.0.0",       # All interfaces
        "127.0.0.1"      # Localhost IP
    ]
    
    # Try to resolve container IP if possible
    container_ip = get_container_ip("timescale-db")
    if container_ip and container_ip not in hosts_to_try:
        hosts_to_try.insert(1, container_ip)
    
    # Use the known correct password
    passwords_to_try = ["aquapass12345"]
    
    success = False
    for host in hosts_to_try:
        for password in passwords_to_try:
            if check_connection(host=host, password=password):
                success = True
                print(f"✅ Successfully connected to PostgreSQL at {host}:5432 with password: {password or 'empty string'}")
                break
        if success:
            break
    
    if not success:
        print("❌ Failed to connect to PostgreSQL with any configuration")
    
    sys.exit(0 if success else 1)
