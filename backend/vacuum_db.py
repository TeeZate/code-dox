import sqlite3
import os
import sys

def vacuum_database(db_path):
    print(f"Attempting to vacuum database at: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"Error: Database file not found at {db_path}")
        return False
    
    try:
        # Connect to the database
        print("Connecting to database...")
        conn = sqlite3.connect(db_path)
        
        # Get initial size
        initial_size = os.path.getsize(db_path) / (1024 * 1024)  # Size in MB
        print(f"Initial database size: {initial_size:.2f} MB")
        
        # Execute VACUUM
        print("Executing VACUUM command (this may take a while)...")
        conn.execute("VACUUM;")
        
        # Commit and close
        conn.commit()
        conn.close()
        
        # Get final size
        final_size = os.path.getsize(db_path) / (1024 * 1024)  # Size in MB
        print(f"Final database size: {final_size:.2f} MB")
        print(f"Space reclaimed: {initial_size - final_size:.2f} MB")
        
        return True
    except Exception as e:
        print(f"Error vacuuming database: {str(e)}")
        return False

if __name__ == "__main__":
    # Default database path
    db_path = "db.sqlite3"
    
    # Allow custom path from command line
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    
    success = vacuum_database(db_path)
    if success:
        print("Database vacuum completed successfully!")
    else:
        print("Database vacuum failed.")
