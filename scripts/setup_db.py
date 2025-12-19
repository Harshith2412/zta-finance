#!/usr/bin/env python3
"""
Database setup script for ZTA-Finance
Initializes MySQL database with required tables
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import mysql.connector
from mysql.connector import Error
from config.settings import settings


def parse_database_url(url: str) -> dict:
    """Parse MySQL database URL"""
    # Format: mysql://user:password@host:port/database
    url = url.replace('mysql://', '')
    
    if '@' in url:
        credentials, location = url.split('@')
        username, password = credentials.split(':')
    else:
        raise ValueError("Invalid database URL format")
    
    if '/' in location:
        host_port, database = location.split('/')
    else:
        raise ValueError("Database name not specified")
    
    if ':' in host_port:
        host, port = host_port.split(':')
        port = int(port)
    else:
        host = host_port
        port = 3306
    
    return {
        'host': host,
        'port': port,
        'user': username,
        'password': password,
        'database': database
    }


def create_connection(config: dict, database: bool = True):
    """Create MySQL connection"""
    try:
        conn_config = {
            'host': config['host'],
            'port': config['port'],
            'user': config['user'],
            'password': config['password']
        }
        
        if database:
            conn_config['database'] = config['database']
        
        connection = mysql.connector.connect(**conn_config)
        
        if connection.is_connected():
            print(f"✓ Connected to MySQL server")
            return connection
    except Error as e:
        print(f"✗ Error connecting to MySQL: {e}")
        return None


def create_database(config: dict):
    """Create database if it doesn't exist"""
    connection = create_connection(config, database=False)
    
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {config['database']} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            print(f"✓ Database '{config['database']}' created/verified")
            cursor.close()
            return True
        except Error as e:
            print(f"✗ Error creating database: {e}")
            return False
        finally:
            if connection.is_connected():
                connection.close()
    return False


def execute_sql_file(connection, filepath: str):
    """Execute SQL file"""
    try:
        with open(filepath, 'r') as f:
            sql_script = f.read()
        
        cursor = connection.cursor()
        
        # Split by semicolon and execute each statement
        statements = [stmt.strip() for stmt in sql_script.split(';') if stmt.strip()]
        
        for statement in statements:
            if statement:
                try:
                    cursor.execute(statement)
                except Error as e:
                    print(f"Warning: {e}")
                    print(f"Statement: {statement[:100]}...")
        
        connection.commit()
        cursor.close()
        print(f"✓ SQL file executed: {filepath}")
        return True
        
    except Error as e:
        print(f"✗ Error executing SQL file: {e}")
        return False
    except FileNotFoundError:
        print(f"✗ SQL file not found: {filepath}")
        return False


def verify_tables(connection):
    """Verify that tables were created"""
    try:
        cursor = connection.cursor()
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        
        if tables:
            print("\n✓ Tables created successfully:")
            for table in tables:
                print(f"  - {table[0]}")
            cursor.close()
            return True
        else:
            print("\n✗ No tables found")
            cursor.close()
            return False
            
    except Error as e:
        print(f"✗ Error verifying tables: {e}")
        return False


def main():
    """Main setup function"""
    print("=" * 70)
    print("ZTA-Finance Database Setup")
    print("=" * 70)
    print()
    
    # Parse database URL
    try:
        db_config = parse_database_url(settings.database_url)
    except Exception as e:
        print(f"✗ Error parsing database URL: {e}")
        print("Please check your DATABASE_URL in .env file")
        sys.exit(1)
    
    # Create database
    if not create_database(db_config):
        print("\n✗ Failed to create database")
        sys.exit(1)
    
    # Connect to database
    connection = create_connection(db_config, database=True)
    
    if not connection:
        print("\n✗ Failed to connect to database")
        sys.exit(1)
    
    # Execute SQL initialization script
    sql_file = Path(__file__).parent.parent / "database" / "init.sql"
    
    if execute_sql_file(connection, str(sql_file)):
        # Verify tables
        verify_tables(connection)
        print("\n" + "=" * 70)
        print("✓ Database setup completed successfully!")
        print("=" * 70)
    else:
        print("\n✗ Database setup failed")
        sys.exit(1)
    
    # Close connection
    if connection.is_connected():
        connection.close()
        print("\n✓ Connection closed")


if __name__ == "__main__":
    main()