# app/crud/merchant.py
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.models.merchant import Merchant as MerchantModel
from app.schemas.merchant import MerchantCreate, MerchantUpdate
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class MerchantCRUDError(Exception):
    """Custom exception for merchant CRUD operations"""
    pass


class DuplicateFEINError(MerchantCRUDError):
    """Raised when trying to create/update a merchant with duplicate FEIN"""
    pass


def create_merchant(db: Session, merchant: MerchantCreate) -> MerchantModel:
    """
    Create a new merchant with validation and error handling
    """
    try:
        # Check for duplicate FEIN
        if merchant.fein:
            existing = db.query(MerchantModel).filter(
                MerchantModel.fein == merchant.fein
            ).first()
            if existing:
                raise DuplicateFEINError(
                    f"A merchant with FEIN {merchant.fein} already exists"
                )

        # Create merchant instance
        db_merchant = MerchantModel(**merchant.dict())

        # Add to session and commit
        db.add(db_merchant)
        db.commit()
        db.refresh(db_merchant)

        logger.info(f"Created merchant: {db_merchant.id} - {db_merchant.company_name}")
        return db_merchant

    except IntegrityError as e:
        db.rollback()
        logger.error(f"Integrity error creating merchant: {str(e)}")
        if "fein" in str(e).lower():
            raise DuplicateFEINError("FEIN must be unique")
        raise MerchantCRUDError(f"Database integrity error: {str(e)}")
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error creating merchant: {str(e)}")
        raise MerchantCRUDError(f"Failed to create merchant: {str(e)}")
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error creating merchant: {str(e)}")
        raise MerchantCRUDError(f"Unexpected error: {str(e)}")


def get_merchant(db: Session, merchant_id: int) -> Optional[MerchantModel]:
    """
    Get a single merchant by ID
    """
    try:
        merchant = db.query(MerchantModel).filter(
            MerchantModel.id == merchant_id
        ).first()
        return merchant
    except SQLAlchemyError as e:
        logger.error(f"Error fetching merchant {merchant_id}: {str(e)}")
        raise MerchantCRUDError(f"Failed to fetch merchant: {str(e)}")


def get_merchant_by_fein(db: Session, fein: str) -> Optional[MerchantModel]:
    """
    Get a merchant by FEIN
    """
    try:
        merchant = db.query(MerchantModel).filter(
            MerchantModel.fein == fein
        ).first()
        return merchant
    except SQLAlchemyError as e:
        logger.error(f"Error fetching merchant by FEIN {fein}: {str(e)}")
        raise MerchantCRUDError(f"Failed to fetch merchant: {str(e)}")


def get_merchants(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
) -> List[MerchantModel]:
    """
    Get merchants with filtering, pagination, and sorting
    """
    try:
        query = db.query(MerchantModel)

        # Apply filters
        if status:
            query = query.filter(MerchantModel.status == status)

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (MerchantModel.company_name.ilike(search_term)) |
                (MerchantModel.email.ilike(search_term)) |
                (MerchantModel.contact_person.ilike(search_term)) |
                (MerchantModel.fein.ilike(search_term))
            )

        # Apply sorting
        sort_column = getattr(MerchantModel, sort_by, MerchantModel.created_at)
        if sort_order.lower() == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        # Apply pagination
        merchants = query.offset(skip).limit(limit).all()
        return merchants

    except SQLAlchemyError as e:
        logger.error(f"Error fetching merchants: {str(e)}")
        raise MerchantCRUDError(f"Failed to fetch merchants: {str(e)}")


def count_merchants(
        db: Session,
        status: Optional[str] = None,
        search: Optional[str] = None
) -> int:
    """
    Count merchants with optional filters
    """
    try:
        query = db.query(MerchantModel)

        if status:
            query = query.filter(MerchantModel.status == status)

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (MerchantModel.company_name.ilike(search_term)) |
                (MerchantModel.email.ilike(search_term)) |
                (MerchantModel.contact_person.ilike(search_term)) |
                (MerchantModel.fein.ilike(search_term))
            )

        return query.count()

    except SQLAlchemyError as e:
        logger.error(f"Error counting merchants: {str(e)}")
        raise MerchantCRUDError(f"Failed to count merchants: {str(e)}")


def update_merchant(
        db: Session,
        merchant_id: int,
        merchant_update: MerchantUpdate
) -> Optional[MerchantModel]:
    """
    Update a merchant with validation
    """
    try:
        # Get the merchant
        db_merchant = db.query(MerchantModel).filter(
            MerchantModel.id == merchant_id
        ).first()

        if not db_merchant:
            return None

        # Get update data
        update_data = merchant_update.dict(exclude_unset=True)

        # Check for FEIN uniqueness if updating FEIN
        if "fein" in update_data and update_data["fein"]:
            existing = db.query(MerchantModel).filter(
                MerchantModel.fein == update_data["fein"],
                MerchantModel.id != merchant_id
            ).first()
            if existing:
                raise DuplicateFEINError(
                    f"A merchant with FEIN {update_data['fein']} already exists"
                )

        # Update fields
        for field, value in update_data.items():
            setattr(db_merchant, field, value)

        # Update timestamp
        db_merchant.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(db_merchant)

        logger.info(f"Updated merchant: {merchant_id}")
        return db_merchant

    except IntegrityError as e:
        db.rollback()
        logger.error(f"Integrity error updating merchant {merchant_id}: {str(e)}")
        if "fein" in str(e).lower():
            raise DuplicateFEINError("FEIN must be unique")
        raise MerchantCRUDError(f"Database integrity error: {str(e)}")
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error updating merchant {merchant_id}: {str(e)}")
        raise MerchantCRUDError(f"Failed to update merchant: {str(e)}")


def delete_merchant(db: Session, merchant_id: int) -> bool:
    """
    Delete a merchant (soft delete by setting status to 'closed')
    """
    try:
        db_merchant = db.query(MerchantModel).filter(
            MerchantModel.id == merchant_id
        ).first()

        if not db_merchant:
            return False

        # Check if merchant has active offers
        from app.models.offer import Offer
        active_offers = db.query(Offer).filter(
            Offer.merchant_id == merchant_id,
            Offer.status.in_(["sent", "selected", "funded"])
        ).count()

        if active_offers > 0:
            raise MerchantCRUDError(
                "Cannot delete merchant with active offers. "
                "Please close or delete all offers first."
            )

        # Soft delete by setting status
        db_merchant.status = "closed"
        db_merchant.updated_at = datetime.utcnow()

        db.commit()
        logger.info(f"Soft deleted merchant: {merchant_id}")
        return True

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error deleting merchant {merchant_id}: {str(e)}")
        raise MerchantCRUDError(f"Failed to delete merchant: {str(e)}")


def get_merchant_stats(db: Session) -> Dict[str, Any]:
    """
    Get merchant statistics
    """
    try:
        total = db.query(MerchantModel).count()

        stats = {
            "total": total,
            "by_status": {},
            "recent_count": 0
        }

        # Count by status
        statuses = ["lead", "prospect", "applicant", "approved", "declined", "funded", "closed"]
        for status in statuses:
            count = db.query(MerchantModel).filter(
                MerchantModel.status == status
            ).count()
            stats["by_status"][status] = count

        # Count recent (last 30 days)
        from datetime import datetime, timedelta
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        stats["recent_count"] = db.query(MerchantModel).filter(
            MerchantModel.created_at >= thirty_days_ago
        ).count()

        return stats

    except SQLAlchemyError as e:
        logger.error(f"Error getting merchant stats: {str(e)}")
        raise MerchantCRUDError(f"Failed to get merchant statistics: {str(e)}")