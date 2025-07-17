# app/crud/principal.py
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import and_, or_
from app.models.principal import Principal as PrincipalModel
from app.models.merchant import Merchant as MerchantModel
from app.schemas.principal import PrincipalCreate, PrincipalUpdate
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class PrincipalCRUDError(Exception):
    """Custom exception for principal CRUD operations"""
    pass


class DuplicateSSNError(PrincipalCRUDError):
    """Raised when trying to create/update a principal with duplicate SSN for same merchant"""
    pass


class OwnershipExceededError(PrincipalCRUDError):
    """Raised when total ownership percentage would exceed 100%"""
    pass


def verify_merchant_exists(db: Session, merchant_id: int) -> bool:
    """Verify that the merchant exists"""
    merchant = db.query(MerchantModel).filter(MerchantModel.id == merchant_id).first()
    return merchant is not None


def calculate_total_ownership(db: Session, merchant_id: int, exclude_principal_id: Optional[int] = None) -> float:
    """Calculate total ownership percentage for a merchant"""
    query = db.query(PrincipalModel).filter(PrincipalModel.merchant_id == merchant_id)
    if exclude_principal_id:
        query = query.filter(PrincipalModel.id != exclude_principal_id)

    principals = query.all()
    return sum(p.ownership_percentage or 0 for p in principals)

def get_all_principals(
    db: Session,
    skip: int = 0,
    limit: int = 1000
) -> List[PrincipalModel]:
    """Get all active principals (excludes soft deleted)"""
    return db.query(PrincipalModel).filter(
        PrincipalModel.is_deleted == False
    ).offset(skip).limit(limit).all()


def create_principal(db: Session, principal: PrincipalCreate) -> PrincipalModel:
    """Create a new principal with validation"""
    try:
        # Verify merchant exists
        if not verify_merchant_exists(db, principal.merchant_id):
            raise PrincipalCRUDError(f"Merchant with ID {principal.merchant_id} not found")

        # Check for duplicate SSN within the same merchant
        if principal.ssn:
            existing = db.query(PrincipalModel).filter(
                and_(
                    PrincipalModel.merchant_id == principal.merchant_id,
                    PrincipalModel.ssn == principal.ssn
                )
            ).first()
            if existing:
                raise DuplicateSSNError(
                    f"A principal with SSN {principal.ssn[:3]}-XX-XXXX already exists for this merchant"
                )

        # Check total ownership percentage
        current_total = calculate_total_ownership(db, principal.merchant_id)
        new_total = current_total + (principal.ownership_percentage or 0)
        if new_total > 100:
            raise OwnershipExceededError(
                f"Total ownership would be {new_total}%. Maximum allowed is 100%"
            )

        # If this is the primary contact, unset others
        if principal.is_primary_contact:
            db.query(PrincipalModel).filter(
                PrincipalModel.merchant_id == principal.merchant_id
            ).update({"is_primary_contact": False})

        # Create principal
        db_principal = PrincipalModel(**principal.dict())
        db.add(db_principal)
        db.commit()
        db.refresh(db_principal)

        logger.info(f"Created principal: {db_principal.id} for merchant {principal.merchant_id}")
        return db_principal

    except IntegrityError as e:
        db.rollback()
        logger.error(f"Integrity error creating principal: {str(e)}")
        raise PrincipalCRUDError(f"Database integrity error: {str(e)}")
    except (DuplicateSSNError, OwnershipExceededError):
        db.rollback()
        raise
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error creating principal: {str(e)}")
        raise PrincipalCRUDError(f"Failed to create principal: {str(e)}")


def get_principal(db: Session, principal_id: int) -> Optional[PrincipalModel]:
    """Get a single principal by ID"""
    try:
        return db.query(PrincipalModel).filter(PrincipalModel.id == principal_id).first()
    except SQLAlchemyError as e:
        logger.error(f"Error fetching principal {principal_id}: {str(e)}")
        raise PrincipalCRUDError(f"Failed to fetch principal: {str(e)}")


def get_principals_by_merchant(
        db: Session,
        merchant_id: int,
        only_guarantors: bool = False
) -> List[PrincipalModel]:
    """Get all principals for a merchant"""
    try:
        query = db.query(PrincipalModel).filter(PrincipalModel.merchant_id == merchant_id)

        if only_guarantors:
            query = query.filter(PrincipalModel.is_guarantor == True)

        return query.order_by(
            PrincipalModel.is_primary_contact.desc(),
            PrincipalModel.ownership_percentage.desc()
        ).all()

    except SQLAlchemyError as e:
        logger.error(f"Error fetching principals for merchant {merchant_id}: {str(e)}")
        raise PrincipalCRUDError(f"Failed to fetch principals: {str(e)}")


def get_principals_by_ssn(db: Session, ssn: str) -> List[PrincipalModel]:
    """Get all principals with a specific SSN (across all merchants)"""
    try:
        return db.query(PrincipalModel).filter(PrincipalModel.ssn == ssn).all()
    except SQLAlchemyError as e:
        logger.error(f"Error fetching principals by SSN: {str(e)}")
        raise PrincipalCRUDError(f"Failed to fetch principals: {str(e)}")


def update_principal(
        db: Session,
        principal_id: int,
        principal_update: PrincipalUpdate
) -> Optional[PrincipalModel]:
    """Update a principal with validation"""
    try:
        # Get the principal
        db_principal = db.query(PrincipalModel).filter(
            PrincipalModel.id == principal_id
        ).first()

        if not db_principal:
            return None

        update_data = principal_update.dict(exclude_unset=True)

        # Check SSN uniqueness if updating SSN
        if "ssn" in update_data and update_data["ssn"]:
            existing = db.query(PrincipalModel).filter(
                and_(
                    PrincipalModel.merchant_id == db_principal.merchant_id,
                    PrincipalModel.ssn == update_data["ssn"],
                    PrincipalModel.id != principal_id
                )
            ).first()
            if existing:
                raise DuplicateSSNError(
                    f"A principal with this SSN already exists for this merchant"
                )

        # Check ownership percentage if updating
        if "ownership_percentage" in update_data:
            current_total = calculate_total_ownership(
                db,
                db_principal.merchant_id,
                exclude_principal_id=principal_id
            )
            new_total = current_total + (update_data["ownership_percentage"] or 0)
            if new_total > 100:
                raise OwnershipExceededError(
                    f"Total ownership would be {new_total}%. Maximum allowed is 100%"
                )

        # Handle primary contact update
        if update_data.get("is_primary_contact", False):
            # Unset other primary contacts for this merchant
            db.query(PrincipalModel).filter(
                and_(
                    PrincipalModel.merchant_id == db_principal.merchant_id,
                    PrincipalModel.id != principal_id
                )
            ).update({"is_primary_contact": False})

        # Update fields
        for field, value in update_data.items():
            setattr(db_principal, field, value)

        db_principal.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(db_principal)

        logger.info(f"Updated principal: {principal_id}")
        return db_principal

    except (DuplicateSSNError, OwnershipExceededError):
        db.rollback()
        raise
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error updating principal {principal_id}: {str(e)}")
        raise PrincipalCRUDError(f"Failed to update principal: {str(e)}")


def delete_principal(db: Session, principal_id: int) -> bool:
    """Delete a principal"""
    try:
        db_principal = db.query(PrincipalModel).filter(
            PrincipalModel.id == principal_id
        ).first()

        if not db_principal:
            return False

        # Check if this is the only principal for the merchant
        principal_count = db.query(PrincipalModel).filter(
            PrincipalModel.merchant_id == db_principal.merchant_id
        ).count()

        if principal_count == 1:
            logger.warning(f"Deleting the last principal for merchant {db_principal.merchant_id}")

        db.delete(db_principal)
        db.commit()

        logger.info(f"Deleted principal: {principal_id}")
        return True

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error deleting principal {principal_id}: {str(e)}")
        raise PrincipalCRUDError(f"Failed to delete principal: {str(e)}")


def get_merchant_ownership_summary(db: Session, merchant_id: int) -> Dict[str, Any]:
    """Get ownership summary for a merchant"""
    try:
        principals = get_principals_by_merchant(db, merchant_id)

        total_ownership = sum(p.ownership_percentage or 0 for p in principals)
        primary_contact = next((p for p in principals if p.is_primary_contact), None)
        guarantor_count = sum(1 for p in principals if p.is_guarantor)

        return {
            "merchant_id": merchant_id,
            "principal_count": len(principals),
            "total_ownership_percentage": float(total_ownership),
            "ownership_allocated": total_ownership == 100,
            "primary_contact": {
                "id": primary_contact.id,
                "name": f"{primary_contact.first_name} {primary_contact.last_name}"
            } if primary_contact else None,
            "guarantor_count": guarantor_count,
            "principals": [
                {
                    "id": p.id,
                    "name": f"{p.first_name} {p.last_name}",
                    "ownership_percentage": float(p.ownership_percentage or 0),
                    "is_primary_contact": p.is_primary_contact,
                    "is_guarantor": p.is_guarantor
                }
                for p in principals
            ]
        }

    except SQLAlchemyError as e:
        logger.error(f"Error getting ownership summary for merchant {merchant_id}: {str(e)}")
        raise PrincipalCRUDError(f"Failed to get ownership summary: {str(e)}")