# app/crud/banking.py
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from app.models.banking import BankAccount
from app.schemas.banking import BankAccountCreate, BankAccountUpdate
import datetime
from fastapi import HTTPException


class CRUDBankAccount:
    def create(
            self,
            db: Session,
            merchant_id: int,
            bank_account: BankAccountCreate
    ) -> BankAccount:
        # If this is set as primary, unset other primary accounts
        if bank_account.is_primary:
            db.query(BankAccount).filter(
                and_(
                    BankAccount.merchant_id == merchant_id,
                    BankAccount.is_primary == True
                )
            ).update({"is_primary": False})

        db_bank_account = BankAccount(
            merchant_id=merchant_id,
            **bank_account.dict()
        )
        db.add(db_bank_account)
        db.commit()
        db.refresh(db_bank_account)
        return db_bank_account

    def get(self, db: Session, bank_account_id: int, include_deleted: bool = False) -> Optional[BankAccount]:
        query = db.query(BankAccount).filter(
            BankAccount.id == bank_account_id
        )

        # By default, exclude deleted records
        if not include_deleted:
            query = query.filter(BankAccount.is_deleted == False)

        return query.first()

    def get_by_merchant(
            self,
            db: Session,
            merchant_id: int,
            skip: int = 0,
            limit: int = 100,
            active_only: bool = False,
            include_deleted: bool = False
    ) -> List[BankAccount]:
        query = db.query(BankAccount).filter(
            BankAccount.merchant_id == merchant_id
        )

        # Exclude deleted unless specifically requested
        if not include_deleted:
            query = query.filter(BankAccount.is_deleted == False)

        if active_only:
            query = query.filter(BankAccount.is_active == True)

        return query.offset(skip).limit(limit).all()

    def update(
            self,
            db: Session,
            bank_account_id: int,
            bank_account_update: BankAccountUpdate
    ) -> Optional[BankAccount]:
        db_bank_account = self.get(db, bank_account_id)
        if not db_bank_account:
            return None

        update_data = bank_account_update.dict(exclude_unset=True)

        # Handle primary account logic
        if update_data.get("is_primary") == True:
            db.query(BankAccount).filter(
                and_(
                    BankAccount.merchant_id == db_bank_account.merchant_id,
                    BankAccount.is_primary == True,
                    BankAccount.id != bank_account_id
                )
            ).update({"is_primary": False})

        for field, value in update_data.items():
            setattr(db_bank_account, field, value)

        db.commit()
        db.refresh(db_bank_account)
        return db_bank_account

    def delete(self, db: Session, bank_account_id: int, deleted_by: str = None) -> bool:
        db_bank_account = self.get(db, bank_account_id)
        if not db_bank_account:
            return False

        # Check if already deleted
        if db_bank_account.is_deleted:
            return False  # Already deleted, nothing to do

        # Soft delete - just mark as deleted
        db_bank_account.is_deleted = True
        db_bank_account.deleted_at = datetime.utcnow()
        db_bank_account.deleted_by = deleted_by

        # Also deactivate it
        db_bank_account.is_active = False

        db.commit()
        return True

    def restore(self, db: Session, bank_account_id: int) -> Optional[BankAccount]:
        """Restore a soft-deleted bank account"""
        # Need to include deleted records in search
        db_bank_account = self.get(db, bank_account_id, include_deleted=True)

        if not db_bank_account:
            return None

        if not db_bank_account.is_deleted:
            return db_bank_account  # Not deleted, nothing to restore

        # Restore
        db_bank_account.is_deleted = False
        db_bank_account.deleted_at = None
        db_bank_account.deleted_by = None
        # Note: Don't automatically reactivate - that's a business decision
        # db_bank_account.is_active = True  # Uncomment if you want this

        db.commit()
        db.refresh(db_bank_account)
        return db_bank_account

    def set_primary(
            self,
            db: Session,
            merchant_id: int,
            bank_account_id: int
    ) -> Optional[BankAccount]:
        # Unset all primary accounts for this merchant
        db.query(BankAccount).filter(
            and_(
                BankAccount.merchant_id == merchant_id,
                BankAccount.is_primary == True
            )
        ).update({"is_primary": False})

        # Set the new primary
        db_bank_account = db.query(BankAccount).filter(
            and_(
                BankAccount.id == bank_account_id,
                BankAccount.merchant_id == merchant_id
            )
        ).first()

        if db_bank_account:
            db_bank_account.is_primary = True
            db.commit()
            db.refresh(db_bank_account)

        return db_bank_account


crud_bank_account = CRUDBankAccount()