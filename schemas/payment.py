# app/schemas/payment.py
from pydantic import BaseModel, Field, validator
from decimal import Decimal
from datetime import datetime
from typing import Optional, List
from enum import Enum


class PaymentType(str, Enum):
    ACH = "ACH"
    WIRE = "Wire"
    CHECK = "Check"
    CREDIT_CARD = "Credit Card"
    DEBIT_CARD = "Debit Card"
    CASH = "Cash"
    OTHER = "Other"


class PaymentBase(BaseModel):
    deal_id: int = Field(..., description="ID of the associated deal")
    date: datetime = Field(..., description="Date of the payment")
    amount: Decimal = Field(..., gt=0, decimal_places=2, description="Payment amount")
    type: PaymentType = Field(..., description="Type of payment")
    bounced: bool = Field(default=False, description="Whether the payment bounced")
    notes: Optional[str] = Field(None, max_length=1000, description="Optional notes about the payment")

    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Payment amount must be greater than 0')
        return v

    @validator('date')
    def validate_date(cls, v):
        if v > datetime.now():
            raise ValueError('Payment date cannot be in the future')
        return v


class PaymentCreate(PaymentBase):
    pass


class PaymentUpdate(BaseModel):
    date: Optional[datetime] = None
    amount: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    type: Optional[PaymentType] = None
    bounced: Optional[bool] = None
    notes: Optional[str] = Field(None, max_length=1000)

    @validator('amount')
    def validate_amount(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Payment amount must be greater than 0')
        return v

    @validator('date')
    def validate_date(cls, v):
        if v is not None and v > datetime.now():
            raise ValueError('Payment date cannot be in the future')
        return v


class Payment(PaymentBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        orm_mode = True


class PaymentSummary(BaseModel):
    """Summary statistics for payments"""
    total_payments: int
    total_amount: Decimal
    total_bounced: int
    bounced_amount: Decimal
    last_payment_date: Optional[datetime]
    average_payment: Optional[Decimal]


class PaymentFilter(BaseModel):
    """Filters for searching payments"""
    deal_id: Optional[int] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    type: Optional[PaymentType] = None
    bounced: Optional[bool] = None
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None