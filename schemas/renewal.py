# app/schemas/renewal.py
from pydantic import BaseModel, Field, validator
from decimal import Decimal
from datetime import datetime, date
from typing import Optional, List
from enum import Enum


class RenewalStatus(str, Enum):
    ACTIVE = "active"
    REVERSED = "reversed"
    CANCELLED = "cancelled"


# RenewalInfo Schemas
class RenewalInfoBase(BaseModel):
    old_deal_id: int = Field(..., description="ID of the old deal being paid off")
    transfer_balance: Decimal = Field(..., gt=0, decimal_places=2, description="Amount being transferred from old deal")
    final_payment_amount: Optional[Decimal] = Field(None, gt=0, decimal_places=2,
                                                    description="Final payment if different from transfer balance")
    payoff_date: Optional[date] = None
    notes: Optional[str] = Field(None, max_length=1000)

    @validator('transfer_balance')
    def validate_transfer_balance(cls, v):
        if v <= 0:
            raise ValueError('Transfer balance must be greater than 0')
        return v


class RenewalInfoCreate(RenewalInfoBase):
    pass


class RenewalInfoUpdate(BaseModel):
    transfer_balance: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    final_payment_amount: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    payoff_date: Optional[date] = None
    notes: Optional[str] = Field(None, max_length=1000)


class RenewalInfo(RenewalInfoBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True


# DealRenewalJunction Schemas
class DealRenewalJunctionBase(BaseModel):
    deal_id: int = Field(..., description="ID of the new renewal deal")
    renewal_info_id: int = Field(..., description="ID of the renewal info record")


class DealRenewalJunctionCreate(DealRenewalJunctionBase):
    pass


class DealRenewalJunction(DealRenewalJunctionBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True


# DealRenewalRelationship Schemas
class DealRenewalRelationshipBase(BaseModel):
    old_deal_id: int = Field(..., description="ID of the old deal that was renewed")
    new_deal_id: int = Field(..., description="ID of the new renewal deal")
    renewal_info_id: int = Field(..., description="ID of the renewal info record")
    status: RenewalStatus = Field(default=RenewalStatus.ACTIVE)


class DealRenewalRelationshipCreate(DealRenewalRelationshipBase):
    pass


class DealRenewalRelationshipUpdate(BaseModel):
    status: Optional[RenewalStatus] = None


class DealRenewalRelationship(DealRenewalRelationshipBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        orm_mode = True


# Renewal Process Schemas
class RenewalDealInfo(BaseModel):
    """Information about an old deal to be renewed"""
    old_deal_id: int
    transfer_balance: Decimal = Field(..., gt=0, decimal_places=2)
    payoff_date: Optional[date] = None
    notes: Optional[str] = None


class CreateRenewalDeal(BaseModel):
    """Create a new renewal deal with multiple old deals"""
    merchant_id: int
    bank_account_id: Optional[int] = None

    # New deal terms (from offer)
    offer_id: int
    funding_date: date
    first_payment_date: date

    # Renewal specific
    old_deals: List[RenewalDealInfo] = Field(..., min_items=1, description="List of old deals being renewed")

    # Administrative
    notes: Optional[str] = None
    created_by: Optional[str] = None


class RenewalSummary(BaseModel):
    """Summary of a renewal deal"""
    deal_id: int
    deal_number: str
    is_renewal: bool
    funded_amount: Decimal
    total_transfer_balance: Decimal
    net_cash_to_merchant: Decimal
    old_deals_count: int
    old_deal_ids: List[int]
    created_at: datetime


class RenewalChain(BaseModel):
    """Shows the complete renewal chain for a deal"""
    deal_id: int
    deal_number: str

    # If this deal was renewed
    was_renewed: bool
    renewed_into: Optional[dict] = None  # {deal_id, deal_number, renewal_date}

    # If this deal is a renewal
    is_renewal: bool
    renewed_from: List[dict] = []  # [{deal_id, deal_number, transfer_balance}]