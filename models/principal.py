# app/models/principal.py
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey, Boolean, Numeric, func
from sqlalchemy.orm import relationship
from app.database import Base


class Principal(Base):
    __tablename__ = "principals"

    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False, index=True)

    # Personal Information
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    ownership_percentage = Column(Numeric(5, 2), default=100.00)  # 0.00 to 100.00

    # Sensitive Information (should be encrypted in production)
    ssn = Column(String)  # Should be encrypted!
    date_of_birth = Column(Date)

    # Address Information
    home_address = Column(Text)
    city = Column(String)
    state = Column(String)
    zip = Column(String)

    # Contact Information
    phone = Column(String)
    email = Column(String)

    # Flags
    is_primary_contact = Column(Boolean, default=False)
    is_guarantor = Column(Boolean, default=True)  # Usually all principals are guarantors

    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    merchant = relationship("Merchant", back_populates="principals")

    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(String(100), nullable=True)