# app/models/renewal.py
from sqlalchemy import Column, Integer, String, DateTime, Numeric, Boolean, ForeignKey, Date, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class RenewalInfo(Base):
    """Stores information about each old deal being paid off in a renewal"""
    __tablename__ = "renewal_info"

    id = Column(Integer, primary_key=True, index=True)

    # The old deal being paid off
    old_deal_id = Column(Integer, ForeignKey("deals.id"), nullable=False, index=True)

    # Financial details
    transfer_balance = Column(Numeric(12, 2), nullable=False)  # Amount being transferred from this old deal
    final_payment_amount = Column(Numeric(12, 2), nullable=True)  # If different from transfer_balance

    # Tracking
    payoff_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    old_deal = relationship("Deal", foreign_keys=[old_deal_id])
    deal_renewal_junctions = relationship("DealRenewalJunction", back_populates="renewal_info")
    renewal_relationships = relationship("DealRenewalRelationship", back_populates="renewal_info")


class DealRenewalJunction(Base):
    """Links new renewal deals to their renewal_info records"""
    __tablename__ = "deal_renewal_junction"

    id = Column(Integer, primary_key=True, index=True)

    # The new renewal deal
    deal_id = Column(Integer, ForeignKey("deals.id"), nullable=False, index=True)

    # The renewal info for one of the old deals
    renewal_info_id = Column(Integer, ForeignKey("renewal_info.id"), nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    deal = relationship("Deal", back_populates="renewal_junctions")
    renewal_info = relationship("RenewalInfo", back_populates="deal_renewal_junctions")


class DealRenewalRelationship(Base):
    """Tracks the complete renewal chain between old and new deals"""
    __tablename__ = "deal_renewal_relationships"

    id = Column(Integer, primary_key=True, index=True)

    # The old deal that was renewed
    old_deal_id = Column(Integer, ForeignKey("deals.id"), nullable=False, index=True)

    # The new renewal deal that paid it off
    new_deal_id = Column(Integer, ForeignKey("deals.id"), nullable=False, index=True)

    # Link to the renewal info for details
    renewal_info_id = Column(Integer, ForeignKey("renewal_info.id"), nullable=False)

    # Status tracking
    status = Column(String(20), default="active", nullable=False)  # active, reversed, cancelled

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(String(100), nullable=True)

    # Relationships
    old_deal = relationship("Deal", foreign_keys=[old_deal_id], backref="renewed_to_relationships")
    new_deal = relationship("Deal", foreign_keys=[new_deal_id], backref="renewed_from_relationships")
    renewal_info = relationship("RenewalInfo", back_populates="renewal_relationships")