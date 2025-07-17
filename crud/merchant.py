# app/crud/merchant.py - Updated for soft deletes
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, or_
from app.models.merchant import Merchant
from app.schemas.merchant import MerchantCreate, MerchantUpdate
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class MerchantCRUDError(Exception):
    """Base exception for merchant CRUD operations"""
    pass


# Commented out FEIN duplicate check as requested
# class DuplicateFEINError(MerchantCRUDError):
#     """Raised when FEIN already exists"""
#     pass


def create_merchant(db: Session, merchant: MerchantCreate) -> Merchant:
    """Create new merchant"""
    try:
        # Commented out FEIN duplicate check
        # if merchant.fein:
        #     existing = db.query(Merchant).filter(
        #         and_(
        #             Merchant.fein == merchant.fein,
        #             Merchant.is_deleted == False
        #         )
        #     ).first()
        #     if existing:
        #         raise DuplicateFEINError(f"FEIN {merchant.fein} already exists")

        db_merchant = Merchant(**merchant.dict())
        db.add(db_merchant)
        db.commit()
        db.refresh(db_merchant)
        return db_merchant
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating merchant: {str(e)}")
        raise MerchantCRUDError(f"Failed to create merchant: {str(e)}")


def get_merchant(db: Session, merchant_id: int) -> Merchant:
    """Get merchant by ID (only active merchants)"""
    return db.query(Merchant).filter(
        and_(
            Merchant.id == merchant_id,
            Merchant.is_deleted == False
        )
    ).first()


def get_merchant_by_fein(db: Session, fein: str) -> Merchant:
    """Get merchant by FEIN (only active merchants)"""
    return db.query(Merchant).filter(
        and_(
            Merchant.fein == fein,
            Merchant.is_deleted == False
        )
    ).first()


def get_merchants(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        status: str = None,
        search: str = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
) -> list[Merchant]:
    """Get merchants with filtering and pagination (only active merchants)"""

    query = db.query(Merchant).filter(Merchant.is_deleted == False)

    # Apply status filter
    if status:
        query = query.filter(Merchant.status == status)

    # Apply search filter
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Merchant.company_name.ilike(search_term),
                Merchant.contact_person.ilike(search_term),
                Merchant.email.ilike(search_term),
                Merchant.fein.ilike(search_term)
            )
        )

    # Apply sorting
    if sort_by == "company_name":
        order_col = Merchant.company_name
    elif sort_by == "status":
        order_col = Merchant.status
    elif sort_by == "updated_at":
        order_col = Merchant.updated_at
    else:
        order_col = Merchant.created_at

    if sort_order == "desc":
        query = query.order_by(order_col.desc())
    else:
        query = query.order_by(order_col.asc())

    return query.offset(skip).limit(limit).all()


def count_merchants(db: Session, status: str = None, search: str = None) -> int:
    """Count merchants with filters (only active merchants)"""
    query = db.query(Merchant).filter(Merchant.is_deleted == False)

    if status:
        query = query.filter(Merchant.status == status)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Merchant.company_name.ilike(search_term),
                Merchant.contact_person.ilike(search_term),
                Merchant.email.ilike(search_term),
                Merchant.fein.ilike(search_term)
            )
        )

    return query.count()


def update_merchant(
        db: Session,
        merchant_id: int,
        merchant_update: MerchantUpdate
) -> Merchant:
    """Update merchant (only active merchants)"""
    try:
        merchant = get_merchant(db, merchant_id)
        if not merchant:
            return None

        # Commented out FEIN duplicate check
        # if merchant_update.fein and merchant_update.fein != merchant.fein:
        #     existing = db.query(Merchant).filter(
        #         and_(
        #             Merchant.fein == merchant_update.fein,
        #             Merchant.id != merchant_id,
        #             Merchant.is_deleted == False
        #         )
        #     ).first()
        #     if existing:
        #         raise DuplicateFEINError(f"FEIN {merchant_update.fein} already exists")

        # Update fields
        update_data = merchant_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(merchant, field, value)

        merchant.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(merchant)
        return merchant
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating merchant {merchant_id}: {str(e)}")
        raise MerchantCRUDError(f"Failed to update merchant: {str(e)}")


def delete_merchant(db: Session, merchant_id: int, deleted_by: str = "system") -> bool:
    """Soft delete merchant"""
    try:
        merchant = get_merchant(db, merchant_id)
        if not merchant:
            return False

        # Soft delete
        merchant.is_deleted = True
        merchant.deleted_at = datetime.utcnow()
        merchant.deleted_by = deleted_by

        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting merchant {merchant_id}: {str(e)}")
        raise MerchantCRUDError(f"Failed to delete merchant: {str(e)}")


def get_merchant_stats(db: Session) -> dict:
    """Get merchant statistics (only active merchants)"""
    try:
        # Count by status
        status_counts = db.query(
            Merchant.status,
            func.count(Merchant.id).label('count')
        ).filter(
            Merchant.is_deleted == False
        ).group_by(Merchant.status).all()

        # Total count
        total = db.query(Merchant).filter(Merchant.is_deleted == False).count()

        # Recent activity (last 30 days)
        from datetime import datetime, timedelta
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_count = db.query(Merchant).filter(
            and_(
                Merchant.created_at >= thirty_days_ago,
                Merchant.is_deleted == False
            )
        ).count()

        return {
            "total": total,
            "recent_30_days": recent_count,
            "by_status": {status: count for status, count in status_counts}
        }
    except Exception as e:
        logger.error(f"Error getting merchant stats: {str(e)}")
        raise MerchantCRUDError(f"Failed to get merchant statistics: {str(e)}")


def restore_merchant(db: Session, merchant_id: int) -> Merchant:
    """Restore soft-deleted merchant"""
    try:
        merchant = db.query(Merchant).filter(
            and_(
                Merchant.id == merchant_id,
                Merchant.is_deleted == True
            )
        ).first()

        if not merchant:
            return None

        merchant.is_deleted = False
        merchant.deleted_at = None
        merchant.deleted_by = None
        merchant.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(merchant)
        return merchant
    except Exception as e:
        db.rollback()
        logger.error(f"Error restoring merchant {merchant_id}: {str(e)}")
        raise MerchantCRUDError(f"Failed to restore merchant: {str(e)}")