"""
Database Migration Script
Adds image_path column to transactions table
"""

from sqlalchemy import create_engine, text

# Database connection (same as in database.py)
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:9824@localhost/tye_db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)

def migrate():
    with engine.connect() as conn:
        # Add image_path column to transactions table
        try:
            conn.execute(text("""
                ALTER TABLE transactions 
                ADD COLUMN IF NOT EXISTS image_path VARCHAR;
            """))
            conn.commit()
            print("[SUCCESS] Added image_path column to transactions table!")
        except Exception as e:
            print(f"[ERROR] {e}")

if __name__ == "__main__":
    print("Running database migration...")
    migrate()
    print("Migration complete!")
