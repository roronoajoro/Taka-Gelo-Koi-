"""
FastAPI Backend - Complete with Google OAuth, Budget System, and Monthly Reports
Version 3.0 - Production Ready
"""

from fastapi import FastAPI, HTTPException, Depends, status, File, UploadFile, Query
from sqlalchemy.orm import Session
from database import engine, get_db
import models, schemas
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from datetime import datetime
from collections import defaultdict
import os
import uuid
from pathlib import Path
import ocr_service
import parser_service

# Google OAuth imports
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests


# ============ CONFIGURATION ============

# Google OAuth Configuration
GOOGLE_CLIENT_ID = "114576452021-8e52ima3s04sk72it2emvdic9a7d3006.apps.googleusercontent.com"

# Create database tables
models.Base.metadata.create_all(bind=engine)

# Create uploads directory
UPLOAD_DIR = Path("uploads/receipts")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ============ FASTAPI APP SETUP ============

app = FastAPI(title="TYE - Track Your Expenses")

# Mount static files
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# CORS configuration
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "*"  # For development
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ GOOGLE OAUTH ENDPOINTS ============

@app.post("/auth/google", response_model=schemas.GoogleLoginResponse)
async def google_login(token_request: schemas.GoogleTokenRequest, db: Session = Depends(get_db)):
    """Authenticate user with Google OAuth token"""
    try:
        idinfo = id_token.verify_oauth2_token(
            token_request.token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )
        
        google_id = idinfo['sub']
        email = idinfo['email']
        name = idinfo.get('name', email.split('@')[0])
        picture = idinfo.get('picture', None)
        
        user = db.query(models.User).filter(models.User.google_id == google_id).first()
        
        is_new_user = False
        
        if not user:
            user = models.User(
                name=name,
                email=email,
                google_id=google_id,
                picture=picture
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            is_new_user = True
        else:
            user.name = name
            user.email = email
            user.picture = picture
            db.commit()
            db.refresh(user)
        
        return schemas.GoogleLoginResponse(
            message="Login successful",
            user_id=user.id,
            name=user.name,
            email=user.email,
            picture=user.picture,
            is_new_user=is_new_user
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google token: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication failed: {str(e)}"
        )


@app.get("/auth/verify/{user_id}")
def verify_user(user_id: int, db: Session = Depends(get_db)):
    """Verify if a user exists"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {
        "user_id": user.id,
        "name": user.name,
        "email": user.email,
        "picture": user.picture
    }


# ============ TRANSACTION ENDPOINTS ============

@app.post("/transactions/", response_model=schemas.TransactionOut)
def create_transaction(transaction: schemas.TransactionCreate, db: Session = Depends(get_db)):
    """
    Create a new transaction with validation
    """
    # Validate amount is positive
    if transaction.amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Amount must be greater than 0"
        )
    
    db_transaction = models.Transaction(**transaction.dict())
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    return db_transaction


@app.get("/transactions/{user_id}", response_model=list[schemas.TransactionOut])
def read_transactions(user_id: int, db: Session = Depends(get_db)):
    """Get all transactions for a specific user"""
    transactions = db.query(models.Transaction).filter(
        models.Transaction.user_id == user_id
    ).all()
    return transactions


@app.delete("/transactions/{transaction_id}")
def delete_transaction(transaction_id: int, db: Session = Depends(get_db)):
    """Delete a transaction"""
    transaction = db.query(models.Transaction).filter(
        models.Transaction.id == transaction_id
    ).first()
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    db.delete(transaction)
    db.commit()
    return {"message": "Transaction deleted"}


@app.put("/transactions/{transaction_id}", response_model=schemas.TransactionOut)
def update_transaction(
    transaction_id: int,
    update: schemas.TransactionUpdate,
    db: Session = Depends(get_db)
):
    """Edit an existing transaction's amount, category, description, or date"""
    transaction = db.query(models.Transaction).filter(
        models.Transaction.id == transaction_id
    ).first()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if update.amount is not None:
        if update.amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be > 0")
        transaction.amount = update.amount
    if update.category is not None:
        transaction.category = update.category
    if update.description is not None:
        transaction.description = update.description
    if update.date is not None:
        transaction.date = update.date

    db.commit()
    db.refresh(transaction)
    return transaction


@app.get("/summary/{user_id}")
def get_monthly_summary(
    user_id: int,
    month: str = Query(default=None, description="Month in YYYY-MM format, defaults to current month"),
    db: Session = Depends(get_db)
):
    """Get monthly spending summary. Pass ?month=YYYY-MM for any month."""
    txs = db.query(models.Transaction).filter(
        models.Transaction.user_id == user_id
    ).all()

    total_spent = 0.0
    category_breakdown: defaultdict = defaultdict(float)

    current_month = month if month else datetime.now().strftime("%Y-%m")

    for t in txs:
        if t.date.startswith(current_month):
            total_spent += t.amount
            category_breakdown[t.category] += t.amount

    return {
        "total_spent": total_spent,
        "month": current_month,
        "breakdown": dict(category_breakdown)
    }


# ============ BUDGET ENDPOINTS ============

@app.post("/budgets/", response_model=schemas.BudgetOut)
def create_budget(budget: schemas.BudgetCreate, user_id: int, db: Session = Depends(get_db)):
    """
    Create a new monthly budget for a category
    """
    # Check if budget already exists for this user/category/month
    existing = db.query(models.Budget).filter(
        models.Budget.user_id == user_id,
        models.Budget.category == budget.category,
        models.Budget.month == budget.month
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Budget for {budget.category} in {budget.month} already exists"
        )
    
    # Validate amount is positive
    if budget.monthly_limit <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Budget amount must be greater than 0"
        )
    
    db_budget = models.Budget(
        user_id=user_id,
        **budget.dict()
    )
    db.add(db_budget)
    db.commit()
    db.refresh(db_budget)
    return db_budget


@app.get("/budgets/{user_id}/{month}", response_model=list[schemas.BudgetOut])
def get_budgets(user_id: int, month: str, db: Session = Depends(get_db)):
    """
    Get all budgets for a user in a specific month
    Month format: YYYY-MM (e.g., "2026-02")
    """
    budgets = db.query(models.Budget).filter(
        models.Budget.user_id == user_id,
        models.Budget.month == month
    ).all()
    return budgets


@app.put("/budgets/{budget_id}", response_model=schemas.BudgetOut)
def update_budget(budget_id: int, budget_update: schemas.BudgetUpdate, db: Session = Depends(get_db)):
    """Update an existing budget"""
    budget = db.query(models.Budget).filter(models.Budget.id == budget_id).first()
    
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    
    # Update fields
    if budget_update.monthly_limit is not None:
        if budget_update.monthly_limit <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Budget amount must be greater than 0"
            )
        budget.monthly_limit = budget_update.monthly_limit
    
    if budget_update.alert_threshold is not None:
        budget.alert_threshold = budget_update.alert_threshold
    
    if budget_update.notifications_enabled is not None:
        budget.notifications_enabled = budget_update.notifications_enabled
    
    db.commit()
    db.refresh(budget)
    return budget


@app.delete("/budgets/{budget_id}")
def delete_budget(budget_id: int, db: Session = Depends(get_db)):
    """Delete a budget"""
    budget = db.query(models.Budget).filter(models.Budget.id == budget_id).first()
    
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    
    db.delete(budget)
    db.commit()
    return {"message": "Budget deleted"}


@app.get("/budget-status/{user_id}/{month}/{category}", response_model=schemas.BudgetStatus)
def get_budget_status(user_id: int, month: str, category: str, db: Session = Depends(get_db)):
    """
    Get budget status for a specific category
    Shows spent, remaining, percentage used, and alert status
    """
    # Get budget
    budget = db.query(models.Budget).filter(
        models.Budget.user_id == user_id,
        models.Budget.month == month,
        models.Budget.category == category
    ).first()
    
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    
    # Calculate spent amount for this category in this month
    transactions = db.query(models.Transaction).filter(
        models.Transaction.user_id == user_id,
        models.Transaction.category == category,
        models.Transaction.date.like(f"{month}%")
    ).all()
    
    spent = sum(t.amount for t in transactions)
    remaining = budget.monthly_limit - spent
    percentage_used = (spent / budget.monthly_limit * 100) if budget.monthly_limit > 0 else 0
    is_over_budget = spent > budget.monthly_limit
    is_near_limit = percentage_used >= budget.alert_threshold
    
    return schemas.BudgetStatus(
        budget=budget,
        spent=spent,
        remaining=remaining,
        percentage_used=percentage_used,
        is_over_budget=is_over_budget,
        is_near_limit=is_near_limit
    )


# ============ MONTHLY REPORT ENDPOINT ============

@app.get("/monthly-report/{user_id}", response_model=schemas.MonthlyExpenseReport)
def get_monthly_report(user_id: int, month: str, db: Session = Depends(get_db)):
    """
    Get detailed expense report for a specific month
    Includes total spent, category breakdown, and budget comparison
    
    Month format: YYYY-MM (e.g., "2026-02")
    """
    # Get all transactions for this month
    transactions = db.query(models.Transaction).filter(
        models.Transaction.user_id == user_id,
        models.Transaction.date.like(f"{month}%")
    ).all()
    
    # Calculate total and breakdown
    total_spent = 0
    category_breakdown = defaultdict(float)
    
    for t in transactions:
        total_spent += t.amount
        category_breakdown[t.category] += t.amount
    
    # Get budgets for this month
    budgets = db.query(models.Budget).filter(
        models.Budget.user_id == user_id,
        models.Budget.month == month
    ).all()
    
    # Create budget comparison
    budget_comparison = {}
    for budget in budgets:
        spent = category_breakdown.get(budget.category, 0)
        budget_comparison[budget.category] = {
            "budget": budget.monthly_limit,
            "spent": spent,
            "remaining": budget.monthly_limit - spent,
            "percentage_used": (spent / budget.monthly_limit * 100) if budget.monthly_limit > 0 else 0,
            "is_over_budget": spent > budget.monthly_limit
        }
    
    return schemas.MonthlyExpenseReport(
        month=month,
        total_spent=total_spent,
        category_breakdown=dict(category_breakdown),
        budget_comparison=budget_comparison if budget_comparison else None
    )


# ============ RECEIPT/OCR ENDPOINTS ============

@app.post("/upload-receipt/{transaction_id}")
async def upload_receipt(
    transaction_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload receipt image for a transaction"""
    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: JPEG, PNG, WebP"
        )
    
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    max_size = 10 * 1024 * 1024  # 10MB
    if file_size > max_size:
        raise HTTPException(
            status_code=400,
            detail="File too large. Maximum size is 10MB"
        )
    
    transaction = db.query(models.Transaction).filter(
        models.Transaction.id == transaction_id
    ).first()
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    file_extension = file.filename.split(".")[-1]
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = UPLOAD_DIR / unique_filename
    
    try:
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save file: {str(e)}"
        )
    
    transaction.image_path = f"receipts/{unique_filename}"
    db.commit()
    
    return {
        "message": "Receipt uploaded successfully",
        "image_path": transaction.image_path,
        "image_url": f"http://127.0.0.1:8000/uploads/{transaction.image_path}"
    }


@app.post("/extract-text/{transaction_id}")
def extract_text_from_receipt(transaction_id: int, db: Session = Depends(get_db)):
    """Extract text from receipt image using OCR"""
    transaction = db.query(models.Transaction).filter(
        models.Transaction.id == transaction_id
    ).first()
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    if not transaction.image_path:
        raise HTTPException(
            status_code=400,
            detail="No receipt image found for this transaction"
        )
    
    image_path = f"uploads/{transaction.image_path}"
    
    if not ocr_service.is_paddleocr_available():
        raise HTTPException(
            status_code=500,
            detail="OCR service is not available"
        )
    
    try:
        extracted_text = ocr_service.extract_text_from_image(image_path)
        transaction.raw_text = extracted_text
        db.commit()
        
        return {
            "message": "Text extracted successfully",
            "raw_text": extracted_text,
            "character_count": len(extracted_text)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"OCR failed: {str(e)}"
        )


@app.post("/parse-receipt/{transaction_id}")
def parse_receipt_data(transaction_id: int, db: Session = Depends(get_db)):
    """Parse OCR text to extract structured data"""
    transaction = db.query(models.Transaction).filter(
        models.Transaction.id == transaction_id
    ).first()
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    if not transaction.raw_text:
        raise HTTPException(
            status_code=400,
            detail="No OCR text found. Please extract text first."
        )
    
    parsed_data = parser_service.parse_receipt(transaction.raw_text)
    
    return {
        "message": "Receipt parsed successfully",
        "parsed_data": parsed_data
    }


@app.put("/transactions/{transaction_id}/autofill")
def autofill_transaction(
    transaction_id: int,
    amount: float = None,
    category: str = None,
    date: str = None,
    db: Session = Depends(get_db)
):
    """Update transaction with auto-parsed data"""
    transaction = db.query(models.Transaction).filter(
        models.Transaction.id == transaction_id
    ).first()
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    if amount is not None:
        if amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Amount must be greater than 0"
            )
        transaction.amount = amount
    if category is not None:
        transaction.category = category
    if date is not None:
        transaction.date = date
    
    db.commit()
    db.refresh(transaction)
    
    return {
        "message": "Transaction updated successfully",
        "transaction": transaction
    }


@app.post("/parse-image")
async def parse_image_instantly(file: UploadFile = File(...)):
    """Parse uploaded image instantly (before transaction creation)"""
    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: JPEG, PNG, WebP"
        )
    
    contents = await file.read()
    file_size = len(contents)
    
    if file_size > 10 * 1024 * 1024:  # 10MB
        raise HTTPException(
            status_code=400,
            detail="File too large. Max size: 10MB"
        )
    
    import tempfile
    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=f".{file.filename.split('.')[-1]}"
    ) as temp_file:
        temp_file.write(contents)
        temp_path = temp_file.name
    
    try:
        if not ocr_service.is_paddleocr_available():
            os.unlink(temp_path)
            raise HTTPException(
                status_code=500,
                detail="OCR service is not available"
            )
        
        extracted_text = ocr_service.extract_text_from_image(temp_path)
        parsed_data = parser_service.parse_receipt(extracted_text)
        
        os.unlink(temp_path)
        
        return {
            "message": "Image parsed successfully",
            "parsed_data": parsed_data,
            "raw_text": extracted_text
        }
    except Exception as e:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse image: {str(e)}"
        )


# ============ HEALTH CHECK ============

@app.get("/")
def read_root():
    """API health check"""
    return {
        "status": "running",
        "message": "TYE - Track Your Expenses API",
        "version": "3.0",
        "features": [
            "Google OAuth 2.0",
            "Budget tracking with alerts",
            "Monthly expense reports",
            "AI-powered OCR (Google Vision)",
            "Bengali + English support"
        ]
    }


@app.get("/health")
def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "database": "connected",
        "auth": "Google OAuth configured",
        "ocr": "available" if ocr_service.is_paddleocr_available() else "unavailable",
        "features": {
            "budget_system": True,
            "monthly_reports": True,
            "negative_validation": True
        }
    }