"""
Pydantic Schemas with Google OAuth and Budget Support
"""

from pydantic import BaseModel, EmailStr
from typing import Optional


# ============ GOOGLE OAUTH SCHEMAS ============

class GoogleTokenRequest(BaseModel):
    """What frontend sends after Google login"""
    token: str


class UserOut(BaseModel):
    """What we send back after successful login"""
    id: int
    name: str
    email: EmailStr
    picture: Optional[str] = None
    google_id: str

    class Config:
        from_attributes = True


class GoogleLoginResponse(BaseModel):
    """Response after successful Google OAuth login"""
    message: str
    user_id: int
    name: str
    email: str
    picture: Optional[str] = None
    is_new_user: bool


# ============ BUDGET SCHEMAS ============

class BudgetCreate(BaseModel):
    """Create a new budget"""
    category: str
    monthly_limit: float
    month: str  # Format: "2026-02"
    alert_threshold: Optional[float] = 80.0
    notifications_enabled: Optional[bool] = True


class BudgetUpdate(BaseModel):
    """Update an existing budget"""
    monthly_limit: Optional[float] = None
    alert_threshold: Optional[float] = None
    notifications_enabled: Optional[bool] = None


class BudgetOut(BaseModel):
    """Budget response"""
    id: int
    user_id: int
    category: str
    monthly_limit: float
    month: str
    alert_threshold: float
    notifications_enabled: bool
    
    class Config:
        from_attributes = True


class BudgetStatus(BaseModel):
    """Budget status with spending info"""
    budget: BudgetOut
    spent: float
    remaining: float
    percentage_used: float
    is_over_budget: bool
    is_near_limit: bool  # True if >= alert_threshold


# ============ TRANSACTION SCHEMAS ============

class TransactionCreate(BaseModel):
    """What the user sends to create a transaction"""
    amount: float  # Changed to float
    category: str
    description: str
    date: str
    user_id: int
    image_path: Optional[str] = None


class TransactionOut(BaseModel):
    """What the API returns"""
    id: int
    amount: float  # Changed to float
    category: str
    description: str
    date: str
    image_path: Optional[str] = None
    raw_text: Optional[str] = None
    
    class Config:
        from_attributes = True


class MonthlyExpenseReport(BaseModel):
    """Monthly expense breakdown"""
    month: str
    total_spent: float
    category_breakdown: dict  # {category: amount}
    budget_comparison: Optional[dict] = None  # {category: {budget, spent, remaining}}


class TransactionUpdate(BaseModel):
    """Update an existing transaction"""
    amount: Optional[float] = None
    category: Optional[str] = None
    description: Optional[str] = None
    date: Optional[str] = None