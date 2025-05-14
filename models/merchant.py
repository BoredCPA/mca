from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import date

class Merchant(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    company_name: str
    address: str
    fein: str
    entity_type: str
    submitted_date: Optional[date] = None
