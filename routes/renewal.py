# app/routes/renewal.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from app.database import get_db
from app.schemas.renewal import (
    RenewalInfo, RenewalInfoCreate, RenewalInfoUpdate,
    DealRenewalJunction, DealRenewalRelationship,
    CreateRenewalDeal, RenewalSummary, RenewalChain
)
from app.schemas.deal import Deal
from app.crud import renewal as crud
from app.crud import deal as deal_crud
from app.crud import merchant as merchant_crud
from app.crud import offer as offer_crud

router = APIRouter(
    prefix="/api/v1/renewals",
    tags=["renewals"]
)


# Renewal Deal Creation
@router.post("/deals", response_model=Deal, status_code=201)
def create_renewal_deal(
        renewal_data: CreateRenewalDeal,
        db: Session = Depends(get_db)
):
    """Create a new renewal deal that pays off one or more old deals"""
    # Verify merchant exists
    merchant = merchant_crud.get_merchant(db, renewal_data.merchant_id)
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    # Verify offer exists and belongs to merchant
    offer = offer_crud.get_offer(db, renewal_data.offer_id)
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    if offer.merchant_id != renewal_data.merchant_id:
        raise HTTPException(status_code=400, detail="Offer does not belong to merchant")
    if offer.status != "selected":
        raise HTTPException(status_code=400, detail="Offer must be in 'selected' status")

    # Verify all old deals exist and belong to the merchant
    for old_deal_info in renewal_data.old_deals:
        old_deal = deal_crud.get_deal(db, old_deal_info.old_deal_id)
        if not old_deal:
            raise HTTPException(
                status_code=404,
                detail=f"Old deal {old_deal_info.old_deal_id} not found"
            )
        if old_deal.merchant_id != renewal_data.merchant_id:
            raise HTTPException(
                status_code=400,
                detail=f"Old deal {old_deal_info.old_deal_id} does not belong to merchant"
            )
        if old_deal.status == "renewed":
            raise HTTPException(
                status_code=400,
                detail=f"Deal {old_deal_info.old_deal_id} has already been renewed"
            )

    try:
        return crud.create_renewal_deal(db=db, renewal_data=renewal_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Renewal Info Management
@router.get("/info/{renewal_info_id}", response_model=RenewalInfo)
def get_renewal_info(
        renewal_info_id: int,
        db: Session = Depends(get_db)
):
    """Get a specific renewal info record"""
    renewal_info = db.query(crud.RenewalInfo).filter(
        crud.RenewalInfo.id == renewal_info_id
    ).first()
    if not renewal_info:
        raise HTTPException(status_code=404, detail="Renewal info not found")
    return renewal_info


@router.put("/info/{renewal_info_id}", response_model=RenewalInfo)
def update_renewal_info(
        renewal_info_id: int,
        update_data: RenewalInfoUpdate,
        db: Session = Depends(get_db)
):
    """Update a renewal info record"""
    renewal_info = crud.update_renewal_info(db=db, renewal_info_id=renewal_info_id, update_data=update_data)
    if not renewal_info:
        raise HTTPException(status_code=404, detail="Renewal info not found")
    return renewal_info


# Deal Renewal Information
@router.get("/deals/{deal_id}/renewal-info", response_model=List[RenewalInfo])
def get_renewal_info_by_deal(
        deal_id: int,
        db: Session = Depends(get_db)
):
    """Get all renewal info records for a renewal deal"""
    deal = deal_crud.get_deal(db, deal_id)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    if not deal.is_renewal:
        raise HTTPException(status_code=400, detail="Deal is not a renewal")

    return crud.get_renewal_info_by_deal(db=db, deal_id=deal_id)


@router.get("/deals/{deal_id}/old-deals")
def get_old_deals_for_renewal(
        deal_id: int,
        db: Session = Depends(get_db)
):
    """Get all old deals that were renewed by this renewal deal"""
    deal = deal_crud.get_deal(db, deal_id)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    if not deal.is_renewal:
        raise HTTPException(status_code=400, detail="Deal is not a renewal")

    return crud.get_deals_renewed_by(db=db, renewal_deal_id=deal_id)


@router.get("/deals/{deal_id}/summary", response_model=RenewalSummary)
def get_renewal_summary(
        deal_id: int,
        db: Session = Depends(get_db)
):
    """Get renewal summary for a renewal deal"""
    summary = crud.get_renewal_summary(db=db, deal_id=deal_id)
    if not summary:
        raise HTTPException(
            status_code=404,
            detail="Deal not found or is not a renewal"
        )
    return summary


# Renewal Chain Information
@router.get("/deals/{deal_id}/chain", response_model=RenewalChain)
def get_renewal_chain(
        deal_id: int,
        db: Session = Depends(get_db)
):
    """Get the complete renewal chain for any deal"""
    try:
        return crud.get_renewal_chain(db=db, deal_id=deal_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Deal not found")


@router.get("/deals/{deal_id}/renewed-into")
def check_if_renewed(
        deal_id: int,
        db: Session = Depends(get_db)
):
    """Check if a deal was renewed and get the renewal deal info"""
    renewal_info = crud.get_renewal_deal_for(db=db, old_deal_id=deal_id)
    if not renewal_info:
        return {"was_renewed": False, "renewal_deal": None}
    return {"was_renewed": True, "renewal_deal": renewal_info}


# Renewal Management
@router.post("/reverse")
def reverse_renewal(
        old_deal_id: int,
        new_deal_id: int,
        db: Session = Depends(get_db)
):
    """Reverse a renewal relationship (e.g., if funding fails)"""
    success = crud.reverse_renewal(
        db=db,
        old_deal_id=old_deal_id,
        new_deal_id=new_deal_id
    )
    if not success:
        raise HTTPException(
            status_code=404,
            detail="Renewal relationship not found or already reversed"
        )
    return {"message": "Renewal reversed successfully"}


# Merchant Renewal Information
@router.get("/merchants/{merchant_id}/renewal-deals", response_model=List[Deal])
def get_merchant_renewal_deals(
        merchant_id: int,
        db: Session = Depends(get_db)
):
    """Get all renewal deals for a merchant"""
    # Verify merchant exists
    merchant = merchant_crud.get_merchant(db, merchant_id)
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    # Get all deals for merchant and filter renewals
    deals = deal_crud.get_deals_by_merchant(db, merchant_id)
    renewal_deals = [deal for deal in deals if deal.is_renewal]

    return renewal_deals


@router.get("/relationships", response_model=List[DealRenewalRelationship])
def get_renewal_relationships(
        old_deal_id: Optional[int] = None,
        new_deal_id: Optional[int] = None,
        status: Optional[str] = None,
        db: Session = Depends(get_db)
):
    """Get renewal relationships with optional filtering"""
    query = db.query(crud.DealRenewalRelationship)

    if old_deal_id:
        query = query.filter(crud.DealRenewalRelationship.old_deal_id == old_deal_id)
    if new_deal_id:
        query = query.filter(crud.DealRenewalRelationship.new_deal_id == new_deal_id)
    if status:
        query = query.filter(crud.DealRenewalRelationship.status == status)

    return query.all()