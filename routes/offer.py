# app/routes/offer.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.offer import Offer, OfferCreate, OfferUpdate
from app.crud import offer as offer_crud
from app.database import SessionLocal
from typing import List

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/offers/", response_model=Offer)
def create_offer(offer: OfferCreate, db: Session = Depends(get_db)):
    """Create a new offer for a merchant"""
    return offer_crud.create_offer(db, offer)


@router.get("/offers/", response_model=List[Offer])
def read_offers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all offers with pagination"""
    return offer_crud.get_offers(db, skip=skip, limit=limit)


@router.get("/offers/{offer_id}", response_model=Offer)
def read_offer(offer_id: int, db: Session = Depends(get_db)):
    """Get a specific offer by ID"""
    db_offer = offer_crud.get_offer(db, offer_id=offer_id)
    if db_offer is None:
        raise HTTPException(status_code=404, detail="Offer not found")
    return db_offer


@router.get("/merchants/{merchant_id}/offers/", response_model=List[Offer])
def read_merchant_offers(merchant_id: int, db: Session = Depends(get_db)):
    """Get all offers for a specific merchant"""
    return offer_crud.get_offers_by_merchant(db, merchant_id=merchant_id)


@router.get("/merchants/{merchant_id}/offers/selected", response_model=Offer)
def read_selected_offer(merchant_id: int, db: Session = Depends(get_db)):
    """Get the selected offer for a merchant"""
    db_offer = offer_crud.get_selected_offer_by_merchant(db, merchant_id=merchant_id)
    if db_offer is None:
        raise HTTPException(status_code=404, detail="No selected offer found for this merchant")
    return db_offer


@router.put("/offers/{offer_id}", response_model=Offer)
def update_offer(offer_id: int, offer_update: OfferUpdate, db: Session = Depends(get_db)):
    """Update an existing offer"""
    db_offer = offer_crud.update_offer(db, offer_id=offer_id, offer_update=offer_update)
    if db_offer is None:
        raise HTTPException(status_code=404, detail="Offer not found")
    return db_offer


@router.patch("/offers/{offer_id}/status/{status}")
def update_offer_status(offer_id: int, status: str, db: Session = Depends(get_db)):
    """Update offer status (draft, sent, selected, funded)"""
    valid_statuses = ["draft", "sent", "selected", "funded"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

    offer_update = OfferUpdate(status=status)
    db_offer = offer_crud.update_offer(db, offer_id=offer_id, offer_update=offer_update)
    if db_offer is None:
        raise HTTPException(status_code=404, detail="Offer not found")
    return {"message": f"Offer status updated to {status}", "offer_id": offer_id}


@router.delete("/offers/{offer_id}")
def delete_offer(offer_id: int, db: Session = Depends(get_db)):
    """Delete an offer"""
    db_offer = offer_crud.delete_offer(db, offer_id=offer_id)
    if db_offer is None:
        raise HTTPException(status_code=404, detail="Offer not found")
    return {"message": "Offer deleted successfully"}