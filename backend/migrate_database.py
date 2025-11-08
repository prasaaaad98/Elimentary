"""
Migration script to add is_financial_report and classification_reason columns to documents table.
This script safely adds the new columns if they don't already exist.
"""
import sqlite3
from pathlib import Path
from app.config import settings


def migrate_database():
    """Add new columns to documents table if they don't exist."""
    # Extract database path from DATABASE_URL
    db_url = settings.DATABASE_URL
    if db_url.startswith("sqlite:///"):
        db_path = db_url.replace("sqlite:///", "")
        db_path = Path(db_path)
    else:
        print(f"Unsupported database URL: {db_url}")
        return
    
    if not db_path.exists():
        print(f"Database file {db_path} does not exist. It will be created on first run.")
        return
    
    print(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(documents)")
        columns = [row[1] for row in cursor.fetchall()]
        
        # Add is_financial_report column if it doesn't exist
        if "is_financial_report" not in columns:
            print("Adding is_financial_report column...")
            cursor.execute("ALTER TABLE documents ADD COLUMN is_financial_report BOOLEAN")
            print("[OK] Added is_financial_report column")
        else:
            print("[OK] is_financial_report column already exists")
        
        # Add classification_reason column if it doesn't exist
        if "classification_reason" not in columns:
            print("Adding classification_reason column...")
            cursor.execute("ALTER TABLE documents ADD COLUMN classification_reason TEXT")
            print("[OK] Added classification_reason column")
        else:
            print("[OK] classification_reason column already exists")
        
        # Add created_at column if it doesn't exist
        if "created_at" not in columns:
            print("Adding created_at column...")
            cursor.execute("ALTER TABLE documents ADD COLUMN created_at DATETIME")
            print("[OK] Added created_at column")
        else:
            print("[OK] created_at column already exists")
        
        # Add processed_at column if it doesn't exist
        if "processed_at" not in columns:
            print("Adding processed_at column...")
            cursor.execute("ALTER TABLE documents ADD COLUMN processed_at DATETIME")
            print("[OK] Added processed_at column")
        else:
            print("[OK] processed_at column already exists")
        
        # Add content_hash column if it doesn't exist (for deduplication)
        if "content_hash" not in columns:
            print("Adding content_hash column...")
            cursor.execute("ALTER TABLE documents ADD COLUMN content_hash TEXT")
            # Create index for faster lookups
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_content_hash ON documents(content_hash)")
            print("[OK] Added content_hash column and index")
        else:
            print("[OK] content_hash column already exists")
        
        # Set default created_at for existing rows that have NULL
        print("Setting default created_at for existing rows...")
        cursor.execute("""
            UPDATE documents 
            SET created_at = datetime('now') 
            WHERE created_at IS NULL
        """)
        updated_count = cursor.rowcount
        if updated_count > 0:
            print(f"[OK] Updated {updated_count} existing rows with default created_at")
        else:
            print("[OK] No rows needed updating")
        
        # Check if document_chunks table exists, create if not
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='document_chunks'
        """)
        table_exists = cursor.fetchone() is not None
        
        if not table_exists:
            print("Creating document_chunks table...")
            cursor.execute("""
                CREATE TABLE document_chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER NOT NULL,
                    page_number INTEGER,
                    chunk_index INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    embedding TEXT,
                    FOREIGN KEY (document_id) REFERENCES documents(id)
                )
            """)
            print("[OK] Created document_chunks table")
        else:
            print("[OK] document_chunks table already exists")
        
        conn.commit()
        print("\nMigration completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"\nError during migration: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate_database()

