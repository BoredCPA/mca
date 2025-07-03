# app/routes/deal.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from app.database import get_db
from app.schemas.deal import (
    Deal, DealCreate, DealUpdate, DealFilter, DealSummary
)
from app.crud import deal as crud
from app.crud import merchant as merchant_crud
from app.crud import offer as offer_crud

router = APIRouter(
    prefix="/api/v1/deals",
    tags=["deals"]
)


@router.post("/", response_model=Deal, status_code=201)
def create_deal(
        deal: DealCreate,
        db: Session = Depends(get_db)
):
    """Create a new deal from an accepted offer"""
    # Verify merchant exists
    merchant = merchant_crud.get_merchant(db, deal.merchant_id)
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    # Verify offer exists and belongs to merchant
    offer = offer_crud.get_offer(db, deal.offer_id)
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    if offer.merchant_id != deal.merchant_id:
        raise HTTPException(status_code=400, detail="Offer does not belong to merchant")
    if offer.status != "selected":
        raise HTTPException(status_code=400, detail="Offer must be in 'selected' status")

    try:
        return crud.create_deal(db=db, deal=deal)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[Deal])
def list_deals(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
        merchant_id: Optional[int] = None,
        status: Optional[str] = None,
        funding_date_from: Optional[date] = None,
        funding_date_to: Optional[date] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        in_collections: Optional[bool] = None,
        db: Session = Depends(get_db)
):
    """Get list of deals with optional filtering"""
    filters = DealFilter(
        merchant_id=merchant_id,
        status=status,
        funding_date_from=funding_date_from,
        funding_date_to=funding_date_to,
        min_amount=min_amount,
        max_amount=max_amount,
        in_collections=in_collections
    )
    return crud.get_deals(db=db, skip=skip, limit=limit, filters=filters)


@router.get("/active", response_model=List[Deal])
def get_active_deals(db: Session = Depends(get_db)):
    """Get all active deals"""
    return crud.get_active_deals(db=db)


@router.get("/summary", response_model=DealSummary)
def get_deal_summary(db: Session = Depends(get_db)):
    """Get summary statistics for all deals"""
    return crud.get_deal_summary(db=db)


@router.get("/{deal_id}", response_model=Deal)
def get_deal(
        deal_id: int,
        db: Session = Depends(get_db)
):
    """Get a specific deal by ID"""
    deal = crud.get_deal(db=db, deal_id=deal_id)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    return deal


@router.get("/number/{deal_number}", response_model=Deal)
def get_deal_by_number(
        deal_number: str,
        db: Session = Depends(get_db)
):
    """Get a deal by its deal number"""
    deal = crud.get_deal_by_number(db=db, deal_number=deal_number)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    return deal


@router.put("/{deal_id}", response_model=Deal)
def update_deal(
        deal_id: int,
        deal_update: DealUpdate,
        db: Session = Depends(get_db)
):
    """Update a deal"""
    deal = crud.update_deal(db=db, deal_id=deal_id, deal_update=deal_update)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    return deal


@router.patch("/{deal_id}/balance", response_model=Deal)
def update_deal_balance(
        deal_id: int,
        db: Session = Depends(get_db)
):
    """Update deal balance based on payments"""
    deal = crud.update_deal_balance(db=db, deal_id=deal_id)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    return deal


@router.delete("/{deal_id}", status_code=204)
def delete_deal(
        deal_id: int,
        db: Session = Depends(get_db)
):
    """Delete a deal (soft delete by changing status)"""
    if not crud.delete_deal(db=db, deal_id=deal_id):
        raise HTTPException(status_code=404, detail="Deal not found")


# Merchant-specific endpoints
@router.get("/merchants/{merchant_id}/deals", response_model=List[Deal])
def get_deals_by_merchant(
        merchant_id: int,
        db: Session = Depends(get_db)
):
    """Get all deals for a specific merchant"""
    # Verify merchant exists
    merchant = merchant_crud.get_merchant(db, merchant_id)
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    return crud.get_deals_by_merchant(db=db, merchant_id=merchant_id)