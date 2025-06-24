# app/models/banking.py
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class BankAccount(Base):
    __tablename__ = "bank_accounts"

    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False)

    # Account details
    account_name = Column(String, nullable=False)  # e.g., "Business Checking"
    account_number = Column(String, nullable=False)  # Last 4 digits only for security
    routing_number = Column(String, nullable=False)
    bank_name = Column(String, nullable=False)
    account_type = Column(String, nullable=False)  # checking, savings

    # Status
    is_active = Column(Boolean, default=True)
    is_primary = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    merchant = relationship("Merchant", back_populates="bank_accounts")
    # If you have a Deal model, uncomment this:
    # deals = relationship("Deal", back_populates="bank_account")

    __table_args__ = (
        CheckConstraint(
            "account_type IN ('checking', 'savings')",
            name="check_account_type"
        ),
    )
