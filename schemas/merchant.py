from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date, datetime

class MerchantBase(BaseModel):
    company_name: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    fein: Optional[str] = None
    phone: Optional[str] = None
    entity_type: Optional[str] = None
    submitted_date: Optional[date] = None
    email: Optional[EmailStr] = None
    contact_person: Optional[str] = None
    status: Optional[str] = "lead"
    notes: Optional[str] = None

class MerchantCreate(MerchantBase):
    pass

class Merchant(MerchantBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
