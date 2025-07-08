# app/models/merchant.py
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, func, Boolean
from sqlalchemy.orm import relationship
from app.database import Base


class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String, nullable=False)
    address = Column(Text)
    city = Column(String)
    state = Column(String)
    zip = Column(String)
    fein = Column(String, unique=True)
    phone = Column(String)
    entity_type = Column(String)
    submitted_date = Column(Date)

    email = Column(String)
    contact_person = Column(String)
    status = Column(String, default="lead")
    notes = Column(Text)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    offers = relationship("Offer", back_populates="merchant")
    principals = relationship("Principal", back_populates="merchant")  # No cascade
    bank_accounts = relationship("BankAccount", back_populates="merchant")  # No cascade
    deals = relationship("Deal", back_populates="merchant")  # No cascade

    # Add:
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(String(100), nullable=True)
