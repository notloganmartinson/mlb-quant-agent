import os
import sqlite3
from datetime import datetime
import sys

# Ensure project root is in path for imports
sys.path.append(os.getcwd())

from core.db_manager import MLBDbManager

def run_migrations():
    """
    Architects a safe, patch-based database migration system.
    Tracks which schema updates have already been applied to prevent data loss.
    """
    db_manager = MLBDbManager()
    db_path = db_manager.db_path
    migrations_dir = "migrations"
    
    # Ensure data directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn = db_manager._get_connection()
    cursor = conn.cursor()
    
    # 1. Ensure _migrations table exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS _migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE NOT NULL,
            applied_at TEXT NOT NULL
        )
    """)
    conn.commit()
    
    # 2. Read all .sql files in migrations/ directory
    if not os.path.exists(migrations_dir):
        print(f"Migrations directory '{migrations_dir}' not found.")
        conn.close()
        return

    migration_files = sorted([f for f in os.listdir(migrations_dir) if f.endswith(".sql")])
    
    # 3. Get applied migrations
    cursor.execute("SELECT filename FROM _migrations")
    applied_migrations = {row['filename'] for row in cursor.fetchall()}
    
    # 4. Execute new migrations
    new_migrations_applied = 0
    for filename in migration_files:
        if filename not in applied_migrations:
            print(f"Applying migration: {filename}...")
            file_path = os.path.join(migrations_dir, filename)
            try:
                with open(file_path, "r") as f:
                    migration_sql = f.read()
                
                # Execute the migration script
                cursor.executescript(migration_sql)
                
                # Log the migration
                cursor.execute(
                    "INSERT INTO _migrations (filename, applied_at) VALUES (?, ?)",
                    (filename, datetime.now().isoformat())
                )
                conn.commit()
                print(f"Successfully applied {filename}.")
                new_migrations_applied += 1
            except Exception as e:
                conn.rollback()
                print(f"Error applying migration {filename}: {e}")
                break
    
    if new_migrations_applied == 0:
        print("Database is up to date. No new migrations applied.")
    else:
        print(f"Applied {new_migrations_applied} new migration(s).")

    conn.close()

if __name__ == "__main__":
    run_migrations()
