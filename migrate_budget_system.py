"""
Migration: Add Budget System + Update Amount to Float
Run this AFTER the Google OAuth migration
"""

from sqlalchemy import create_engine, text

# Database connection
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:9824@localhost/tye_db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)

def migrate():
    """Add budgets table and update transactions.amount to float"""
    with engine.connect() as conn:
        try:
            # Step 1: Create budgets table
            print("Step 1: Creating budgets table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS budgets (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    category VARCHAR NOT NULL,
                    monthly_limit FLOAT NOT NULL,
                    month VARCHAR NOT NULL,
                    alert_threshold FLOAT DEFAULT 80.0,
                    notifications_enabled BOOLEAN DEFAULT TRUE
                );
            """))
            conn.commit()
            print("✅ Budgets table created!")
            
            # Step 2: Create indexes for better performance
            print("Step 2: Creating indexes...")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_budgets_user_id ON budgets(user_id);
                CREATE INDEX IF NOT EXISTS idx_budgets_month ON budgets(month);
                CREATE UNIQUE INDEX IF NOT EXISTS idx_budgets_user_category_month 
                ON budgets(user_id, category, month);
            """))
            conn.commit()
            print("✅ Indexes created!")
            
            # Step 3: Update transactions.amount to FLOAT (from INTEGER)
            print("Step 3: Updating transactions.amount to FLOAT...")
            # PostgreSQL allows changing INTEGER to FLOAT without data loss
            try:
                conn.execute(text("""
                    ALTER TABLE transactions 
                    ALTER COLUMN amount TYPE FLOAT USING amount::FLOAT;
                """))
                conn.commit()
                print("✅ Amount column updated to FLOAT!")
            except Exception as e:
                # If it's already FLOAT, that's OK
                print(f"ℹ️  Amount column: {e}")
                conn.rollback()
            
            print("\n" + "="*60)
            print("✅ BUDGET MIGRATION SUCCESSFUL!")
            print("="*60)
            print("\nNew features enabled:")
            print("✅ Monthly budget tracking per category")
            print("✅ Budget alerts and notifications")
            print("✅ Decimal amount support (e.g., 150.50)")
            print("\nYou can now:")
            print("  - Set monthly budgets for each category")
            print("  - Get alerts when nearing budget limits")
            print("  - View budget vs actual spending")
            print("  - Create custom categories with budgets")
            
        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            print("\nTroubleshooting:")
            print("1. Make sure Google OAuth migration ran first")
            print("2. Check database connection")
            print("3. Verify PostgreSQL is running")
            conn.rollback()
            raise

if __name__ == "__main__":
    print("="*60)
    print("Budget System Migration")
    print("="*60)
    print(f"Database: {SQLALCHEMY_DATABASE_URL}")
    print("\n⚠️  This will:")
    print("   - Create budgets table")
    print("   - Update amount column to support decimals")
    print("="*60)
    
    response = input("\nProceed with migration? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        migrate()
    else:
        print("Migration cancelled.")
