# app/schemas/deal.py
from pydantic import BaseModel, Field, field_validator
from decimal import Decimal
from datetime import datetime, date
from typing import Optional, List
from enum import Enum

from app.schemas.merchant import Merchant
from app.schemas.offer import Offer
from app.schemas.banking import BankAccountBase
from app.schemas.payment import Payment


class DealStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    DEFAULTED = "defaulted"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


class PaymentFrequency(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    BI_WEEKLY = "bi-weekly"
    MONTHLY = "monthly"


class DealBase(BaseModel):
    merchant_id: int = Field(..., description="ID of the merchant")
    offer_id: int = Field(..., description="ID of the accepted offer")
    bank_account_id: Optional[int] = Field(None, description="ID of the bank account for funding")

    funded_amount: Decimal = Field(..., gt=0, decimal_places=2)
    factor_rate: Decimal = Field(..., gt=1, le=2, decimal_places=4)
    payment_amount: Decimal = Field(..., gt=0, decimal_places=2)
    payment_frequency: PaymentFrequency
    number_of_payments: int = Field(..., gt=0)

    funding_date: date
    first_payment_date: date

    notes: Optional[str] = Field(None, max_length=2000)
    created_by: Optional[str] = Field(None, max_length=100)

    @field_validator('first_payment_date')
    @classmethod
    def validate_first_payment_date(cls, v, values):
        if 'funding_date' in values and v < values['funding_date']:
            raise ValueError('First payment date cannot be before funding date')
        return v


class DealCreate(BaseModel):
    merchant_id: int
    offer_id: int
    bank_account_id: Optional[int] = None
    funding_date: date
    first_payment_date: date
    notes: Optional[str] = None
    created_by: Optional[str] = None


class DealUpdate(BaseModel):
    bank_account_id: Optional[int] = None
    status: Optional[DealStatus] = None
    payment_amount: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    in_collections: Optional[bool] = None
    collections_notes: Optional[str] = None
    notes: Optional[str] = Field(None, max_length=2000)


class Deal(DealBase):
    id: int
    deal_number: str

    rtr_amount: Decimal
    maturity_date: date

    total_paid: Decimal
    balance_remaining: Decimal
    payments_remaining: int
    last_payment_date: Optional[date]

    status: DealStatus
    actual_completion_date: Optional[date]

    in_collections: bool
    collections_notes: Optional[str]

    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class DealWithRelations(Deal):
    merchant: Merchant
    offer: Offer
    bank_account: Optional[BankAccountBase]
    payments: List[Payment] = []


class DealSummary(BaseModel):
    total_deals: int
    active_deals: int
    completed_deals: int
    defaulted_deals: int
    total_funded: Decimal
    total_collected: Decimal
    total_outstanding: Decimal
    average_factor_rate: Decimal
    average_deal_size: Decimal
    completion_rate: float


class DealPerformance(BaseModel):
    deal_id: int
    deal_number: str
    payment_performance: float
    projected_completion_date: Optional[date]
    roi: Decimal
    irr: Optional[Decimal]


class DealFilter(BaseModel):
    merchant_id: Optional[int] = None
    status: Optional[DealStatus] = None
    funding_date_from: Optional[date] = None
    funding_date_to: Optional[date] = None
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    in_collections: Optional[bool] = None
