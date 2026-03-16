from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# ⚠️ CHECK THIS: Ensure your username/password are correct.
# If you just installed Postgres, the default user is often 'postgres' and password might be what you set.
# format: postgresql://username:password@localhost/database_name
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:9824@localhost/tye_db"

# THIS IS THE MISSING VARIABLE 'engine'
engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Helper function to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()