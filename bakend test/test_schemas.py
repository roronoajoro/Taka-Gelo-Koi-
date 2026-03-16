"""
test_schemas.py
===============
Unit tests for schemas.py — the data validation layer of TYE.

Pydantic schemas are the gatekeepers between the HTTP request body
and the database.  If validation is wrong, bad data reaches the DB.

Run with:
    pytest tests/backend/test_schemas.py -v
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from pydantic import ValidationError
from schemas import (
    TransactionCreate,
    TransactionUpdate,
    BudgetCreate,
    BudgetUpdate,
    GoogleTokenRequest,
    BudgetOut,
    TransactionOut,
)


# ─────────────────────────────────────────────────────────────
# 1.  GoogleTokenRequest — what the frontend sends after login
# ─────────────────────────────────────────────────────────────

class TestGoogleTokenRequest:
    """
    WHY THIS MATTERS:
    The /auth/google endpoint receives this schema.  If it accepts
    an empty token, the backend will try to verify "" against Google
    and throw a confusing server error instead of a clean 422.
    """

    def test_valid_token(self):
        req = GoogleTokenRequest(token="eyJhbGciOiJSUzI1NiJ9.FAKE.TOKEN")
        assert req.token == "eyJhbGciOiJSUzI1NiJ9.FAKE.TOKEN"

    def test_missing_token_raises(self):
        with pytest.raises(ValidationError):
            GoogleTokenRequest()  # token is required

    def test_token_is_string(self):
        req = GoogleTokenRequest(token="abc123")
        assert isinstance(req.token, str)


# ─────────────────────────────────────────────────────────────
# 2.  TransactionCreate — what creates a new expense entry
# ─────────────────────────────────────────────────────────────

class TestTransactionCreate:
    """
    WHY THIS MATTERS:
    Every expense the user logs goes through this schema.
    The amount must be a float (not a string), category and date must
    be present, and user_id must be there to tie the record to a user.
    The backend also checks amount > 0, so we test boundary values.
    """

    def test_valid_transaction(self):
        tx = TransactionCreate(
            amount=450.0,
            category="Food",
            description="KFC Dhanmondi",
            date="2026-03-14",
            user_id=1
        )
        assert tx.amount == 450.0
        assert tx.category == "Food"
        assert tx.user_id == 1

    def test_amount_as_integer_coerced_to_float(self):
        tx = TransactionCreate(
            amount=500,     # int — Pydantic should coerce to float
            category="Transport",
            description="Uber",
            date="2026-03-14",
            user_id=1
        )
        assert isinstance(tx.amount, float)
        assert tx.amount == 500.0

    def test_missing_amount_raises(self):
        with pytest.raises(ValidationError):
            TransactionCreate(
                category="Food",
                description="Lunch",
                date="2026-03-14",
                user_id=1
            )

    def test_missing_user_id_raises(self):
        with pytest.raises(ValidationError):
            TransactionCreate(
                amount=100.0,
                category="Food",
                description="Lunch",
                date="2026-03-14"
            )

    def test_missing_category_raises(self):
        with pytest.raises(ValidationError):
            TransactionCreate(
                amount=100.0,
                description="Lunch",
                date="2026-03-14",
                user_id=1
            )

    def test_image_path_is_optional(self):
        tx = TransactionCreate(
            amount=100.0,
            category="Food",
            description="Lunch",
            date="2026-03-14",
            user_id=1
        )
        assert tx.image_path is None  # optional field defaults to None

    def test_with_image_path(self):
        tx = TransactionCreate(
            amount=100.0,
            category="Food",
            description="Lunch",
            date="2026-03-14",
            user_id=1,
            image_path="receipts/abc123.jpg"
        )
        assert tx.image_path == "receipts/abc123.jpg"

    def test_amount_string_raises(self):
        """
        Passing a non-numeric string should fail validation.
        Protects against payloads like { "amount": "abc" }.
        """
        with pytest.raises(ValidationError):
            TransactionCreate(
                amount="not-a-number",
                category="Food",
                description="Lunch",
                date="2026-03-14",
                user_id=1
            )


# ─────────────────────────────────────────────────────────────
# 3.  TransactionUpdate — partial edit of a transaction
# ─────────────────────────────────────────────────────────────

class TestTransactionUpdate:
    """
    WHY THIS MATTERS:
    The PUT /transactions/{id} endpoint uses this schema.
    Every field is Optional — the user might only want to fix the date
    or change the category without touching the amount.
    We must confirm the schema allows partial updates.
    """

    def test_all_fields_optional(self):
        update = TransactionUpdate()   # no fields — all optional
        assert update.amount is None
        assert update.category is None
        assert update.description is None
        assert update.date is None

    def test_update_amount_only(self):
        update = TransactionUpdate(amount=999.99)
        assert update.amount == 999.99
        assert update.category is None

    def test_update_category_only(self):
        update = TransactionUpdate(category="Utilities")
        assert update.category == "Utilities"
        assert update.amount is None

    def test_update_multiple_fields(self):
        update = TransactionUpdate(amount=200.0, category="Shopping", date="2026-02-01")
        assert update.amount == 200.0
        assert update.category == "Shopping"
        assert update.date == "2026-02-01"

    def test_invalid_amount_type_raises(self):
        with pytest.raises(ValidationError):
            TransactionUpdate(amount="free")


# ─────────────────────────────────────────────────────────────
# 4.  BudgetCreate — creates a monthly budget for a category
# ─────────────────────────────────────────────────────────────

class TestBudgetCreate:
    """
    WHY THIS MATTERS:
    Budgets are the heart of TYE's alert system.  If a budget is created
    with a wrong monthly_limit or invalid month format, the comparison
    against actual spending will silently produce wrong results.
    alert_threshold defaults to 80 (%) — tests confirm that default.
    """

    def test_valid_budget(self):
        budget = BudgetCreate(
            category="Food",
            monthly_limit=5000.0,
            month="2026-03"
        )
        assert budget.category == "Food"
        assert budget.monthly_limit == 5000.0
        assert budget.month == "2026-03"

    def test_alert_threshold_defaults_to_80(self):
        budget = BudgetCreate(
            category="Food",
            monthly_limit=5000.0,
            month="2026-03"
        )
        assert budget.alert_threshold == 80.0

    def test_notifications_enabled_defaults_true(self):
        budget = BudgetCreate(
            category="Transport",
            monthly_limit=2000.0,
            month="2026-03"
        )
        assert budget.notifications_enabled is True

    def test_custom_alert_threshold(self):
        budget = BudgetCreate(
            category="Food",
            monthly_limit=5000.0,
            month="2026-03",
            alert_threshold=50.0
        )
        assert budget.alert_threshold == 50.0

    def test_missing_category_raises(self):
        with pytest.raises(ValidationError):
            BudgetCreate(monthly_limit=5000.0, month="2026-03")

    def test_missing_monthly_limit_raises(self):
        with pytest.raises(ValidationError):
            BudgetCreate(category="Food", month="2026-03")

    def test_missing_month_raises(self):
        with pytest.raises(ValidationError):
            BudgetCreate(category="Food", monthly_limit=5000.0)

    def test_monthly_limit_coerced_from_int(self):
        budget = BudgetCreate(
            category="Rent",
            monthly_limit=20000,   # int
            month="2026-03"
        )
        assert isinstance(budget.monthly_limit, float)


# ─────────────────────────────────────────────────────────────
# 5.  BudgetUpdate — partial edit of existing budget
# ─────────────────────────────────────────────────────────────

class TestBudgetUpdate:
    """
    WHY THIS MATTERS:
    Users often want to raise/lower a budget mid-month or toggle
    notifications. Only the changed fields should be required.
    """

    def test_all_optional(self):
        upd = BudgetUpdate()
        assert upd.monthly_limit is None
        assert upd.alert_threshold is None
        assert upd.notifications_enabled is None

    def test_update_limit_only(self):
        upd = BudgetUpdate(monthly_limit=8000.0)
        assert upd.monthly_limit == 8000.0

    def test_disable_notifications(self):
        upd = BudgetUpdate(notifications_enabled=False)
        assert upd.notifications_enabled is False
