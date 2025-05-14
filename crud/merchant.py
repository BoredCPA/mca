from sqlmodel import Session, select
from models.merchant import Merchant
from database import engine

def create_merchant(merchant: Merchant) -> Merchant:
    with Session(engine) as session:
        session.add(merchant)
        session.commit()
        session.refresh(merchant)
        return merchant

def get_merchant(id: int) -> Merchant | None:
    with Session(engine) as session:
        return session.get(Merchant, id)

def get_all_merchants() -> list[Merchant]:
    with Session(engine) as session:
        return session.exec(select(Merchant)).all()

def update_merchant(id: int, updated_data: dict) -> Merchant | None:
    with Session(engine) as session:
        merchant = session.get(Merchant, id)
        if not merchant:
            return None
        for key, value in updated_data.items():
            setattr(merchant, key, value)
        session.commit()
        session.refresh(merchant)
        return merchant

def delete_merchant(id: int) -> bool:
    with Session(engine) as session:
        merchant = session.get(Merchant, id)
        if not merchant:
            return False
        session.delete(merchant)
        session.commit()
        return True
