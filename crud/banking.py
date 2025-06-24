# app/crud/banking.py
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from app.models.banking import BankAccount
from app.schemas.banking import BankAccountCreate, BankAccountUpdate
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

    def get(self, db: Session, bank_account_id: int) -> Optional[BankAccount]:
        return db.query(BankAccount).filter(
            BankAccount.id == bank_account_id
        ).first()

    def get_by_merchant(
            self,
            db: Session,
            merchant_id: int,
            skip: int = 0,
            limit: int = 100,
            active_only: bool = False
    ) -> List[BankAccount]:
        query = db.query(BankAccount).filter(
            BankAccount.merchant_id == merchant_id
        )

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

    def delete(self, db: Session, bank_account_id: int) -> bool:
        db_bank_account = self.get(db, bank_account_id)
        if not db_bank_account:
            return False

        # Check if bank account is in use by any deals
        # Uncomment when you have deals implemented:
        # if db_bank_account.deals:
        #     raise HTTPException(
        #         status_code=400,
        #         detail="Cannot delete bank account that is associated with deals"
        #     )

        db.delete(db_bank_account)
        db.commit()
        return True

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