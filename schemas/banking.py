# app/schemas/banking.py
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


class BankAccountBase(BaseModel):
    account_name: str = Field(..., min_length=1, max_length=100)
    account_number: str = Field(..., min_length=4, max_length=4)  # Last 4 digits only
    routing_number: str = Field(..., pattern="^[0-9]{9}$")  # Changed from regex to pattern
    bank_name: str = Field(..., min_length=1, max_length=100)
    account_type: str = Field(..., pattern="^(checking|savings)$")  # Changed from regex to pattern
    is_active: bool = True
    is_primary: bool = False

    @field_validator('account_number')
    @classmethod
    def validate_account_number(cls, v):
        if not v.isdigit():
            raise ValueError('Account number must contain only digits')
        return v


class BankAccountCreate(BankAccountBase):
    pass


class BankAccountUpdate(BaseModel):
    account_name: Optional[str] = Field(None, min_length=1, max_length=100)
    bank_name: Optional[str] = Field(None, min_length=1, max_length=100)
    account_type: Optional[str] = Field(None, pattern="^(checking|savings)$")  # Changed from regex to pattern
    is_active: Optional[bool] = None
    is_primary: Optional[bool] = None


class BankAccountInDB(BankAccountBase):
    id: int
    merchant_id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class BankAccountResponse(BankAccountInDB):
    merchant_name: Optional[str] = None