# app/schemas/principal.py
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
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
    ownership_percentage: Optional[Decimal] = Field(
        default=100.00,
        ge=0,
        le=100,
        max_digits=5,
        decimal_places=2,
        description="Ownership percentage (0-100)"
    )
    ssn: Optional[str] = Field(
        None,
        min_length=11,
        max_length=11,
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
        min_length=2,
        max_length=2,
        description="Two-letter state code"
    )
    zip: Optional[str] = Field(
        None,
        min_length=5,
        max_length=10,
        description="ZIP code (XXXXX or XXXXX-XXXX)"
    )
    phone: Optional[str] = Field(
        None,
        min_length=10,
        max_length=15,
        description="Phone number"
    )
    email: Optional[str] = Field(
        None,
        max_length=255,
        description="Email address"
    )
    is_primary_contact: bool = Field(
        default=False,
        description="Is this the primary contact for the merchant?"
    )
    is_guarantor: bool = Field(
        default=True,
        description="Is this principal a guarantor?"
    )

    # Validators
    @field_validator('first_name', 'last_name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if v:
            # Remove extra whitespace and strip
            v = ' '.join(v.split()).strip()
            # Check for valid characters
            if not re.match(r"^[a-zA-Z\s\-'.]+$", v):
                raise ValueError('Name can only contain letters, spaces, hyphens, and apostrophes')
            # Check for minimum meaningful length
            if len(v.replace(' ', '').replace('-', '').replace("'", '').replace('.', '')) < 1:
                raise ValueError('Name must contain at least one letter')
        return v

    @field_validator('ssn')
    @classmethod
    def validate_ssn(cls, v: Optional[str]) -> Optional[str]:
        if v:
            # Remove any non-numeric characters
            cleaned = re.sub(r'[^0-9]', '', v)
            if len(cleaned) != 9:
                raise ValueError('SSN must contain exactly 9 digits')

            # Format as XXX-XX-XXXX
            formatted_ssn = f"{cleaned[:3]}-{cleaned[3:5]}-{cleaned[5:]}"

            # Validate SSN rules
            # First three digits can't be 000, 666, or 900-999
            first_three = int(cleaned[:3])
            if first_three == 0 or first_three == 666 or first_three >= 900:
                raise ValueError('Invalid SSN: Invalid area number')

            # Middle two digits can't be 00
            if cleaned[3:5] == '00':
                raise ValueError('Invalid SSN: Invalid group number')

            # Last four digits can't be 0000
            if cleaned[5:] == '0000':
                raise ValueError('Invalid SSN: Invalid serial number')

            return formatted_ssn
        return v

    @field_validator('date_of_birth')
    @classmethod
    def validate_date_of_birth(cls, v: Optional[date]) -> Optional[date]:
        if v:
            # Must be at least 18 years old
            today = date.today()
            age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
            if age < 18:
                raise ValueError('Principal must be at least 18 years old')
            # Can't be born in the future
            if v > today:
                raise ValueError('Date of birth cannot be in the future')
            # Reasonable age limit (e.g., 120 years)
            if age > 120:
                raise ValueError('Invalid date of birth: unrealistic age')
        return v

    @field_validator('state')
    @classmethod
    def validate_state(cls, v: Optional[str]) -> Optional[str]:
        if v:
            v = v.upper().strip()
            valid_states = {
                'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'DC', 'FL',
                'GA', 'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME',
                'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH',
                'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI',
                'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI',
                'WY', 'PR', 'VI', 'GU', 'AS', 'MP'  # Include territories
            }
            if v not in valid_states:
                raise ValueError(f'Invalid state code: {v}')
        return v

    @field_validator('zip')
    @classmethod
    def validate_zip(cls, v: Optional[str]) -> Optional[str]:
        if v:
            # Remove any spaces or hyphens for validation
            cleaned = re.sub(r'[^0-9]', '', v)

            # Must be either 5 or 9 digits
            if len(cleaned) not in [5, 9]:
                raise ValueError('ZIP code must be 5 digits (XXXXX) or 9 digits (XXXXX-XXXX)')

            # Format appropriately
            if len(cleaned) == 5:
                return cleaned
            else:
                return f"{cleaned[:5]}-{cleaned[5:]}"
        return v

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v:
            # Remove all non-numeric characters
            cleaned = re.sub(r'[^0-9]', '', v)

            # Handle different phone formats
            if len(cleaned) == 10:
                # US number without country code
                return f"+1{cleaned}"
            elif len(cleaned) == 11 and cleaned[0] == '1':
                # US number with country code
                return f"+{cleaned}"
            elif 10 <= len(cleaned) <= 15:
                # International number
                return f"+{cleaned}"
            else:
                raise ValueError('Phone number must be 10-15 digits')
        return v

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v:
            v = v.lower().strip()
            # More comprehensive email validation
            email_pattern = re.compile(
                r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            )
            if not email_pattern.match(v):
                raise ValueError('Invalid email format')

            # Additional checks
            if '..' in v:
                raise ValueError('Email cannot contain consecutive dots')
            if v.startswith('.') or v.endswith('.'):
                raise ValueError('Email cannot start or end with a dot')

            # Check domain has at least one dot after @
            domain = v.split('@')[1]
            if '.' not in domain:
                raise ValueError('Email domain must contain at least one dot')

        return v

    @model_validator(mode='after')
    def validate_address_completeness(self):
        """If any address field is provided, require city, state, and zip"""
        address = self.home_address
        city = self.city
        state = self.state
        zip_code = self.zip

        address_fields = [address, city, state, zip_code]
        provided_fields = [f for f in address_fields if f is not None]

        if provided_fields and len(provided_fields) < 4:
            raise ValueError(
                'If any address field is provided, all address fields '
                '(home_address, city, state, zip) are required'
            )

        return self

    @model_validator(mode='after')
    def validate_primary_contact_requirements(self):
        """Primary contacts must have email and phone"""
        if self.is_primary_contact and not (self.email and self.phone):
            raise ValueError('Primary contacts must have both email and phone number')
        return self


class PrincipalCreate(PrincipalBase):
    pass


class PrincipalUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    ownership_percentage: Optional[Decimal] = Field(
        None,
        ge=0,
        le=100,
        max_digits=5,
        decimal_places=2
    )
    ssn: Optional[str] = Field(None, min_length=11, max_length=11)
    date_of_birth: Optional[date] = None
    home_address: Optional[str] = Field(None, max_length=500)
    city: Optional[str] = Field(None, min_length=2, max_length=100)
    state: Optional[str] = Field(None, min_length=2, max_length=2)
    zip: Optional[str] = Field(None, min_length=5, max_length=10)
    phone: Optional[str] = Field(None, min_length=10, max_length=15)
    email: Optional[str] = Field(None, max_length=255)
    is_primary_contact: Optional[bool] = None
    is_guarantor: Optional[bool] = None

    # Apply the same validators as PrincipalBase
    _validate_name = field_validator('first_name', 'last_name')(PrincipalBase.validate_name)
    _validate_ssn = field_validator('ssn')(PrincipalBase.validate_ssn)
    _validate_date_of_birth = field_validator('date_of_birth')(PrincipalBase.validate_date_of_birth)
    _validate_state = field_validator('state')(PrincipalBase.validate_state)
    _validate_zip = field_validator('zip')(PrincipalBase.validate_zip)
    _validate_phone = field_validator('phone')(PrincipalBase.validate_phone)
    _validate_email = field_validator('email')(PrincipalBase.validate_email)

    @model_validator(mode='after')
    def validate_partial_address_update(self):
        """For updates, if any address field is provided, validate completeness"""
        address_fields = {
            'home_address': self.home_address,
            'city': self.city,
            'state': self.state,
            'zip': self.zip
        }

        # Filter out None values to see what's being updated
        updating_fields = {k: v for k, v in address_fields.items() if v is not None}

        # If updating any address field, warn about incomplete address
        # Note: This is less strict than create since it's a partial update
        if updating_fields and len(updating_fields) < 4:
            # This is a warning, not an error for updates
            # You might want to log this or handle it differently
            pass

        return self


class Principal(PrincipalBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PrincipalListResponse(BaseModel):
    principals: List[Principal]
    total: int
    merchant_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)