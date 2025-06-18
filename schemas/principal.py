# app/schemas/principal.py
from pydantic import BaseModel, Field, validator, root_validator
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
import re


class PrincipalBase(BaseModel):
    merchant_id: int = Field(..., gt=0)
    first_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Principal's first name"
    )
    last_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Principal's last name"
    )
    title: Optional[str] = Field(
        None,
        max_length=100,
        description="Title/Position (CEO, President, Owner, etc.)"
    )
    ownership_percentage: Optional[Decimal] = Field(
        100.00,
        ge=0,
        le=100,
        decimal_places=2,
        description="Ownership percentage (0-100)"
    )
    ssn: Optional[str] = Field(
        None,
        regex="^\\d{3}-\\d{2}-\\d{4}$",
        description="Social Security Number (XXX-XX-XXXX)"
    )
    date_of_birth: Optional[date] = Field(
        None,
        description="Date of birth"
    )
    home_address: Optional[str] = Field(
        None,
        max_length=500,
        description="Home street address"
    )
    city: Optional[str] = Field(
        None,
        min_length=2,
        max_length=100,
        description="City"
    )
    state: Optional[str] = Field(
        None,
        regex="^[A-Z]{2}$",
        description="Two-letter state code"
    )
    zip: Optional[str] = Field(
        None,
        regex="^\\d{5}(-\\d{4})?$",
        description="ZIP code"
    )
    phone: Optional[str] = Field(
        None,
        regex="^\\+?1?\\d{10,14}$",
        description="Phone number"
    )
    email: Optional[str] = Field(
        None,
        max_length=255,
        description="Email address"
    )
    is_primary_contact: Optional[bool] = Field(
        False,
        description="Is this the primary contact for the merchant?"
    )
    is_guarantor: Optional[bool] = Field(
        True,
        description="Is this principal a guarantor?"
    )

    # Validators
    @validator('first_name', 'last_name')
    def validate_name(cls, v):
        if v:
            # Remove extra whitespace
            v = ' '.join(v.split())
            # Check for valid characters
            if not re.match(r"^[a-zA-Z\s\-'.]+$", v):
                raise ValueError('Name can only contain letters, spaces, hyphens, and apostrophes')
        return v

    @validator('title')
    def validate_title(cls, v):
        if v:
            # Normalize common titles
            title_map = {
                'ceo': 'CEO',
                'cfo': 'CFO',
                'coo': 'COO',
                'cto': 'CTO',
                'president': 'President',
                'vice president': 'Vice President',
                'vp': 'VP',
                'owner': 'Owner',
                'partner': 'Partner',
                'member': 'Member',
                'manager': 'Manager',
                'managing member': 'Managing Member',
                'managing partner': 'Managing Partner',
            }
            v_lower = v.lower().strip()
            if v_lower in title_map:
                v = title_map[v_lower]
        return v

    @validator('ssn')
    def validate_ssn(cls, v):
        if v:
            # Remove any non-numeric characters
            cleaned = re.sub(r'[^0-9]', '', v)
            if len(cleaned) != 9:
                raise ValueError('SSN must contain exactly 9 digits')
            # Format as XXX-XX-XXXX
            v = f"{cleaned[:3]}-{cleaned[3:5]}-{cleaned[5:]}"
            # Basic validation - not all zeros
            if cleaned == '000000000':
                raise ValueError('Invalid SSN')
            # First three digits can't be 000, 666, or 900-999
            first_three = int(cleaned[:3])
            if first_three == 0 or first_three == 666 or first_three >= 900:
                raise ValueError('Invalid SSN')
        return v

    @validator('date_of_birth')
    def validate_date_of_birth(cls, v):
        if v:
            # Must be at least 18 years old
            today = date.today()
            age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
            if age < 18:
                raise ValueError('Principal must be at least 18 years old')
            # Can't be more than 100 years old
            if age > 100:
                raise ValueError('Invalid date of birth')
        return v

    @validator('state')
    def validate_state(cls, v):
        if v:
            v = v.upper()
            valid_states = [
                'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'DC', 'FL',
                'GA', 'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME',
                'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH',
                'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI',
                'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY'
            ]
            if v not in valid_states:
                raise ValueError(f'Invalid state code')
        return v

    @validator('zip')
    def validate_zip(cls, v):
        if v:
            # Remove any spaces
            v = v.replace(' ', '')
        return v

    @validator('phone')
    def validate_phone(cls, v):
        if v:
            # Remove all non-numeric characters
            cleaned = re.sub(r'[^0-9]', '', v)
            if len(cleaned) == 10:
                v = f"+1{cleaned}"
            elif len(cleaned) == 11 and cleaned[0] == '1':
                v = f"+{cleaned}"
            else:
                v = f"+{cleaned}"
        return v

    @validator('email')
    def validate_email(cls, v):
        if v:
            # Basic email validation
            if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', v):
                raise ValueError('Invalid email format')
            v = v.lower()
        return v

    @root_validator
    def validate_address_completeness(cls, values):
        # If any address field is provided, require city and state
        address = values.get('home_address')
        city = values.get('city')
        state = values.get('state')

        if address and not (city and state):
            raise ValueError('If home address is provided, city and state are required')

        return values


class PrincipalCreate(PrincipalBase):
    pass


class PrincipalUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    title: Optional[str] = Field(None, max_length=100)
    ownership_percentage: Optional[Decimal] = Field(None, ge=0, le=100, decimal_places=2)
    ssn: Optional[str] = Field(None, regex="^\\d{3}-\\d{2}-\\d{4}$")
    date_of_birth: Optional[date] = None
    home_address: Optional[str] = Field(None, max_length=500)
    city: Optional[str] = Field(None, min_length=2, max_length=100)
    state: Optional[str] = Field(None, regex="^[A-Z]{2}$")
    zip: Optional[str] = Field(None, regex="^\\d{5}(-\\d{4})?$")
    phone: Optional[str] = Field(None, regex="^\\+?1?\\d{10,14}$")
    email: Optional[str] = Field(None, max_length=255)
    is_primary_contact: Optional[bool] = None
    is_guarantor: Optional[bool] = None

    # Reuse validators from base class
    _validate_name = validator('first_name', 'last_name', allow_reuse=True)(PrincipalBase.validate_name)
    _validate_title = validator('title', allow_reuse=True)(PrincipalBase.validate_title)
    _validate_ssn = validator('ssn', allow_reuse=True)(PrincipalBase.validate_ssn)
    _validate_date_of_birth = validator('date_of_birth', allow_reuse=True)(PrincipalBase.validate_date_of_birth)
    _validate_state = validator('state', allow_reuse=True)(PrincipalBase.validate_state)
    _validate_zip = validator('zip', allow_reuse=True)(PrincipalBase.validate_zip)
    _validate_phone = validator('phone', allow_reuse=True)(PrincipalBase.validate_phone)
    _validate_email = validator('email', allow_reuse=True)(PrincipalBase.validate_email)


class Principal(PrincipalBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PrincipalListResponse(BaseModel):
    principals: List[Principal]
    total: int
    merchant_id: Optional[int] = None