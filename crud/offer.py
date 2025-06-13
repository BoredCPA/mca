# app/crud/offer.py
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.offer import Offer as OfferModel
from app.schemas.offer import OfferCreate, OfferUpdate
from typing import List, Optional
from decimal import Decimal
from datetime import datetime


def calculate_offer_fields(offer_data: dict) -> dict:
    """Calculate RTR, net funds, payment amount, and APR"""
    advance = offer_data.get('advance', 0)
    factor = offer_data.get('factor', 0)
    upfront_fees = offer_data.get('upfront_fees', 0)
    specified_percentage = offer_data.get('specified_percentage', 0)
    payment_frequency = offer_data.get('payment_frequency', 'daily')

    # Calculate RTR (Return to Remit)
    rtr = advance * factor

    # Calculate net funds
    net_funds = advance - upfront_fees

    # Calculate daily payment amount
    payment_amount = (rtr * specified_percentage) / 100

    # Calculate APR (simplified calculation)
    # This is a basic calculation - you may want to refine this
    total_cost = rtr - advance
    if advance > 0:
        cost_percentage = (total_cost / advance) * 100
        # Annualize based on payment frequency
        if payment_frequency == 'daily':
            apr = cost_percentage * 365 / 250  # Assuming 250 business days
        elif payment_frequency == 'weekly':
            apr = cost_percentage * 52
        elif payment_frequency == 'bi-weekly':
            apr = cost_percentage * 26
        elif payment_frequency == 'monthly':
            apr = cost_percentage * 12
        else:
            apr = cost_percentage
    else:
        apr = 0

    offer_data.update({
        'rtr': rtr,
        'net_funds': net_funds,
        'payment_amount': payment_amount,
        'apr': apr
    })

    return offer_data


def create_offer(db: Session, offer: OfferCreate):
    # Convert to dict and calculate fields
    offer_data = offer.dict()
    offer_data = calculate_offer_fields(offer_data)

    db_offer = OfferModel(**offer_data)
    db.add(db_offer)
    db.commit()
    db.refresh(db_offer)
    return db_offer


def get_offers(db: Session, skip: int = 0, limit: int = 100):
    return db.query(OfferModel).offset(skip).limit(limit).all()


def get_offer(db: Session, offer_id: int):
    return db.query(OfferModel).filter(OfferModel.id == offer_id).first()


def get_offers_by_merchant(db: Session, merchant_id: int):
    return db.query(OfferModel).filter(OfferModel.merchant_id == merchant_id).order_by(
        OfferModel.created_at.desc()).all()


def get_selected_offer_by_merchant(db: Session, merchant_id: int):
    return db.query(OfferModel).filter(
        and_(OfferModel.merchant_id == merchant_id, OfferModel.status == "selected")
    ).first()


def update_offer(db: Session, offer_id: int, offer_update: OfferUpdate):
    db_offer = db.query(OfferModel).filter(OfferModel.id == offer_id).first()
    if db_offer:
        update_data = offer_update.dict(exclude_unset=True)

        # Recalculate fields if financial data changed
        if any(field in update_data for field in
               ['advance', 'factor', 'upfront_fees', 'specified_percentage', 'payment_frequency']):
            # Merge current data with updates
            current_data = {
                'advance': db_offer.advance,
                'factor': db_offer.factor,
                'upfront_fees': db_offer.upfront_fees,
                'specified_percentage': db_offer.specified_percentage,
                'payment_frequency': db_offer.payment_frequency,
            }
            current_data.update(update_data)
            update_data = calculate_offer_fields(update_data)

        # Handle status change timestamps
        if 'status' in update_data:
            if update_data['status'] == 'sent' and not db_offer.sent_at:
                update_data['sent_at'] = datetime.utcnow()
            elif update_data['status'] == 'selected' and not db_offer.selected_at:
                update_data['selected_at'] = datetime.utcnow()
            elif update_data['status'] == 'funded' and not db_offer.funded_at:
                update_data['funded_at'] = datetime.utcnow()

        for field, value in update_data.items():
            setattr(db_offer, field, value)

        db.commit()
        db.refresh(db_offer)
    return db_offer


def delete_offer(db: Session, offer_id: int):
    db_offer = db.query(OfferModel).filter(OfferModel.id == offer_id).first()
    if db_offer:
        db.delete(db_offer)
        db.commit()
    return db_offer