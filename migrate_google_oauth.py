"""
Database Migration Script for Google OAuth
Adds google_id and picture columns to users table
IMPORTANT: Run this ONCE before starting your backend
"""

from sqlalchemy import create_engine, text

# Database connection (same as in database.py)
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:9824@localhost/tye_db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)

def migrate():
    """Add Google OAuth columns to users table"""
    with engine.connect() as conn:
        try:
            # Step 1: Add new columns
            print("Step 1: Adding google_id column...")
            conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS google_id VARCHAR UNIQUE;
            """))
            conn.commit()
            print("✅ google_id column added!")
            
            print("Step 2: Adding picture column...")
            conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS picture VARCHAR;
            """))
            conn.commit()
            print("✅ picture column added!")
            
            # Step 2: Make google_id NOT NULL for new users (existing can be NULL)
            print("Step 3: Creating index on google_id...")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_users_google_id 
                ON users(google_id);
            """))
            conn.commit()
            print("✅ Index created!")
            
            # Step 3: Remove password_hash column (if it exists)
            # WARNING: This will delete password data!
            # Comment out if you want to keep backward compatibility
            print("Step 4: Removing password_hash column...")
            try:
                conn.execute(text("""
                    ALTER TABLE users 
                    DROP COLUMN IF EXISTS password_hash;
                """))
                conn.commit()
                print("✅ password_hash column removed!")
            except Exception as e:
                print(f"⚠️  Note: {e}")
                print("   (This is OK if column doesn't exist)")
            
            print("\n" + "="*60)
            print("✅ MIGRATION SUCCESSFUL!")
            print("="*60)
            print("Your database is now ready for Google OAuth!")
            print("You can now start your backend: python main.py")
            
        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            print("\nTroubleshooting:")
            print("1. Make sure PostgreSQL is running")
            print("2. Check database connection in database.py")
            print("3. Verify database name 'tye_db' exists")
            conn.rollback()
            raise

if __name__ == "__main__":
    print("="*60)
    print("PostgreSQL Migration for Google OAuth")
    print("="*60)
    print(f"Database: {SQLALCHEMY_DATABASE_URL}")
    print("\n⚠️  WARNING: This will modify your users table!")
    print("   - Adds: google_id, picture columns")
    print("   - Removes: password_hash column")
    print("\nMake sure you have a backup if needed!")
    print("="*60)
    
    response = input("\nProceed with migration? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        migrate()
    else:
        print("Migration cancelled.")
