# app/routes/banking.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db  # Fixed import
from app.schemas.banking import (  # Fixed import
    BankAccountCreate,
    BankAccountUpdate,
    BankAccountResponse,
    BankAccountInDB
)
from app.crud.banking import crud_bank_account  # Fixed import
from app.crud.merchant import get_merchant  # Fixed import

router = APIRouter(
    prefix="/merchants/{merchant_id}/banking",
    tags=["banking"]
)

@router.post("/", response_model=BankAccountResponse)
def create_bank_account(
        merchant_id: int,
        bank_account: BankAccountCreate,
        db: Session = Depends(get_db)
):
    """Create a new bank account for a merchant"""
    # Verify merchant exists
    merchant = get_merchant.get(db, merchant_id)
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    db_bank_account = crud_bank_account.create(db, merchant_id, bank_account)
    response = BankAccountResponse.from_orm(db_bank_account)
    response.merchant_name = merchant.name
    return response


@router.get("/", response_model=List[BankAccountResponse])
def get_merchant_bank_accounts(
        merchant_id: int,
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=100),
        active_only: bool = Query(False),
        db: Session = Depends(get_db)
):
    """Get all bank accounts for a merchant"""
    merchant = get_merchant.get(db, merchant_id)
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    bank_accounts = crud_bank_account.get_by_merchant(
        db, merchant_id, skip, limit, active_only
    )

    response = []
    for account in bank_accounts:
        account_response = BankAccountResponse.from_orm(account)
        account_response.merchant_name = merchant.name
        response.append(account_response)

    return response


@router.get("/{bank_account_id}", response_model=BankAccountResponse)
def get_bank_account(
        merchant_id: int,
        bank_account_id: int,
        db: Session = Depends(get_db)
):
    """Get a specific bank account"""
    bank_account = crud_bank_account.get(db, bank_account_id)
    if not bank_account or bank_account.merchant_id != merchant_id:
        raise HTTPException(status_code=404, detail="Bank account not found")

    response = BankAccountResponse.from_orm(bank_account)
    response.merchant_name = bank_account.merchant.name
    return response


@router.patch("/{bank_account_id}", response_model=BankAccountResponse)
def update_bank_account(
        merchant_id: int,
        bank_account_id: int,
        bank_account_update: BankAccountUpdate,
        db: Session = Depends(get_db)
):
    """Update a bank account"""
    # Verify bank account belongs to merchant
    existing = crud_bank_account.get(db, bank_account_id)
    if not existing or existing.merchant_id != merchant_id:
        raise HTTPException(status_code=404, detail="Bank account not found")

    updated = crud_bank_account.update(db, bank_account_id, bank_account_update)
    response = BankAccountResponse.from_orm(updated)
    response.merchant_name = updated.merchant.name
    return response


@router.delete("/{bank_account_id}")
def delete_bank_account(
        merchant_id: int,
        bank_account_id: int,
        db: Session = Depends(get_db)
):
    """Delete a bank account"""
    # Verify bank account belongs to merchant
    existing = crud_bank_account.get(db, bank_account_id)
    if not existing or existing.merchant_id != merchant_id:
        raise HTTPException(status_code=404, detail="Bank account not found")

    try:
        crud_bank_account.delete(db, bank_account_id)
        return {"message": "Bank account deleted successfully"}
    except HTTPException as e:
        raise e


@router.post("/{bank_account_id}/set-primary", response_model=BankAccountResponse)
def set_primary_bank_account(
        merchant_id: int,
        bank_account_id: int,
        db: Session = Depends(get_db)
):
    """Set a bank account as primary for the merchant"""
    bank_account = crud_bank_account.set_primary(db, merchant_id, bank_account_id)
    if not bank_account:
        raise HTTPException(status_code=404, detail="Bank account not found")

    response = BankAccountResponse.from_orm(bank_account)
    response.merchant_name = bank_account.merchant.name
    return response


# Alternative routing structure - direct access
router_direct = APIRouter(
    prefix="/banking",
    tags=["banking"]
)


@router_direct.get("/{bank_account_id}", response_model=BankAccountResponse)
def get_bank_account_direct(
        bank_account_id: int,
        db: Session = Depends(get_db)
):
    """Get a bank account by ID directly"""
    bank_account = crud_bank_account.get(db, bank_account_id)
    if not bank_account:
        raise HTTPException(status_code=404, detail="Bank account not found")

    response = BankAccountResponse.from_orm(bank_account)
    response.merchant_name = bank_account.merchant.name
    return response