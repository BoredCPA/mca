# app/models/merchant.py (UPDATED)
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, func
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

    # Relationship to offers
    offers = relationship("Offer", back_populates="merchant")