# app/schemas/offer.py
from pydantic import BaseModel, computed_field
from typing import Optional
from datetime import datetime
from decimal import Decimal


class OfferBase(BaseModel):
    merchant_id: int
    advance: Decimal
    factor: Decimal
    upfront_fees: Optional[Decimal] = 0.00
    upfront_fee_percentage: Optional[Decimal] = 0.00
    specified_percentage: Decimal
    payment_frequency: Optional[str] = "daily"
    renewal: Optional[bool] = False
    transfer_balance: Optional[Decimal] = 0.00
    deal_id: Optional[str] = None
    status: Optional[str] = "draft"


class OfferCreate(OfferBase):
    pass


class OfferUpdate(BaseModel):
    advance: Optional[Decimal] = None
    factor: Optional[Decimal] = None
    upfront_fees: Optional[Decimal] = None
    upfront_fee_percentage: Optional[Decimal] = None
    specified_percentage: Optional[Decimal] = None
    payment_frequency: Optional[str] = None
    renewal: Optional[bool] = None
    transfer_balance: Optional[Decimal] = None
    deal_id: Optional[str] = None
    status: Optional[str] = None


class Offer(OfferBase):
    id: int
    rtr: Optional[Decimal] = None
    net_funds: Optional[Decimal] = None
    payment_amount: Optional[Decimal] = None
    apr: Optional[Decimal] = None
    created_at: datetime
    updated_at: datetime
    sent_at: Optional[datetime] = None
    selected_at: Optional[datetime] = None
    funded_at: Optional[datetime] = None

    @computed_field
    @property
    def calculated_rtr(self) -> Decimal:
        """Calculate RTR (Return to Remit): advance * factor"""
        return self.advance * self.factor

    @computed_field
    @property
    def calculated_net_funds(self) -> Decimal:
        """Calculate net funds: advance - upfront_fees"""
        return self.advance - (self.upfront_fees or 0)

    class Config:
        from_attributes = True