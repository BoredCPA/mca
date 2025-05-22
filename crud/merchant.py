from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.merchant import Merchant, MerchantCreate
from app.crud import merchant as merchant_crud
from app.database import SessionLocal, engine, Base

Base.metadata.create_all(bind=engine)

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/merchants/", response_model=Merchant)
def create_merchant(merchant: MerchantCreate, db: Session = Depends(get_db)):
    return merchant_crud.create_merchant(db, merchant)

@router.get("/merchants/", response_model=list[Merchant])
def read_merchants(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return merchant_crud.get_merchants(db, skip=skip, limit=limit)
