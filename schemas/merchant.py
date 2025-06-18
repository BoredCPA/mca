# app/schemas/merchant.py - Enhanced with comprehensive validation
from pydantic import BaseModel, EmailStr, validator, Field
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
        description="ZIP code (5 or 9 digits)"
    )
    fein: Optional[str] = Field(
        None,
        description="Federal Employer Identification Number (XX-XXXXXXX)"
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

    # Validators
    @validator('company_name')
    def validate_company_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Company name cannot be empty')
        # Remove extra whitespace
        v = ' '.join(v.split())
        # Check for minimum meaningful length
        if len(v) < 2:
            raise ValueError('Company name must be at least 2 characters')
        # Check for suspicious patterns (all numbers, special chars only)
        if not re.search(r'[a-zA-Z]', v):
            raise ValueError('Company name must contain at least one letter')
        return v

    @validator('state')
    def validate_state(cls, v):
        if v is None:
            return v
        # Uppercase and validate state code
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
            raise ValueError(f'Invalid state code. Must be one of: {", ".join(valid_states)}')
        return v

    @validator('zip')
    def validate_zip(cls, v):
        if v is None:
            return v
        # Remove any spaces or dashes
        v = re.sub(r'[\s-]', '', v.strip())
        # Validate ZIP format (5 digits or 9 digits)
        if not re.match(r'^\d{5}(\d{4})?$', v):
            raise ValueError('ZIP code must be 5 or 9 digits (e.g., 12345 or 123456789)')
        # Format with dash if 9 digits
        if len(v) == 9:
            v = f"{v[:5]}-{v[5:]}"
        return v

    @validator('fein')
    def validate_fein(cls, v):
        if v is None:
            return v
        # Remove any spaces or dashes
        cleaned = re.sub(r'[\s-]', '', v.strip())
        # Validate FEIN format (9 digits)
        if not re.match(r'^\d{9}$', cleaned):
            raise ValueError('FEIN must be 9 digits (XX-XXXXXXX format)')
        # Format as XX-XXXXXXX
        return f"{cleaned[:2]}-{cleaned[2:]}"

    @validator('phone')
    def validate_phone(cls, v):
        if v is None:
            return v
        # Remove all non-digit characters
        digits = re.sub(r'\D', '', v)
        # Check length
        if len(digits) == 10:
            # Format as (XXX) XXX-XXXX
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        elif len(digits) == 11 and digits[0] == '1':
            # Remove country code and format
            digits = digits[1:]
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        else:
            raise ValueError('Phone number must be 10 digits')

    @validator('entity_type')
    def validate_entity_type(cls, v):
        if v is None:
            return v
        valid_types = [
            'LLC', 'Corporation', 'S-Corp', 'C-Corp',
            'Partnership', 'Sole Proprietorship', 'LLP',
            'Non-Profit', 'Other'
        ]
        if v not in valid_types:
            raise ValueError(f'Invalid entity type. Must be one of: {", ".join(valid_types)}')
        return v

    @validator('status')
    def validate_status(cls, v):
        if v is None:
            return 'lead'
        valid_statuses = [
            'lead', 'prospect', 'application_sent', 'application_received',
            'in_underwriting', 'approved', 'declined', 'funded', 'renewed',
            'churned', 'blacklisted'
        ]
        if v not in valid_statuses:
            raise ValueError(f'Invalid status. Must be one of: {", ".join(valid_statuses)}')
        return v

    @validator('submitted_date')
    def validate_submitted_date(cls, v):
        if v is None:
            return v
        # Don't allow future dates
        if v > date.today():
            raise ValueError('Submitted date cannot be in the future')
        # Don't allow dates too far in the past (e.g., before 2000)
        if v.year < 2000:
            raise ValueError('Submitted date seems too far in the past')
        return v

    @validator('email')
    def validate_email_format(cls, v):
        if v is None:
            return v
        # Additional email validation beyond EmailStr
        # Check for common typos
        email_lower = v.lower()
        if email_lower.endswith(('.con', '.cm', '.co', '.vom')):
            raise ValueError('Email domain appears to have a typo')
        # Check for disposable email domains (add more as needed)
        disposable_domains = [
            'tempmail.com', 'throwaway.email', 'guerrillamail.com',
            'mailinator.com', '10minutemail.com'
        ]
        domain = email_lower.split('@')[-1]
        if domain in disposable_domains:
            raise ValueError('Disposable email addresses are not allowed')
        return v

    @validator('contact_person')
    def validate_contact_person(cls, v):
        if v is None:
            return v
        # Clean up whitespace
        v = ' '.join(v.split())
        # Check for minimum meaningful length
        if len(v) < 2:
            raise ValueError('Contact person name must be at least 2 characters')
        # Check that it contains at least one letter
        if not re.search(r'[a-zA-Z]', v):
            raise ValueError('Contact person name must contain letters')
        # Check for obvious test data
        test_names = ['test', 'testing', 'asdf', 'qwerty', 'xxx', 'na', 'n/a']
        if v.lower() in test_names:
            raise ValueError('Please provide a valid contact person name')
        return v

    @validator('city')
    def validate_city(cls, v):
        if v is None:
            return v
        # Clean up whitespace
        v = ' '.join(v.split())
        # Check for minimum length
        if len(v) < 2:
            raise ValueError('City name must be at least 2 characters')
        # Check that it contains letters
        if not re.search(r'[a-zA-Z]', v):
            raise ValueError('City name must contain letters')
        return v


class MerchantCreate(MerchantBase):
    # Additional validation for creation
    @validator('company_name')
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

    # Copy validators from MerchantBase
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
        MerchantBase.validate_email_format
    )
    _validate_contact_person = validator('contact_person', allow_reuse=True)(
        MerchantBase.validate_contact_person
    )
    _validate_city = validator('city', allow_reuse=True)(
        MerchantBase.validate_city
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