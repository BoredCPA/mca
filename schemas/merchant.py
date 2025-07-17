# app/schemas/merchant.py - Fixed phone field validation
from pydantic import BaseModel, EmailStr, validator, Field, field_validator
from typing import Optional, List
from datetime import date, datetime
import re


class MerchantBase(BaseModel):
    company_name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Company legal name"
    )
    address: Optional[str] = Field(
        None,
        max_length=500,
        description="Street address"
    )
    city: Optional[str] = Field(
        None,
        min_length=2,
        max_length=100,
        description="City name"
    )
    state: Optional[str] = Field(
        None,
        min_length=2,
        max_length=2,
        description="State abbreviation (e.g., NY, CA)"
    )
    zip: Optional[str] = Field(
        None,
        description="ZIP code"
    )
    fein: Optional[str] = Field(
        None,
        description="Federal Employer Identification Number"
    )
    phone: Optional[str] = Field(
        None,
        description="Phone number"
    )
    entity_type: Optional[str] = Field(
        None,
        description="Business entity type"
    )
    submitted_date: Optional[date] = Field(
        None,
        description="Application submission date"
    )
    email: Optional[EmailStr] = Field(
        None,
        description="Primary contact email"
    )
    contact_person: Optional[str] = Field(
        None,
        min_length=2,
        max_length=255,
        description="Primary contact name"
    )
    status: Optional[str] = Field(
        "lead",
        description="Merchant status in pipeline"
    )
    notes: Optional[str] = Field(
        None,
        max_length=5000,
        description="Internal notes"
    )

    # Backend-only validators - focus on business rules and data integrity
    @field_validator('company_name')
    def validate_company_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Company name cannot be empty')
        # Clean up whitespace
        v = ' '.join(v.split())
        # Basic length check (business rule)
        if len(v) < 2:
            raise ValueError('Company name must be at least 2 characters')
        return v

    @field_validator('state')
    def validate_state(cls, v):
        if v is None or v == "":
            return None
        # Normalize and validate state code (business rule)
        v = v.upper().strip()
        valid_states = [
            'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
            'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
            'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
            'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
            'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY',
            'DC', 'PR', 'VI', 'GU', 'AS', 'MP'  # Include territories
        ]
        if v not in valid_states:
            raise ValueError('Invalid state code')
        return v

    @field_validator('zip')
    def validate_zip(cls, v):
        if v is None or v == "":
            return None
        # Basic sanitization - store clean digits only
        cleaned = re.sub(r'[\s-]', '', v.strip())
        # Basic validation - ensure it's numeric
        if not cleaned.isdigit():
            raise ValueError('ZIP code must contain only digits')
        # Length validation (business rule)
        if len(cleaned) not in [5, 9]:
            raise ValueError('ZIP code must be 5 or 9 digits')
        return cleaned

    @field_validator('fein')
    def validate_fein(cls, v):
        if v is None or v == "":
            return None
        # Clean and validate FEIN (business rule)
        cleaned = re.sub(r'[\s-]', '', v.strip())
        if not re.match(r'^\d{9}$', cleaned):
            raise ValueError('FEIN must be exactly 9 digits')
        return cleaned

    @field_validator('phone')
    def validate_phone(cls, v):
        # Handle empty string from frontend - convert to None
        if v is None or v == "" or not v.strip():
            return None
        # Clean phone number - store digits only
        digits = re.sub(r'\D', '', v)
        # If no digits after cleaning, return None
        if not digits:
            return None
        # Validate length (business rule)
        if len(digits) == 11 and digits[0] == '1':
            digits = digits[1:]  # Remove country code
        if len(digits) != 10:
            raise ValueError('Phone number must be exactly 10 digits')
        return digits

    @field_validator('entity_type')
    def validate_entity_type(cls, v):
        if v is None or v == "":
            return None
        # Business rule validation
        valid_types = [
            'LLC', 'Corporation', 'S-Corp', 'C-Corp',
            'Partnership', 'Sole Proprietorship', 'LLP',
            'Non-Profit', 'Other'
        ]
        if v not in valid_types:
            raise ValueError(f'Invalid entity type. Must be one of: {", ".join(valid_types)}')
        return v

    @field_validator('status')
    def validate_status(cls, v):
        if v is None or v == "":
            return 'lead'
        # Workflow integrity validation (critical business rule)
        valid_statuses = [
            'lead', 'prospect', 'application_sent', 'application_received',
            'in_underwriting', 'approved', 'declined', 'funded', 'renewed',
            'churned', 'blacklisted'
        ]
        if v not in valid_statuses:
            raise ValueError(f'Invalid status. Must be one of: {", ".join(valid_statuses)}')
        return v

    @field_validator('submitted_date')
    def validate_submitted_date(cls, v):
        if v is None:
            return v
        # Business rule: prevent future dates (data integrity)
        if v > date.today():
            raise ValueError('Submitted date cannot be in the future')
        # Business rule: prevent unrealistic past dates
        if v.year < 2000:
            raise ValueError('Submitted date cannot be before year 2000')
        return v

    @field_validator('email')
    def validate_email_security(cls, v):
        if v is None:
            return v
        # Security validation: block disposable emails (anti-fraud)
        email_lower = v.lower()
        disposable_domains = [
            'tempmail.com', 'throwaway.email', 'guerrillamail.com',
            'mailinator.com', '10minutemail.com', 'temp-mail.org',
            'dispostable.com', 'yopmail.com', 'maildrop.cc'
        ]
        domain = email_lower.split('@')[-1]
        if domain in disposable_domains:
            raise ValueError('Disposable email addresses are not allowed')
        return v

    @field_validator('contact_person')
    def validate_contact_person(cls, v):
        if v is None or v == "":
            return None
        # Basic data cleaning
        v = ' '.join(v.split())
        # Minimum business requirement
        if len(v) < 2:
            raise ValueError('Contact person name must be at least 2 characters')
        return v

    @field_validator('city')
    def validate_city(cls, v):
        if v is None or v == "":
            return None
        # Basic data cleaning
        v = ' '.join(v.split())
        # Minimum business requirement
        if len(v) < 2:
            raise ValueError('City name must be at least 2 characters')
        return v

    @field_validator('address')
    def validate_address(cls, v):
        if v is None or v == "":
            return None
        # Basic data cleaning
        v = ' '.join(v.split())
        return v if v else None

    @field_validator('notes')
    def validate_notes(cls, v):
        if v is None or v == "":
            return None
        return v


class MerchantCreate(MerchantBase):
    # Additional validation for creation
    @field_validator('company_name')
    def company_name_required(cls, v):
        if not v:
            raise ValueError('Company name is required')
        return v


class MerchantUpdate(BaseModel):
    company_name: Optional[str] = Field(None, min_length=2, max_length=255)
    address: Optional[str] = Field(None, max_length=500)
    city: Optional[str] = Field(None, min_length=2, max_length=100)
    state: Optional[str] = Field(None, min_length=2, max_length=2)
    zip: Optional[str] = None
    fein: Optional[str] = None
    phone: Optional[str] = None
    entity_type: Optional[str] = None
    submitted_date: Optional[date] = None
    email: Optional[EmailStr] = None
    contact_person: Optional[str] = Field(None, min_length=2, max_length=255)
    status: Optional[str] = None
    notes: Optional[str] = Field(None, max_length=5000)

    # Copy validators from MerchantBase - using the old validator syntax for compatibility
    _validate_company_name = validator('company_name', allow_reuse=True)(
        MerchantBase.validate_company_name
    )
    _validate_state = validator('state', allow_reuse=True)(
        MerchantBase.validate_state
    )
    _validate_zip = validator('zip', allow_reuse=True)(
        MerchantBase.validate_zip
    )
    _validate_fein = validator('fein', allow_reuse=True)(
        MerchantBase.validate_fein
    )
    _validate_phone = validator('phone', allow_reuse=True)(
        MerchantBase.validate_phone
    )
    _validate_entity_type = validator('entity_type', allow_reuse=True)(
        MerchantBase.validate_entity_type
    )
    _validate_status = validator('status', allow_reuse=True)(
        MerchantBase.validate_status
    )
    _validate_submitted_date = validator('submitted_date', allow_reuse=True)(
        MerchantBase.validate_submitted_date
    )
    _validate_email = validator('email', allow_reuse=True)(
        MerchantBase.validate_email_security
    )
    _validate_contact_person = validator('contact_person', allow_reuse=True)(
        MerchantBase.validate_contact_person
    )
    _validate_city = validator('city', allow_reuse=True)(
        MerchantBase.validate_city
    )
    _validate_address = validator('address', allow_reuse=True)(
        MerchantBase.validate_address
    )
    _validate_notes = validator('notes', allow_reuse=True)(
        MerchantBase.validate_notes
    )


class Merchant(MerchantBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Response models
class MerchantListResponse(BaseModel):
    merchants: List[Merchant]
    total: int
    page: int
    per_page: int


class ValidationErrorDetail(BaseModel):
    field: str
    message: str
    type: str


class ValidationErrorResponse(BaseModel):
    detail: str = "Validation error"
    errors: List[ValidationErrorDetail]