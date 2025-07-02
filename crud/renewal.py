# app/crud/renewal.py
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from app.models.renewal import RenewalInfo, DealRenewalJunction, DealRenewalRelationship
from app.models.deal import Deal as DealModel
from app.models.offer import Offer as OfferModel
from app.schemas.renewal import (
    RenewalInfoCreate, RenewalInfoUpdate,
    DealRenewalJunctionCreate, DealRenewalRelationshipCreate,
    CreateRenewalDeal, RenewalSummary, RenewalChain
)
from app.crud.deal import generate_deal_number, calculate_maturity_date
from typing import List, Optional
from datetime import datetime, date
from decimal import Decimal


def create_renewal_info(db: Session, renewal_info: RenewalInfoCreate) -> RenewalInfo:
    """Create a renewal info record"""
    # Verify old deal exists
    old_deal = db.query(DealModel).filter(DealModel.id == renewal_info.old_deal_id).first()
    if not old_deal:
        raise ValueError(f"Deal {renewal_info.old_deal_id} not found")

    db_renewal_info = RenewalInfo(**renewal_info.dict())
    db.add(db_renewal_info)
    db.commit()
    db.refresh(db_renewal_info)
    return db_renewal_info


def create_renewal_deal(db: Session, renewal_data: CreateRenewalDeal) -> DealModel:
    """Create a complete renewal deal with all relationships"""
    # Get offer details
    offer = db.query(OfferModel).filter(OfferModel.id == renewal_data.offer_id).first()
    if not offer:
        raise ValueError("Offer not found")

    # Calculate total transfer balance
    total_transfer_balance = sum(old_deal.transfer_balance for old_deal in renewal_data.old_deals)

    # Calculate RTR and maturity date
    rtr_amount = offer.advance * offer.factor
    maturity_date = calculate_maturity_date(
        renewal_data.funding_date,
        offer.payment_frequency,
        offer.number_of_periods or 1
    )

    # Calculate net cash to merchant
    net_cash = offer.advance - offer.upfront_fees - total_transfer_balance

    # Create the renewal deal
    db_deal = DealModel(
        merchant_id=renewal_data.merchant_id,
        offer_id=renewal_data.offer_id,
        bank_account_id=renewal_data.bank_account_id,
        deal_number=generate_deal_number(db),

        # Mark as renewal
        is_renewal=True,
        total_transfer_balance=total_transfer_balance,
        net_cash_to_merchant=net_cash,

        # Financial terms from offer
        funded_amount=offer.advance,
        factor_rate=offer.factor,
        rtr_amount=rtr_amount,
        payment_amount=offer.payment_amount,
        payment_frequency=offer.payment_frequency,
        number_of_payments=offer.number_of_periods or 1,

        # Dates
        funding_date=renewal_data.funding_date,
        first_payment_date=renewal_data.first_payment_date,
        maturity_date=maturity_date,

        # Initial balance
        balance_remaining=rtr_amount,
        payments_remaining=offer.number_of_periods or 1,

        # Administrative
        notes=renewal_data.notes,
        created_by=renewal_data.created_by,
        status="active"
    )

    db.add(db_deal)
    db.flush()  # Get the deal ID without committing

    # Create renewal info and relationships for each old deal
    for old_deal_info in renewal_data.old_deals:
        # Create renewal info
        renewal_info = RenewalInfo(
            old_deal_id=old_deal_info.old_deal_id,
            transfer_balance=old_deal_info.transfer_balance,
            payoff_date=old_deal_info.payoff_date,
            notes=old_deal_info.notes
        )
        db.add(renewal_info)
        db.flush()

        # Create junction record
        junction = DealRenewalJunction(
            deal_id=db_deal.id,
            renewal_info_id=renewal_info.id
        )
        db.add(junction)

        # Create relationship record
        relationship = DealRenewalRelationship(
            old_deal_id=old_deal_info.old_deal_id,
            new_deal_id=db_deal.id,
            renewal_info_id=renewal_info.id,
            status="active"
        )
        db.add(relationship)

        # Update old deal status
        old_deal = db.query(DealModel).filter(DealModel.id == old_deal_info.old_deal_id).first()
        if old_deal:
            old_deal.status = "renewed"

    # Update offer status to funded
    offer.status = "funded"
    offer.funded_at = datetime.utcnow()

    db.commit()
    db.refresh(db_deal)
    return db_deal


def get_renewal_info_by_deal(db: Session, deal_id: int) -> List[RenewalInfo]:
    """Get all renewal info records for a renewal deal"""
    return db.query(RenewalInfo).join(
        DealRenewalJunction
    ).filter(
        DealRenewalJunction.deal_id == deal_id
    ).all()


def get_deals_renewed_by(db: Session, renewal_deal_id: int) -> List[dict]:
    """Get all old deals that were renewed by a specific renewal deal"""
    relationships = db.query(DealRenewalRelationship).filter(
        and_(
            DealRenewalRelationship.new_deal_id == renewal_deal_id,
            DealRenewalRelationship.status == "active"
        )
    ).all()

    results = []
    for rel in relationships:
        old_deal = db.query(DealModel).filter(DealModel.id == rel.old_deal_id).first()
        renewal_info = db.query(RenewalInfo).filter(RenewalInfo.id == rel.renewal_info_id).first()

        if old_deal and renewal_info:
            results.append({
                "deal_id": old_deal.id,
                "deal_number": old_deal.deal_number,
                "transfer_balance": float(renewal_info.transfer_balance),
                "payoff_date": renewal_info.payoff_date
            })

    return results


def get_renewal_deal_for(db: Session, old_deal_id: int) -> Optional[dict]:
    """Check if an old deal was renewed and get the renewal deal info"""
    relationship = db.query(DealRenewalRelationship).filter(
        and_(
            DealRenewalRelationship.old_deal_id == old_deal_id,
            DealRenewalRelationship.status == "active"
        )
    ).first()

    if relationship:
        new_deal = db.query(DealModel).filter(DealModel.id == relationship.new_deal_id).first()
        if new_deal:
            return {
                "deal_id": new_deal.id,
                "deal_number": new_deal.deal_number,
                "renewal_date": new_deal.funding_date
            }

    return None


def get_renewal_chain(db: Session, deal_id: int) -> RenewalChain:
    """Get the complete renewal chain for a deal"""
    deal = db.query(DealModel).filter(DealModel.id == deal_id).first()
    if not deal:
        raise ValueError("Deal not found")

    # Check if this deal was renewed
    renewed_into = get_renewal_deal_for(db, deal_id)

    # Check if this deal is a renewal
    renewed_from = []
    if deal.is_renewal:
        renewed_from = get_deals_renewed_by(db, deal_id)

    return RenewalChain(
        deal_id=deal.id,
        deal_number=deal.deal_number,
        was_renewed=renewed_into is not None,
        renewed_into=renewed_into,
        is_renewal=deal.is_renewal,
        renewed_from=renewed_from
    )


def get_renewal_summary(db: Session, deal_id: int) -> Optional[RenewalSummary]:
    """Get renewal summary for a renewal deal"""
    deal = db.query(DealModel).filter(
        and_(
            DealModel.id == deal_id,
            DealModel.is_renewal == True
        )
    ).first()

    if not deal:
        return None

    # Get old deals
    old_deals_info = get_deals_renewed_by(db, deal_id)
    old_deal_ids = [info["deal_id"] for info in old_deals_info]

    return RenewalSummary(
        deal_id=deal.id,
        deal_number=deal.deal_number,
        is_renewal=deal.is_renewal,
        funded_amount=deal.funded_amount,
        total_transfer_balance=deal.total_transfer_balance,
        net_cash_to_merchant=deal.net_cash_to_merchant or 0,
        old_deals_count=len(old_deal_ids),
        old_deal_ids=old_deal_ids,
        created_at=deal.created_at
    )


def update_renewal_info(db: Session, renewal_info_id: int, update_data: RenewalInfoUpdate) -> Optional[RenewalInfo]:
    """Update a renewal info record"""
    db_renewal_info = db.query(RenewalInfo).filter(RenewalInfo.id == renewal_info_id).first()

    if db_renewal_info:
        update_dict = update_data.dict(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(db_renewal_info, field, value)

        # If transfer balance changed, update the deal's total
        if 'transfer_balance' in update_dict:
            # Find the renewal deal
            junction = db.query(DealRenewalJunction).filter(
                DealRenewalJunction.renewal_info_id == renewal_info_id
            ).first()

            if junction:
                # Recalculate total transfer balance
                all_renewal_infos = get_renewal_info_by_deal(db, junction.deal_id)
                total_transfer = sum(info.transfer_balance for info in all_renewal_infos)

                # Update deal
                deal = db.query(DealModel).filter(DealModel.id == junction.deal_id).first()
                if deal:
                    deal.total_transfer_balance = total_transfer
                    deal.net_cash_to_merchant = deal.funded_amount - deal.upfront_fees - total_transfer

        db.commit()
        db.refresh(db_renewal_info)

    return db_renewal_info


def reverse_renewal(db: Session, old_deal_id: int, new_deal_id: int) -> bool:
    """Reverse a renewal relationship (e.g., if funding fails)"""
    relationship = db.query(DealRenewalRelationship).filter(
        and_(
            DealRenewalRelationship.old_deal_id == old_deal_id,
            DealRenewalRelationship.new_deal_id == new_deal_id,
            DealRenewalRelationship.status == "active"
        )
    ).first()

    if relationship:
        relationship.status = "reversed"

        # Reactivate the old deal
        old_deal = db.query(DealModel).filter(DealModel.id == old_deal_id).first()
        if old_deal and old_deal.status == "renewed":
            old_deal.status = "active"

        db.commit()
        return True

    return False