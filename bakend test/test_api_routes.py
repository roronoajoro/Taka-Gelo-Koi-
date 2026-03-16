"""
test_api_routes.py
==================
Integration tests for the FastAPI backend routes defined in main.py.

Uses an in-memory SQLite database (no Postgres needed) and FastAPI's
TestClient so every test runs quickly without any network I/O.

Run with:
    pytest tests/backend/test_api_routes.py -v
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ── Use SQLite in-memory so tests never touch the real Postgres DB ──
TEST_DATABASE_URL = "sqlite:///./test_tye.db"

# Patch database before importing the app
import database as db_module
engine_test = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)
db_module.engine = engine_test
db_module.SessionLocal = TestingSessionLocal

import models
models.Base.metadata.create_all(bind=engine_test)

from main import app, get_db

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def create_test_user(db):
    """Insert a bare-minimum User row for foreign-key constraints."""
    user = models.User(
        name="Test User",
        email="test@example.com",
        google_id="google_test_001",
        picture=None
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ─────────────────────────────────────────────────────────────
# 1.  Health endpoints
# ─────────────────────────────────────────────────────────────

class TestHealthEndpoints:
    """
    WHY THIS MATTERS:
    The "/" and "/health" routes let ops teams (and CI pipelines) quickly
    confirm the backend is running.  If these fail, every other endpoint
    is suspect.
    """

    def test_root_returns_200(self):
        res = client.get("/")
        assert res.status_code == 200

    def test_root_has_status_key(self):
        res = client.get("/")
        assert res.json()["status"] == "running"

    def test_health_returns_200(self):
        res = client.get("/health")
        assert res.status_code == 200

    def test_health_database_connected(self):
        res = client.get("/health")
        assert res.json()["database"] == "connected"


# ─────────────────────────────────────────────────────────────
# 2.  Transaction CRUD
# ─────────────────────────────────────────────────────────────

class TestTransactionEndpoints:
    """
    WHY THIS MATTERS:
    Transactions are the core unit of TYE. Every feature — budgets,
    reports, summaries — is derived from the transactions table.
    These tests verify that Create / Read / Update / Delete all work,
    and that validation rejects bad data (negative amounts, missing fields).
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        """Create a fresh user before each test; clean up after."""
        models.Base.metadata.create_all(bind=engine_test)
        db = TestingSessionLocal()
        self.user = create_test_user(db)
        self.user_id = self.user.id
        db.close()
        yield
        # Teardown
        db = TestingSessionLocal()
        db.query(models.Transaction).delete()
        db.query(models.Budget).delete()
        db.query(models.User).delete()
        db.commit()
        db.close()

    # ── CREATE ─────────────────────────────────────────────────

    def test_create_transaction_success(self):
        res = client.post("/transactions/", json={
            "amount": 450.0,
            "category": "Food",
            "description": "KFC Dhanmondi",
            "date": "2026-03-14",
            "user_id": self.user_id
        })
        assert res.status_code == 200
        data = res.json()
        assert data["amount"] == 450.0
        assert data["category"] == "Food"
        assert "id" in data

    def test_create_transaction_negative_amount_rejected(self):
        """
        The backend explicitly blocks amount <= 0.
        Negative spending would corrupt budget calculations.
        """
        res = client.post("/transactions/", json={
            "amount": -100.0,
            "category": "Food",
            "description": "Bad entry",
            "date": "2026-03-14",
            "user_id": self.user_id
        })
        assert res.status_code == 400

    def test_create_transaction_zero_amount_rejected(self):
        res = client.post("/transactions/", json={
            "amount": 0.0,
            "category": "Food",
            "description": "Zero",
            "date": "2026-03-14",
            "user_id": self.user_id
        })
        assert res.status_code == 400

    def test_create_transaction_missing_amount_rejected(self):
        res = client.post("/transactions/", json={
            "category": "Food",
            "description": "No amount",
            "date": "2026-03-14",
            "user_id": self.user_id
        })
        assert res.status_code == 422   # Pydantic validation error

    # ── READ ───────────────────────────────────────────────────

    def test_read_transactions_empty_list(self):
        res = client.get(f"/transactions/{self.user_id}")
        assert res.status_code == 200
        assert res.json() == []

    def test_read_transactions_returns_created(self):
        client.post("/transactions/", json={
            "amount": 300.0,
            "category": "Transport",
            "description": "Uber",
            "date": "2026-03-14",
            "user_id": self.user_id
        })
        res = client.get(f"/transactions/{self.user_id}")
        assert res.status_code == 200
        assert len(res.json()) == 1
        assert res.json()[0]["description"] == "Uber"

    def test_read_transactions_only_own_user(self):
        """Transactions from user A must not appear in user B's list."""
        # Create second user
        db = TestingSessionLocal()
        user2 = models.User(
            name="User Two", email="two@test.com",
            google_id="google_test_002"
        )
        db.add(user2); db.commit(); db.refresh(user2)
        uid2 = user2.id
        db.close()

        # User 1 logs a transaction
        client.post("/transactions/", json={
            "amount": 500.0, "category": "Food",
            "description": "My lunch", "date": "2026-03-14",
            "user_id": self.user_id
        })
        # User 2 should see no transactions
        res = client.get(f"/transactions/{uid2}")
        assert res.json() == []

    # ── UPDATE ─────────────────────────────────────────────────

    def test_update_transaction_amount(self):
        create_res = client.post("/transactions/", json={
            "amount": 200.0, "category": "Food",
            "description": "Lunch", "date": "2026-03-14",
            "user_id": self.user_id
        })
        tx_id = create_res.json()["id"]
        upd_res = client.put(f"/transactions/{tx_id}", json={"amount": 350.0})
        assert upd_res.status_code == 200
        assert upd_res.json()["amount"] == 350.0

    def test_update_nonexistent_transaction_returns_404(self):
        res = client.put("/transactions/999999", json={"amount": 100.0})
        assert res.status_code == 404

    def test_update_to_negative_amount_rejected(self):
        create_res = client.post("/transactions/", json={
            "amount": 200.0, "category": "Food",
            "description": "Lunch", "date": "2026-03-14",
            "user_id": self.user_id
        })
        tx_id = create_res.json()["id"]
        upd_res = client.put(f"/transactions/{tx_id}", json={"amount": -50.0})
        assert upd_res.status_code == 400

    # ── DELETE ─────────────────────────────────────────────────

    def test_delete_transaction(self):
        create_res = client.post("/transactions/", json={
            "amount": 100.0, "category": "Food",
            "description": "Coffee", "date": "2026-03-14",
            "user_id": self.user_id
        })
        tx_id = create_res.json()["id"]
        del_res = client.delete(f"/transactions/{tx_id}")
        assert del_res.status_code == 200
        # Verify it's gone
        list_res = client.get(f"/transactions/{self.user_id}")
        assert len(list_res.json()) == 0

    def test_delete_nonexistent_returns_404(self):
        res = client.delete("/transactions/999999")
        assert res.status_code == 404


# ─────────────────────────────────────────────────────────────
# 3.  Monthly Summary endpoint
# ─────────────────────────────────────────────────────────────

class TestSummaryEndpoint:
    """
    WHY THIS MATTERS:
    The /summary endpoint powers the stat cards at the top of the
    Dashboard (total spent, category breakdown). If the month filter
    is wrong, expenses from other months pollute the current totals.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        models.Base.metadata.create_all(bind=engine_test)
        db = TestingSessionLocal()
        self.user = create_test_user(db)
        self.uid = self.user.id
        db.close()
        yield
        db = TestingSessionLocal()
        db.query(models.Transaction).delete()
        db.query(models.Budget).delete()
        db.query(models.User).delete()
        db.commit()
        db.close()

    def _add_tx(self, amount, category, date):
        client.post("/transactions/", json={
            "amount": amount, "category": category,
            "description": "test", "date": date,
            "user_id": self.uid
        })

    def test_summary_empty_for_new_user(self):
        res = client.get(f"/summary/{self.uid}?month=2026-03")
        assert res.status_code == 200
        assert res.json()["total_spent"] == 0.0

    def test_summary_correct_total(self):
        self._add_tx(300.0, "Food", "2026-03-10")
        self._add_tx(250.0, "Transport", "2026-03-12")
        res = client.get(f"/summary/{self.uid}?month=2026-03")
        assert res.json()["total_spent"] == 550.0

    def test_summary_filters_by_month(self):
        """Transactions in February must NOT appear in March summary."""
        self._add_tx(500.0, "Food", "2026-02-15")   # different month
        self._add_tx(200.0, "Food", "2026-03-01")   # this month
        res = client.get(f"/summary/{self.uid}?month=2026-03")
        assert res.json()["total_spent"] == 200.0

    def test_summary_category_breakdown(self):
        self._add_tx(400.0, "Food", "2026-03-10")
        self._add_tx(200.0, "Transport", "2026-03-11")
        res = client.get(f"/summary/{self.uid}?month=2026-03")
        breakdown = res.json()["breakdown"]
        assert breakdown["Food"] == 400.0
        assert breakdown["Transport"] == 200.0

    def test_summary_returns_month_field(self):
        res = client.get(f"/summary/{self.uid}?month=2026-03")
        assert res.json()["month"] == "2026-03"


# ─────────────────────────────────────────────────────────────
# 4.  Budget endpoints
# ─────────────────────────────────────────────────────────────

class TestBudgetEndpoints:
    """
    WHY THIS MATTERS:
    Budgets drive TYE's alert system. If a budget can be created
    twice for the same category/month, the app can't decide which
    limit to enforce.  We verify the duplicate guard works.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        models.Base.metadata.create_all(bind=engine_test)
        db = TestingSessionLocal()
        self.user = create_test_user(db)
        self.uid = self.user.id
        db.close()
        yield
        db = TestingSessionLocal()
        db.query(models.Transaction).delete()
        db.query(models.Budget).delete()
        db.query(models.User).delete()
        db.commit()
        db.close()

    def test_create_budget_success(self):
        res = client.post(f"/budgets/?user_id={self.uid}", json={
            "category": "Food",
            "monthly_limit": 5000.0,
            "month": "2026-03"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["category"] == "Food"
        assert data["monthly_limit"] == 5000.0

    def test_duplicate_budget_rejected(self):
        """Two budgets for Food/2026-03 should be blocked."""
        payload = {
            "category": "Food",
            "monthly_limit": 5000.0,
            "month": "2026-03"
        }
        client.post(f"/budgets/?user_id={self.uid}", json=payload)
        res = client.post(f"/budgets/?user_id={self.uid}", json=payload)
        assert res.status_code == 400

    def test_get_budgets_for_month(self):
        client.post(f"/budgets/?user_id={self.uid}", json={
            "category": "Food", "monthly_limit": 5000.0, "month": "2026-03"
        })
        res = client.get(f"/budgets/{self.uid}/2026-03")
        assert res.status_code == 200
        assert len(res.json()) >= 1

    def test_delete_budget(self):
        create_res = client.post(f"/budgets/?user_id={self.uid}", json={
            "category": "Transport",
            "monthly_limit": 2000.0,
            "month": "2026-03"
        })
        budget_id = create_res.json()["id"]
        del_res = client.delete(f"/budgets/{budget_id}")
        assert del_res.status_code == 200
