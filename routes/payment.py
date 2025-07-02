# app/routes/payment.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

from app.database import get_db
from app.schemas.payment import (
    Payment, PaymentCreate, PaymentUpdate, PaymentFilter,
    PaymentSummary, PaymentType
)
from app.crud import payment as crud

router = APIRouter(
    prefix="/api/v1/payments",
    tags=["payments"]
)


@router.post("/", response_model=Payment, status_code=201)
def create_payment(
    payment: PaymentCreate,
    db: Session = Depends(get_db)
):
    """Create a new payment record"""
    # TODO: Verify deal_id exists when Deal model is created
    return crud.create_payment(db=db, payment=payment)


@router.get("/", response_model=List[Payment])
def list_payments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    deal_id: Optional[int] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    type: Optional[PaymentType] = None,
    bounced: Optional[bool] = None,
    min_amount: Optional[Decimal] = None,
    max_amount: Optional[Decimal] = None,
    db: Session = Depends(get_db)
):
    """Get list of payments with optional filtering"""
    filters = PaymentFilter(
        deal_id=deal_id,
        date_from=date_from,
        date_to=date_to,
        type=type,
        bounced=bounced,
        min_amount=min_amount,
        max_amount=max_amount
    )
    return crud.get_payments(db=db, skip=skip, limit=limit, filters=filters)


@router.get("/recent", response_model=List[Payment])
def get_recent_payments(
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Get recent payments within specified number of days"""
    return crud.get_recent_payments(db=db, days=days, limit=limit)


@router.get("/bounced", response_model=List[Payment])
def get_bounced_payments(
    deal_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get all bounced payments"""
    return crud.get_bounced_payments(db=db, deal_id=deal_id)


@router.get("/stats/by-type")
def get_payment_stats_by_type(
    deal_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get payment statistics grouped by payment type"""
    stats = crud.get_payment_stats_by_type(db=db, deal_id=deal_id)
    return [
        {
            "type": stat.type,
            "count": stat.count,
            "total_amount": float(stat.total_amount) if stat.total_amount else 0,
            "avg_amount": float(stat.avg_amount) if stat.avg_amount else 0
        }
        for stat in stats
    ]


@router.get("/{payment_id}", response_model=Payment)
def get_payment(
    payment_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific payment by ID"""
    payment = crud.get_payment(db=db, payment_id=payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


@router.put("/{payment_id}", response_model=Payment)
def update_payment(
    payment_id: int,
    payment_update: PaymentUpdate,
    db: Session = Depends(get_db)
):
    """Update a payment record"""
    payment = crud.update_payment(db=db, payment_id=payment_id, payment_update=payment_update)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


@router.patch("/{payment_id}/bounce", response_model=Payment)
def mark_payment_bounced(
    payment_id: int,
    bounced: bool = True,
    notes: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Mark a payment as bounced or unbounced"""
    payment = crud.mark_payment_bounced(
        db=db,
        payment_id=payment_id,
        bounced=bounced,
        notes=notes
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


@router.delete("/{payment_id}", status_code=204)
def delete_payment(
    payment_id: int,
    db: Session = Depends(get_db)
):
    """Delete a payment record"""
    if not crud.delete_payment(db=db, payment_id=payment_id):
        raise HTTPException(status_code=404, detail="Payment not found")


# Deal-specific endpoints
@router.get("/deals/{deal_id}/payments", response_model=List[Payment])
def get_payments_by_deal(
    deal_id: int,
    db: Session = Depends(get_db)
):
    """Get all payments for a specific deal"""
    # TODO: Verify deal_id exists when Deal model is created
    return crud.get_payments_by_deal(db=db, deal_id=deal_id)


@router.get("/deals/{deal_id}/summary", response_model=PaymentSummary)
def get_payment_summary_by_deal(
    deal_id: int,
    db: Session = Depends(get_db)
):
    """Get payment summary statistics for a deal"""
    # TODO: Verify deal_id exists when Deal model is created
    return crud.get_payment_summary_by_deal(db=db, deal_id=deal_id)