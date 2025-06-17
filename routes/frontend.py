# app/routes/frontend.py
from fastapi import APIRouter, Request, Depends, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.crud import merchant as merchant_crud
from app.schemas.merchant import MerchantCreate, MerchantUpdate
from app.database import get_db
from datetime import date
from typing import Optional

# CREATE THE ROUTER HERE
router = APIRouter()

# Set up templates
templates = Jinja2Templates(directory="templates")


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
    merchants = merchant_crud.get_merchants(db)
    return templates.TemplateResponse("components/merchants_table.html", {
        "request": request,
        "merchants": merchants
    })


@router.get("/merchants/new", response_class=HTMLResponse)
def new_merchant_form(request: Request):
    return templates.TemplateResponse("components/merchant_form.html", {
        "request": request
    })


@router.post("/merchants", response_class=HTMLResponse)
def create_merchant(
        request: Request,
        db: Session = Depends(get_db),
        company_name: str = Form(...),
        fein: Optional[str] = Form(None),
        entity_type: Optional[str] = Form(None),
        address: Optional[str] = Form(None),
        city: Optional[str] = Form(None),
        state: Optional[str] = Form(None),
        zip: Optional[str] = Form(None),
        contact_person: Optional[str] = Form(None),
        phone: Optional[str] = Form(None),
        email: Optional[str] = Form(None),
        status: str = Form("lead"),
        submitted_date: Optional[str] = Form(None),
        notes: Optional[str] = Form(None),
):
    try:
        # Convert submitted_date string to date object if provided
        submitted_date_obj = None
        if submitted_date:
            try:
                submitted_date_obj = date.fromisoformat(submitted_date)
            except ValueError:
                pass

        # Create merchant data
        merchant_data = MerchantCreate(
            company_name=company_name,
            fein=fein if fein else None,
            entity_type=entity_type if entity_type else None,
            address=address if address else None,
            city=city if city else None,
            state=state if state else None,
            zip=zip if zip else None,
            contact_person=contact_person if contact_person else None,
            phone=phone if phone else None,
            email=email if email else None,
            status=status,
            submitted_date=submitted_date_obj,
            notes=notes if notes else None,
        )

        # Create the merchant
        merchant = merchant_crud.create_merchant(db, merchant_data)

        return """
        <div style="padding: 1rem; background: var(--success); color: white; border-radius: 6px; margin-bottom: 1rem;">
            ✅ Merchant created successfully!
        </div>
        <script>
            setTimeout(() => {
                document.getElementById('modal-container').innerHTML = '';
                htmx.ajax('GET', '/merchants/table', {target: '#merchants-table'});
            }, 1000);
        </script>
        """

    except Exception as e:
        return f"""
        <div style="padding: 1rem; background: var(--danger); color: white; border-radius: 6px; margin-bottom: 1rem;">
            ❌ Error creating merchant: {str(e)}
        </div>
        """