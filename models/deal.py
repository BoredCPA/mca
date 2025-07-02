# app/models/deal.py
from sqlalchemy import Column, Integer, String, DateTime, Numeric, Boolean, ForeignKey, Text, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Deal(Base):
    __tablename__ = "deals"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign keys
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False, index=True)
    offer_id = Column(Integer, ForeignKey("offers.id"), nullable=False, index=True)
    bank_account_id = Column(Integer, ForeignKey("bank_accounts.id"), nullable=True)

    # Deal identification
    deal_number = Column(String(50), unique=True, nullable=False, index=True)  # e.g., "MCA-2024-0001"

    # Renewal tracking
    is_renewal = Column(Boolean, default=False, nullable=False)
    total_transfer_balance = Column(Numeric(12, 2), default=0, nullable=False)  # Sum of all transfer balances
    net_cash_to_merchant = Column(Numeric(12, 2), nullable=True)  # funded_amount - fees - total_transfer_balance

    # Financial terms (copied from offer at time of funding)
    funded_amount = Column(Numeric(12, 2), nullable=False)
    factor_rate = Column(Numeric(5, 4), nullable=False)
    rtr_amount = Column(Numeric(12, 2), nullable=False)  # Return to Remit
    payment_amount = Column(Numeric(10, 2), nullable=False)
    payment_frequency = Column(String(20), nullable=False)  # daily, weekly, bi-weekly, monthly
    number_of_payments = Column(Integer, nullable=False)

    # Deal status
    status = Column(String(50), nullable=False,
                    default="active")  # active, completed, defaulted, suspended, cancelled, renewed

    # Important dates
    funding_date = Column(Date, nullable=False)
    first_payment_date = Column(Date, nullable=False)
    maturity_date = Column(Date, nullable=False)  # Expected completion date
    actual_completion_date = Column(Date, nullable=True)

    # Balance tracking
    total_paid = Column(Numeric(12, 2), default=0, nullable=False)
    balance_remaining = Column(Numeric(12, 2), nullable=False)  # RTR - total_paid (calculated field)
    payments_remaining = Column(Integer, nullable=False)
    last_payment_date = Column(Date, nullable=True)

    # Collections
    in_collections = Column(Boolean, default=False, nullable=False)
    collections_notes = Column(Text, nullable=True)

    # Administrative
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(String(100), nullable=True)  # User who created the deal

    # Relationships
    merchant = relationship("Merchant", back_populates="deals")
    offer = relationship("Offer", back_populates="deal")
    bank_account = relationship("BankAccount")
    payments = relationship("Payment", back_populates="deal", cascade="all, delete-orphan")
    renewal_junctions = relationship("DealRenewalJunction", back_populates="deal",
                                     foreign_keys="DealRenewalJunction.deal_id")