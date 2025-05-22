from sqlalchemy.orm import Session
from app.models.merchant import Merchant as MerchantModel
from app.schemas.merchant import MerchantCreate

def create_merchant(db: Session, merchant: MerchantCreate):
    db_merchant = MerchantModel(**merchant.dict())
    db.add(db_merchant)
    db.commit()
    db.refresh(db_merchant)
    return db_merchant

def get_merchants(db: Session, skip: int = 0, limit: int = 100):
    return db.query(MerchantModel).offset(skip).limit(limit).all()
