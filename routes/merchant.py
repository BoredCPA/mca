from fastapi import APIRouter, HTTPException
from models.merchant import Merchant
from crud import merchant as crud

router = APIRouter(prefix="/merchants", tags=["Merchants"])

@router.post("/", response_model=Merchant)
def create(merchant: Merchant):
    return crud.create_merchant(merchant)

@router.get("/{merchant_id}", response_model=Merchant)
def read(merchant_id: int):
    merchant = crud.get_merchant(merchant_id)
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    return merchant

@router.get("/", response_model=list[Merchant])
def read_all():
    return crud.get_all_merchants()

@router.put("/{merchant_id}", response_model=Merchant)
def update(merchant_id: int, updated: dict):
    merchant = crud.update_merchant(merchant_id, updated)
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    return merchant

@router.delete("/{merchant_id}")
def delete(merchant_id: int):
    success = crud.delete_merchant(merchant_id)
    if not success:
        raise HTTPException(status_code=404, detail="Merchant not found")
    return {"ok": True}
