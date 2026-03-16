"""
Database Models with Google OAuth and Budget System
Includes monthly budget tracking per category
"""

from sqlalchemy import Column, Integer, String, Float, Boolean
from database import Base
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship


class User(Base):
    """User model with Google OAuth"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    
    # Google OAuth fields
    google_id = Column(String, unique=True, index=True, nullable=False)
    picture = Column(String, nullable=True)


class Budget(Base):
    """Monthly budget for each category"""
    __tablename__ = "budgets"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category = Column(String, nullable=False)  # e.g., "Food", "Transport", or custom
    monthly_limit = Column(Float, nullable=False)  # Budget amount in BDT
    month = Column(String, nullable=False)  # Format: "2026-02" (YYYY-MM)
    
    # Notification settings
    alert_threshold = Column(Float, default=80.0)  # Alert when reaching X% of budget (default 80%)
    notifications_enabled = Column(Boolean, default=True)
    
    # Relationship
    owner = relationship("User", backref="budgets")


class Transaction(Base):
    """Transaction model"""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)  # Changed to Float to support decimals
    category = Column(String, nullable=False)
    description = Column(String, nullable=True)
    date = Column(String, nullable=False)  # Format: "2023-10-25"
    image_path = Column(String, nullable=True)
    raw_text = Column(String, nullable=True)
    
    # Link to User
    user_id = Column(Integer, ForeignKey("users.id"))
    
    # Relationship
    owner = relationship("User", back_populates="transactions")


# Setup bidirectional relationship
User.transactions = relationship("Transaction", back_populates="owner")