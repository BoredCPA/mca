# app/crud/offer.py
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.offer import Offer
from app.schemas.offer import OfferCreate, OfferUpdate
from decimal import Decimal
from datetime import datetime
from fastapi import HTTPException


def calculate_offer_fields(offer_data: dict) -> dict:
    """Calculate RTR, net funds, and payment fields based on input"""
    # Calculate RTR
    rtr = offer_data['advance'] * offer_data['factor']
    offer_data['rtr'] = rtr

    # Calculate net funds
    upfront_fees = offer_data.get('upfront_fees', 0) or 0
    offer_data['net_funds'] = offer_data['advance'] - upfront_fees

    # Handle bidirectional payment calculation
    payment_amount = offer_data.get('payment_amount')
    number_of_periods = offer_data.get('number_of_periods')

    if payment_amount is not None and payment_amount > 0:
        # Calculate number of periods from payment amount
        offer_data['number_of_periods'] = int(rtr / payment_amount)
        offer_data['payment_amount'] = payment_amount
    elif number_of_periods is not None and number_of_periods > 0:
        # Calculate payment amount from number of periods
        offer_data['payment_amount'] = rtr / number_of_periods
        offer_data['number_of_periods'] = number_of_periods
    else:
        # Default calculation using specified percentage
        specified_percentage = offer_data.get('specified_percentage', 0)
        if specified_percentage > 0:
            offer_data['payment_amount'] = (rtr * specified_percentage) / 100
            if offer_data['payment_amount'] > 0:
                offer_data['number_of_periods'] = int(rtr / offer_data['payment_amount'])

    return offer_data


def create_offer(db: Session, offer: OfferCreate):
    """Create new offer with calculations"""
    offer_data = offer.model_dump()

    # Handle deal_id - set to None if empty string or generic value
    if offer_data.get('deal_id') in [None, '', 'string']:
        offer_data['deal_id'] = None

    offer_data = calculate_offer_fields(offer_data)

    try:
        db_offer = Offer(**offer_data)
        db.add(db_offer)
        db.commit()
        db.refresh(db_offer)
        return db_offer
    except IntegrityError as e:
        db.rollback()
        if "UNIQUE constraint failed: offers.deal_id" in str(e):
            raise HTTPException(status_code=409, detail="Deal ID already exists")
        raise HTTPException(status_code=400, detail="Database constraint violation")


def get_offer(db: Session, offer_id: int):
    """Get offer by ID"""
    return db.query(Offer).filter(Offer.id == offer_id, Offer.is_deleted == False).first()


def get_offers(db: Session, skip: int = 0, limit: int = 100):
    """Get all offers with pagination"""
    return db.query(Offer).filter(Offer.is_deleted == False).offset(skip).limit(limit).all()


def get_offers_by_merchant(db: Session, merchant_id: int):
    """Get all offers for a merchant"""
    return db.query(Offer).filter(
        Offer.merchant_id == merchant_id,
        Offer.is_deleted == False
    ).all()


def get_selected_offer_by_merchant(db: Session, merchant_id: int):
    """Get selected offer for a merchant"""
    return db.query(Offer).filter(
        Offer.merchant_id == merchant_id,
        Offer.status == "selected",
        Offer.is_deleted == False
    ).first()


def update_offer(db: Session, offer_id: int, offer_update: OfferUpdate):
    """Update existing offer with recalculations"""
    db_offer = get_offer(db, offer_id)
    if not db_offer:
        return None

    # Get current values and apply updates
    update_data = offer_update.model_dump(exclude_unset=True)

    # Apply updates to current offer data
    current_data = {
        'advance': db_offer.advance,
        'factor': db_offer.factor,
        'upfront_fees': db_offer.upfront_fees,
        'specified_percentage': db_offer.specified_percentage,
        'payment_amount': db_offer.payment_amount,
        'number_of_periods': db_offer.number_of_periods
    }
    current_data.update(update_data)

    # Recalculate fields
    calculated_data = calculate_offer_fields(current_data)

    # Update the database record
    for key, value in calculated_data.items():
        if hasattr(db_offer, key):
            setattr(db_offer, key, value)

    # Update timestamp
    db_offer.updated_at = datetime.utcnow()

    # Handle status-specific timestamps
    if 'status' in update_data:
        if update_data['status'] == 'sent':
            db_offer.sent_at = datetime.utcnow()
        elif update_data['status'] == 'selected':
            db_offer.selected_at = datetime.utcnow()
        elif update_data['status'] == 'funded':
            db_offer.funded_at = datetime.utcnow()

    db.commit()
    db.refresh(db_offer)
    return db_offer


def delete_offer(db: Session, offer_id: int):
    """Soft delete an offer"""
    db_offer = get_offer(db, offer_id)
    if not db_offer:
        return None

    db_offer.is_deleted = True
    db_offer.deleted_at = datetime.utcnow()
    db.commit()
    return db_offer