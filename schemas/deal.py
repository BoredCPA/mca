# app/schemas/deal.py
from pydantic import BaseModel, Field, validator
from decimal import Decimal
from datetime import datetime, date
from typing import Optional, List
from enum import Enum


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

    # Financial terms
    funded_amount: Decimal = Field(..., gt=0, decimal_places=2)
    factor_rate: Decimal = Field(..., gt=1, le=2, decimal_places=4)
    payment_amount: Decimal = Field(..., gt=0, decimal_places=2)
    payment_frequency: PaymentFrequency
    number_of_payments: int = Field(..., gt=0)

    # Dates
    funding_date: date
    first_payment_date: date

    # Optional fields
    notes: Optional[str] = Field(None, max_length=2000)
    created_by: Optional[str] = Field(None, max_length=100)

    @validator('first_payment_date')
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

    # Financial terms will be copied from the offer


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

    # Calculated fields
    rtr_amount: Decimal
    maturity_date: date

    # Balance tracking
    total_paid: Decimal
    balance_remaining: Decimal  # This is RTR - total_paid
    payments_remaining: int
    last_payment_date: Optional[date]

    # Status fields
    status: DealStatus
    actual_completion_date: Optional[date]

    # Collections
    in_collections: bool
    collections_notes: Optional[str]

    # Timestamps
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        orm_mode = True


class DealWithRelations(Deal):
    """Deal with related entities included"""
    from app.schemas.merchant import Merchant
    from app.schemas.offer import Offer
    from app.schemas.banking import BankAccount
    from app.schemas.payment import Payment

    merchant: Merchant
    offer: Offer
    bank_account: Optional[BankAccount]
    payments: List[Payment] = []


class DealSummary(BaseModel):
    """Summary statistics for deals"""
    total_deals: int
    active_deals: int
    completed_deals: int
    defaulted_deals: int
    total_funded: Decimal
    total_collected: Decimal
    total_outstanding: Decimal
    average_factor_rate: Decimal
    average_deal_size: Decimal
    completion_rate: float  # Percentage of deals completed successfully


class DealPerformance(BaseModel):
    """Performance metrics for a specific deal"""
    deal_id: int
    deal_number: str
    payment_performance: float  # Percentage of payments made on time
    projected_completion_date: Optional[date]
    roi: Decimal  # Return on investment
    irr: Optional[Decimal]  # Internal rate of return


class DealFilter(BaseModel):
    """Filters for searching deals"""
    merchant_id: Optional[int] = None
    status: Optional[DealStatus] = None
    funding_date_from: Optional[date] = None
    funding_date_to: Optional[date] = None
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    in_collections: Optional[bool] = None