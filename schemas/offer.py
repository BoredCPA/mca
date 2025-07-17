# app/schemas/offer.py
from pydantic import BaseModel, computed_field, field_validator, model_validator
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

    # New fields for bidirectional calculation
    payment_amount: Optional[Decimal] = None
    number_of_periods: Optional[int] = None

    @model_validator(mode='after')
    def validate_payment_calculation(self):
        """Ensure either payment_amount or number_of_periods is provided, not both"""
        if self.payment_amount is not None and self.number_of_periods is not None:
            raise ValueError("Provide either payment_amount OR number_of_periods, not both")
        return self


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
    payment_amount: Optional[Decimal] = None
    number_of_periods: Optional[int] = None

    @model_validator(mode='after')
    def validate_payment_calculation(self):
        """Ensure either payment_amount or number_of_periods is provided, not both"""
        if self.payment_amount is not None and self.number_of_periods is not None:
            raise ValueError("Provide either payment_amount OR number_of_periods, not both")
        return self


class Offer(BaseModel):
    id: int
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

    # Both fields can be present in response (no validation constraint)
    payment_amount: Optional[Decimal] = None
    number_of_periods: Optional[int] = None

    rtr: Optional[Decimal] = None
    net_funds: Optional[Decimal] = None
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