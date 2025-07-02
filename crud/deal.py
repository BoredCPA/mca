# app/crud/deal.py
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from app.models.deal import Deal as DealModel
from app.models.offer import Offer as OfferModel
from app.models.payment import Payment as PaymentModel
from app.schemas.deal import DealCreate, DealUpdate, DealFilter, DealSummary
from typing import List, Optional
from datetime import datetime, date, timedelta
from decimal import Decimal


def generate_deal_number(db: Session) -> str:
    """Generate a unique deal number"""
    current_year = datetime.now().year

    # Get the last deal number for the current year
    last_deal = db.query(DealModel).filter(
        DealModel.deal_number.like(f"MCA-{current_year}-%")
    ).order_by(DealModel.id.desc()).first()

    if last_deal:
        # Extract the sequence number and increment
        last_sequence = int(last_deal.deal_number.split('-')[-1])
        new_sequence = last_sequence + 1
    else:
        new_sequence = 1

    return f"MCA-{current_year}-{new_sequence:04d}"


def calculate_maturity_date(funding_date: date, payment_frequency: str, number_of_payments: int) -> date:
    """Calculate the maturity date based on payment schedule"""
    if payment_frequency == "daily":
        # Assuming 5 business days per week
        weeks = number_of_payments / 5
        return funding_date + timedelta(weeks=weeks)
    elif payment_frequency == "weekly":
        return funding_date + timedelta(weeks=number_of_payments)
    elif payment_frequency == "bi-weekly":
        return funding_date + timedelta(weeks=number_of_payments * 2)
    elif payment_frequency == "monthly":
        return funding_date + timedelta(days=number_of_payments * 30)
    else:
        return funding_date + timedelta(days=number_of_payments)


def create_deal(db: Session, deal: DealCreate) -> DealModel:
    """Create a new deal from an accepted offer"""
    # Get the offer details
    offer = db.query(OfferModel).filter(OfferModel.id == deal.offer_id).first()
    if not offer:
        raise ValueError("Offer not found")

    # Calculate RTR and maturity date
    rtr_amount = offer.advance * offer.factor
    maturity_date = calculate_maturity_date(
        deal.funding_date,
        offer.payment_frequency,
        offer.number_of_periods or 1
    )

    # Calculate net cash to merchant (for non-renewal deals)
    net_cash = offer.advance - offer.upfront_fees

    # Create the deal
    db_deal = DealModel(
        merchant_id=deal.merchant_id,
        offer_id=deal.offer_id,
        bank_account_id=deal.bank_account_id,
        deal_number=generate_deal_number(db),

        # Financial terms from offer
        funded_amount=offer.advance,
        factor_rate=offer.factor,
        rtr_amount=rtr_amount,
        payment_amount=offer.payment_amount,
        payment_frequency=offer.payment_frequency,
        number_of_payments=offer.number_of_periods or 1,

        # Dates
        funding_date=deal.funding_date,
        first_payment_date=deal.first_payment_date,
        maturity_date=maturity_date,

        # Initial balance
        balance_remaining=rtr_amount,
        payments_remaining=offer.number_of_periods or 1,

        # For non-renewal deals
        is_renewal=False,
        total_transfer_balance=Decimal('0'),
        net_cash_to_merchant=net_cash,

        # Administrative
        notes=deal.notes,
        created_by=deal.created_by,
        status="active"
    )

    db.add(db_deal)

    # Update offer status to funded
    offer.status = "funded"
    offer.funded_at = datetime.utcnow()

    db.commit()
    db.refresh(db_deal)
    return db_deal


def get_deal(db: Session, deal_id: int) -> Optional[DealModel]:
    """Get a specific deal by ID"""
    return db.query(DealModel).filter(DealModel.id == deal_id).first()


def get_deal_by_number(db: Session, deal_number: str) -> Optional[DealModel]:
    """Get a deal by its deal number"""
    return db.query(DealModel).filter(DealModel.deal_number == deal_number).first()


def get_deals(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[DealFilter] = None
) -> List[DealModel]:
    """Get deals with optional filtering"""
    query = db.query(DealModel)

    if filters:
        if filters.merchant_id:
            query = query.filter(DealModel.merchant_id == filters.merchant_id)
        if filters.status:
            query = query.filter(DealModel.status == filters.status)
        if filters.funding_date_from:
            query = query.filter(DealModel.funding_date >= filters.funding_date_from)
        if filters.funding_date_to:
            query = query.filter(DealModel.funding_date <= filters.funding_date_to)
        if filters.min_amount:
            query = query.filter(DealModel.funded_amount >= filters.min_amount)
        if filters.max_amount:
            query = query.filter(DealModel.funded_amount <= filters.max_amount)
        if filters.in_collections is not None:
            query = query.filter(DealModel.in_collections == filters.in_collections)

    return query.order_by(DealModel.funding_date.desc()).offset(skip).limit(limit).all()


def get_active_deals(db: Session) -> List[DealModel]:
    """Get all active deals"""
    return db.query(DealModel).filter(DealModel.status == "active").all()


def get_deals_by_merchant(db: Session, merchant_id: int) -> List[DealModel]:
    """Get all deals for a specific merchant"""
    return db.query(DealModel).filter(
        DealModel.merchant_id == merchant_id
    ).order_by(DealModel.funding_date.desc()).all()


def update_deal(db: Session, deal_id: int, deal_update: DealUpdate) -> Optional[DealModel]:
    """Update a deal"""
    db_deal = db.query(DealModel).filter(DealModel.id == deal_id).first()

    if db_deal:
        update_data = deal_update.dict(exclude_unset=True)

        # Handle status changes
        if 'status' in update_data:
            if update_data['status'] == 'completed' and not db_deal.actual_completion_date:
                update_data['actual_completion_date'] = date.today()

        for field, value in update_data.items():
            setattr(db_deal, field, value)

        db.commit()
        db.refresh(db_deal)

    return db_deal


def update_deal_balance(db: Session, deal_id: int) -> Optional[DealModel]:
    """Update deal balance based on payments"""
    db_deal = db.query(DealModel).filter(DealModel.id == deal_id).first()

    if db_deal:
        # Calculate total paid from payments
        payments = db.query(PaymentModel).filter(
            and_(
                PaymentModel.deal_id == deal_id,
                PaymentModel.bounced == False
            )
        ).all()

        total_paid = sum(p.amount for p in payments)
        db_deal.total_paid = total_paid
        db_deal.balance_remaining = db_deal.rtr_amount - total_paid  # RTR minus total collected

        # Update payment count
        db_deal.payments_remaining = db_deal.number_of_payments - len(payments)

        # Update last payment date
        if payments:
            db_deal.last_payment_date = max(p.date for p in payments).date()

        # Check if deal is completed
        if db_deal.balance_remaining <= 0:
            db_deal.status = "completed"
            db_deal.actual_completion_date = date.today()

        db.commit()
        db.refresh(db_deal)

    return db_deal


def get_deal_summary(db: Session) -> DealSummary:
    """Get summary statistics for all deals"""
    deals = db.query(DealModel).all()

    if not deals:
        return DealSummary(
            total_deals=0,
            active_deals=0,
            completed_deals=0,
            defaulted_deals=0,
            total_funded=Decimal('0'),
            total_collected=Decimal('0'),
            total_outstanding=Decimal('0'),
            average_factor_rate=Decimal('0'),
            average_deal_size=Decimal('0'),
            completion_rate=0.0
        )

    active_deals = [d for d in deals if d.status == "active"]
    completed_deals = [d for d in deals if d.status == "completed"]
    defaulted_deals = [d for d in deals if d.status == "defaulted"]

    total_funded = sum(d.funded_amount for d in deals)
    total_collected = sum(d.total_paid for d in deals)
    total_outstanding = sum(d.balance_remaining for d in active_deals)

    average_factor_rate = sum(d.factor_rate for d in deals) / len(deals)
    average_deal_size = total_funded / len(deals)

    completion_rate = (len(completed_deals) / len(deals) * 100) if deals else 0

    return DealSummary(
        total_deals=len(deals),
        active_deals=len(active_deals),
        completed_deals=len(completed_deals),
        defaulted_deals=len(defaulted_deals),
        total_funded=total_funded,
        total_collected=total_collected,
        total_outstanding=total_outstanding,
        average_factor_rate=average_factor_rate,
        average_deal_size=average_deal_size,
        completion_rate=completion_rate
    )


def delete_deal(db: Session, deal_id: int) -> bool:
    """Delete a deal (soft delete by changing status)"""
    db_deal = db.query(DealModel).filter(DealModel.id == deal_id).first()

    if db_deal:
        db_deal.status = "cancelled"
        db.commit()
        return True

    return False