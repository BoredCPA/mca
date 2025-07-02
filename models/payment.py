# app/models/payment.py
from sqlalchemy import Column, Integer, String, DateTime, Numeric, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign key to deals table (to be created)
    deal_id = Column(Integer, ForeignKey("deals.id"), nullable=False, index=True)

    # Payment details
    date = Column(DateTime, nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    type = Column(String(50), nullable=False)  # e.g., "ACH", "Wire", "Check", "Credit Card"
    bounced = Column(Boolean, default=False, nullable=False)
    notes = Column(Text, nullable=True)

    # Tracking fields
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship to deal
    deal = relationship("Deal", back_populates="payments")