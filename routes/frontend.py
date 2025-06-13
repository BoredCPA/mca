# app/routes/frontend.py
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.crud import merchant as merchant_crud
from app.database import SessionLocal

router = APIRouter()
templates = Jinja2Templates(directory="templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@router.get("/merchants", response_class=HTMLResponse)
def merchants_page(request: Request, db: Session = Depends(get_db)):
    merchants = merchant_crud.get_merchants(db)
    return templates.TemplateResponse("merchants.html", {
        "request": request, 
        "merchants": merchants
    })

@router.get("/merchants/table", response_class=HTMLResponse)
def merchants_table(request: Request, db: Session = Depends(get_db)):
    """HTMX endpoint to load just the merchants table"""
    merchants = merchant_crud.get_merchants(db)
    return templates.TemplateResponse("components/merchants_table.html", {
        "request": request, 
        "merchants": merchants
    })