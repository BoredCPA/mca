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
    payment_frequency = offer_data.get('payment_frequency', 'daily')

    # Get either number_of_periods or payment_amount from user
    number_of_periods = offer_data.get('number_of_periods', None)
    payment_amount = offer_data.get('payment_amount', None)

    # Calculate RTR (Return to Remit)
    rtr = advance * factor

    # Calculate net funds
    net_funds = advance - upfront_fees

    # Calculate payment amount based on what user provided
    if number_of_periods and number_of_periods > 0:
        # User provided number of periods (e.g., 22 weeks)
        payment_amount = rtr / number_of_periods
    elif payment_amount:
        # User provided fixed payment amount (e.g., $500 daily)
        # Payment amount is already set by user
        pass
    else:
        # Neither provided - set to 0 or raise error
        payment_amount = 0

    # Calculate total number of payments if payment_amount is provided
    if payment_amount and payment_amount > 0 and not number_of_periods:
        number_of_periods = rtr / payment_amount

    # Calculate APR (simplified calculation)
    # This is a basic calculation - you may want to refine this
    total_cost = rtr - advance
    if advance > 0 and number_of_periods and number_of_periods > 0:
        # Calculate based on actual term length
        if payment_frequency == 'daily':
            days = number_of_periods
            apr = (total_cost / advance) * (365 / days) * 100
        elif payment_frequency == 'weekly':
            weeks = number_of_periods
            apr = (total_cost / advance) * (52 / weeks) * 100
        elif payment_frequency == 'bi-weekly':
            biweeks = number_of_periods
            apr = (total_cost / advance) * (26 / biweeks) * 100
        elif payment_frequency == 'monthly':
            months = number_of_periods
            apr = (total_cost / advance) * (12 / months) * 100
        else:
            apr = 0
    else:
        apr = 0

    offer_data.update({
        'rtr': rtr,
        'net_funds': net_funds,
        'payment_amount': payment_amount,
        'number_of_periods': number_of_periods,
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


def get_offers(db: Session, skip: int = 0, limit: int = 100, include_deleted: bool = False):
    query = db.query(OfferModel)

    if not include_deleted:
        query = query.filter(OfferModel.is_deleted == False)

    return query.offset(skip).limit(limit).all()


def get_offer(db: Session, offer_id: int, include_deleted: bool = False):
    query = db.query(OfferModel).filter(OfferModel.id == offer_id)

    if not include_deleted:
        query = query.filter(OfferModel.is_deleted == False)

    return query.first()


def get_offers_by_merchant(db: Session, merchant_id: int, include_deleted: bool = False):
    query = db.query(OfferModel).filter(OfferModel.merchant_id == merchant_id)

    if not include_deleted:
        query = query.filter(OfferModel.is_deleted == False)

    return query.order_by(OfferModel.created_at.desc()).all()


def get_selected_offer_by_merchant(db: Session, merchant_id: int):
    return db.query(OfferModel).filter(
        and_(
            OfferModel.merchant_id == merchant_id,
            OfferModel.status == "selected",
            OfferModel.is_deleted == False  # Add this check
        )
    ).first()


def update_offer(db: Session, offer_id: int, offer_update: OfferUpdate):
    db_offer = db.query(OfferModel).filter(OfferModel.id == offer_id).first()
    if db_offer:
        update_data = offer_update.dict(exclude_unset=True)

        # Recalculate fields if financial data changed
        if any(field in update_data for field in
               ['advance', 'factor', 'upfront_fees', 'number_of_periods', 'payment_amount', 'payment_frequency']):
            # Merge current data with updates
            current_data = {
                'advance': db_offer.advance,
                'factor': db_offer.factor,
                'upfront_fees': db_offer.upfront_fees,
                'number_of_periods': getattr(db_offer, 'number_of_periods', None),
                'payment_amount': db_offer.payment_amount,
                'payment_frequency': db_offer.payment_frequency,
            }
            current_data.update(update_data)
            update_data = calculate_offer_fields(current_data)

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


def delete_offer(db: Session, offer_id: int, deleted_by: str = None) -> Optional[OfferModel]:
    db_offer = db.query(OfferModel).filter(
        OfferModel.id == offer_id,
        OfferModel.is_deleted == False  # Don't delete if already deleted
    ).first()

    if db_offer:
        # Check if offer is in a state that shouldn't be deleted
        if db_offer.status in ["funded", "selected"]:
            raise ValueError(
                f"Cannot delete offer with status '{db_offer.status}'. "
                "Only draft, sent, or withdrawn offers can be deleted."
            )

        # Soft delete
        db_offer.is_deleted = True
        db_offer.deleted_at = datetime.utcnow()
        db_offer.deleted_by = deleted_by

        # Optionally update status to show it was deleted
        # db_offer.status = "withdrawn"  # Optional

        db.commit()

    return db_offer


def restore_offer(db: Session, offer_id: int) -> Optional[OfferModel]:
    """Restore a soft-deleted offer"""
    db_offer = db.query(OfferModel).filter(
        OfferModel.id == offer_id,
        OfferModel.is_deleted == True
    ).first()

    if db_offer:
        db_offer.is_deleted = False
        db_offer.deleted_at = None
        db_offer.deleted_by = None
        db.commit()

    return db_offer