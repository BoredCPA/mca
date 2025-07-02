# app/crud/payment.py
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from app.models.payment import Payment as PaymentModel
from app.schemas.payment import PaymentCreate, PaymentUpdate, PaymentFilter, PaymentSummary
from typing import List, Optional
from datetime import datetime, timedelta
from decimal import Decimal


def create_payment(db: Session, payment: PaymentCreate) -> PaymentModel:
    """Create a new payment record"""
    db_payment = PaymentModel(**payment.dict())
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    return db_payment


def get_payment(db: Session, payment_id: int) -> Optional[PaymentModel]:
    """Get a specific payment by ID"""
    return db.query(PaymentModel).filter(PaymentModel.id == payment_id).first()


def get_payments(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[PaymentFilter] = None
) -> List[PaymentModel]:
    """Get payments with optional filtering"""
    query = db.query(PaymentModel)

    if filters:
        if filters.deal_id:
            query = query.filter(PaymentModel.deal_id == filters.deal_id)
        if filters.date_from:
            query = query.filter(PaymentModel.date >= filters.date_from)
        if filters.date_to:
            query = query.filter(PaymentModel.date <= filters.date_to)
        if filters.type:
            query = query.filter(PaymentModel.type == filters.type)
        if filters.bounced is not None:
            query = query.filter(PaymentModel.bounced == filters.bounced)
        if filters.min_amount:
            query = query.filter(PaymentModel.amount >= filters.min_amount)
        if filters.max_amount:
            query = query.filter(PaymentModel.amount <= filters.max_amount)

    return query.order_by(PaymentModel.date.desc()).offset(skip).limit(limit).all()


def get_payments_by_deal(db: Session, deal_id: int) -> List[PaymentModel]:
    """Get all payments for a specific deal"""
    return db.query(PaymentModel).filter(
        PaymentModel.deal_id == deal_id
    ).order_by(PaymentModel.date.desc()).all()


def get_payment_summary_by_deal(db: Session, deal_id: int) -> PaymentSummary:
    """Get payment summary statistics for a deal"""
    payments = db.query(PaymentModel).filter(PaymentModel.deal_id == deal_id).all()

    if not payments:
        return PaymentSummary(
            total_payments=0,
            total_amount=Decimal('0'),
            total_bounced=0,
            bounced_amount=Decimal('0'),
            last_payment_date=None,
            average_payment=None
        )

    total_amount = sum(p.amount for p in payments)
    bounced_payments = [p for p in payments if p.bounced]
    bounced_amount = sum(p.amount for p in bounced_payments)

    return PaymentSummary(
        total_payments=len(payments),
        total_amount=total_amount,
        total_bounced=len(bounced_payments),
        bounced_amount=bounced_amount,
        last_payment_date=max(p.date for p in payments),
        average_payment=total_amount / len(payments) if payments else None
    )


def get_recent_payments(db: Session, days: int = 7, limit: int = 50) -> List[PaymentModel]:
    """Get recent payments within specified days"""
    cutoff_date = datetime.now() - timedelta(days=days)
    return db.query(PaymentModel).filter(
        PaymentModel.date >= cutoff_date
    ).order_by(PaymentModel.date.desc()).limit(limit).all()


def get_bounced_payments(db: Session, deal_id: Optional[int] = None) -> List[PaymentModel]:
    """Get all bounced payments, optionally filtered by deal"""
    query = db.query(PaymentModel).filter(PaymentModel.bounced == True)
    if deal_id:
        query = query.filter(PaymentModel.deal_id == deal_id)
    return query.order_by(PaymentModel.date.desc()).all()


def update_payment(db: Session, payment_id: int, payment_update: PaymentUpdate) -> Optional[PaymentModel]:
    """Update a payment record"""
    db_payment = db.query(PaymentModel).filter(PaymentModel.id == payment_id).first()

    if db_payment:
        update_data = payment_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_payment, field, value)

        db.commit()
        db.refresh(db_payment)

    return db_payment


def mark_payment_bounced(db: Session, payment_id: int, bounced: bool = True, notes: Optional[str] = None) -> Optional[
    PaymentModel]:
    """Mark a payment as bounced or unbounced"""
    db_payment = db.query(PaymentModel).filter(PaymentModel.id == payment_id).first()

    if db_payment:
        db_payment.bounced = bounced
        if notes:
            if db_payment.notes:
                db_payment.notes = f"{db_payment.notes}\n{notes}"
            else:
                db_payment.notes = notes

        db.commit()
        db.refresh(db_payment)

    return db_payment


def delete_payment(db: Session, payment_id: int) -> bool:
    """Delete a payment record"""
    db_payment = db.query(PaymentModel).filter(PaymentModel.id == payment_id).first()

    if db_payment:
        db.delete(db_payment)
        db.commit()
        return True

    return False


def get_payment_stats_by_type(db: Session, deal_id: Optional[int] = None):
    """Get payment statistics grouped by payment type"""
    query = db.query(
        PaymentModel.type,
        func.count(PaymentModel.id).label('count'),
        func.sum(PaymentModel.amount).label('total_amount'),
        func.avg(PaymentModel.amount).label('avg_amount')
    )

    if deal_id:
        query = query.filter(PaymentModel.deal_id == deal_id)

    return query.group_by(PaymentModel.type).all()