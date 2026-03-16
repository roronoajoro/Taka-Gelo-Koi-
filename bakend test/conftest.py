"""
conftest.py
===========
Shared pytest fixtures for TYE backend tests.
Placed in the tests/backend/ folder so pytest picks it up automatically.
"""

import pytest
import sys
import os

# Add project root to path so all imports resolve cleanly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import models

TEST_DB_URL = "sqlite:///./conftest_test.db"

@pytest.fixture(scope="session")
def test_engine():
    """Session-scoped SQLite engine — created once for the whole test run."""
    engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    models.Base.metadata.create_all(bind=engine)
    yield engine
    models.Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(test_engine):
    """Function-scoped DB session — rolls back after every test for isolation."""
    connection = test_engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def sample_user(db_session):
    """A ready-made User object for tests that need a foreign key."""
    user = models.User(
        name="Test User",
        email="test@tye.com",
        google_id="google_conftest_001",
        picture=None
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_transaction(db_session, sample_user):
    """A ready-made Transaction tied to sample_user."""
    tx = models.Transaction(
        amount=450.0,
        category="Food",
        description="KFC",
        date="2026-03-14",
        user_id=sample_user.id
    )
    db_session.add(tx)
    db_session.commit()
    db_session.refresh(tx)
    return tx


@pytest.fixture
def sample_budget(db_session, sample_user):
    """A ready-made Budget tied to sample_user."""
    budget = models.Budget(
        user_id=sample_user.id,
        category="Food",
        monthly_limit=5000.0,
        month="2026-03",
        alert_threshold=80.0,
        notifications_enabled=True
    )
    db_session.add(budget)
    db_session.commit()
    db_session.refresh(budget)
    return budget
