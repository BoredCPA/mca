# app/models/offer.py
from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class Offer(Base):
    __tablename__ = "offers"

    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False)

    # Financial details
    advance = Column(Numeric(12, 2), nullable=False)
    factor = Column(Numeric(5, 3), nullable=False)
    upfront_fees = Column(Numeric(12, 2), default=0.00)
    upfront_fee_percentage = Column(Numeric(5, 2), default=0.00)
    specified_percentage = Column(Numeric(5, 2), nullable=False)
    payment_frequency = Column(String, default="daily")
    renewal = Column(Boolean, default=False)
    transfer_balance = Column(Numeric(12, 2), default=0.00)
    deal_id = Column(String, unique=True, nullable=True)

    # Payment calculation fields - bidirectional
    payment_amount = Column(Numeric(12, 2), nullable=True)
    number_of_periods = Column(Integer, nullable=True)

    # Calculated fields
    rtr = Column(Numeric(12, 2))  # advance * factor
    net_funds = Column(Numeric(12, 2))  # advance - upfront_fees
    apr = Column(Numeric(5, 2))

    # Status tracking
    status = Column(String, default="draft")  # draft, sent, selected, funded

    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    sent_at = Column(DateTime, nullable=True)
    selected_at = Column(DateTime, nullable=True)
    funded_at = Column(DateTime, nullable=True)

    # Soft delete fields
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(String(100), nullable=True)

    # Relationships
    merchant = relationship("Merchant", back_populates="offers")
    deal = relationship("Deal", back_populates="offer", uselist=False)  # One-to-one relationship