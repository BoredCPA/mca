# app/tests/unit/test_schemas/test_merchant_schema.py
import pytest
from pydantic import ValidationError
from app.schemas.merchant import MerchantCreate, MerchantUpdate
from datetime import date


class TestMerchantSchema:
    """Test Merchant schema validations"""

    def test_valid_merchant_create(self):
        """Test creating valid merchant schema"""
        data = {
            "company_name": "Test Company LLC",
            "fein": "123456789",
            "status": "lead"
        }
        merchant = MerchantCreate(**data)

        assert merchant.company_name == "Test Company LLC"
        assert merchant.fein == "123456789"
        assert merchant.status == "lead"

    def test_company_name_validation(self):
        """Test company name validation rules"""
        # Too short
        with pytest.raises(ValidationError) as exc_info:
            MerchantCreate(company_name="A")
        assert "at least 2 characters" in str(exc_info.value)

        # Empty string
        with pytest.raises(ValidationError) as exc_info:
            MerchantCreate(company_name="")
        assert "at least 2 characters" in str(exc_info.value)

        # Valid with extra spaces (should be cleaned)
        merchant = MerchantCreate(company_name="  Test   Company  ")
        assert merchant.company_name == "Test Company"

    def test_fein_validation(self):
        """Test FEIN validation"""
        # Valid FEIN
        merchant = MerchantCreate(company_name="Test", fein="123456789")
        assert merchant.fein == "123456789"

        # Valid with dashes (should be cleaned)
        merchant = MerchantCreate(company_name="Test", fein="12-3456789")
        assert merchant.fein == "123456789"

        # Invalid - too short
        with pytest.raises(ValidationError) as exc_info:
            MerchantCreate(company_name="Test", fein="12345678")
        assert "exactly 9 digits" in str(exc_info.value)

        # Invalid - too long
        with pytest.raises(ValidationError):
            MerchantCreate(company_name="Test", fein="1234567890")

    def test_state_validation(self):
        """Test state code validation"""
        # Valid state
        merchant = MerchantCreate(company_name="Test", state="NY")
        assert merchant.state == "NY"

        # Valid lowercase (should be uppercase)
        merchant = MerchantCreate(company_name="Test", state="ca")
        assert merchant.state == "CA"

        # Invalid state
        with pytest.raises(ValidationError) as exc_info:
            MerchantCreate(company_name="Test", state="ZZ")
        assert "Invalid state code" in str(exc_info.value)

    def test_zip_validation(self):
        """Test ZIP code validation"""
        # Valid 5-digit
        merchant = MerchantCreate(company_name="Test", zip="10001")
        assert merchant.zip == "10001"

        # Valid 9-digit
        merchant = MerchantCreate(company_name="Test", zip="100011234")
        assert merchant.zip == "100011234"

        # Valid with dash (should be cleaned)
        merchant = MerchantCreate(company_name="Test", zip="10001-1234")
        assert merchant.zip == "100011234"

        # Invalid - letters
        with pytest.raises(ValidationError):
            MerchantCreate(company_name="Test", zip="ABCDE")

        # Invalid - wrong length
        with pytest.raises(ValidationError):
            MerchantCreate(company_name="Test", zip="1234")

    def test_phone_validation(self):
        """Test phone number validation"""
        # Valid 10-digit
        merchant = MerchantCreate(company_name="Test", phone="2125551234")
        assert merchant.phone == "2125551234"

        # Valid with formatting (should be cleaned)
        merchant = MerchantCreate(company_name="Test", phone="(212) 555-1234")
        assert merchant.phone == "2125551234"

        # Valid with country code
        merchant = MerchantCreate(company_name="Test", phone="12125551234")
        assert merchant.phone == "2125551234"

        # Invalid - too short
        with pytest.raises(ValidationError):
            MerchantCreate(company_name="Test", phone="555-1234")

    def test_email_validation(self):
        """Test email validation including security checks"""
        # Valid email
        merchant = MerchantCreate(company_name="Test", email="test@example.com")
        assert merchant.email == "test@example.com"

        # Invalid format
        with pytest.raises(ValidationError):
            MerchantCreate(company_name="Test", email="invalid-email")

        # Disposable email (should fail)
        with pytest.raises(ValidationError) as exc_info:
            MerchantCreate(company_name="Test", email="test@tempmail.com")
        assert "Disposable email" in str(exc_info.value)

    def test_status_validation(self):
        """Test status validation"""
        # Valid statuses
        valid_statuses = ["lead", "prospect", "approved", "declined", "funded"]
        for status in valid_statuses:
            merchant = MerchantCreate(company_name="Test", status=status)
            assert merchant.status == status

        # Invalid status
        with pytest.raises(ValidationError):
            MerchantCreate(company_name="Test", status="invalid_status")

    def test_submitted_date_validation(self):
        """Test submitted date validation"""
        # Valid date
        merchant = MerchantCreate(
            company_name="Test",
            submitted_date=date.today()
        )
        assert merchant.submitted_date == date.today()

        # Future date (should fail)
        from datetime import timedelta
        future_date = date.today() + timedelta(days=1)
        with pytest.raises(ValidationError) as exc_info:
            MerchantCreate(company_name="Test", submitted_date=future_date)
        assert "cannot be in the future" in str(exc_info.value)


class TestPrincipalSchema:
    """Test Principal schema validations"""

    def test_valid_principal_create(self):
        """Test creating valid principal"""
        from app.schemas.principal import PrincipalCreate

        data = {
            "merchant_id": 1,
            "first_name": "John",
            "last_name": "Doe",
            "ownership_percentage": 50.00,
            "ssn": "123-45-6789",
            "date_of_birth": "1980-01-01"
        }
        principal = PrincipalCreate(**data)

        assert principal.first_name == "John"
        assert principal.ownership_percentage == 50.00
        assert principal.ssn == "123-45-6789"

    def test_name_validation(self):
        """Test name validation"""
        from app.schemas.principal import PrincipalCreate

        # Valid names
        principal = PrincipalCreate(
            merchant_id=1,
            first_name="Mary-Jane",
            last_name="O'Brien"
        )
        assert principal.first_name == "Mary-Jane"

        # Invalid - numbers
        with pytest.raises(ValidationError):
            PrincipalCreate(
                merchant_id=1,
                first_name="John123",
                last_name="Doe"
            )

    def test_ssn_validation(self):
        """Test SSN validation"""
        from app.schemas.principal import PrincipalCreate

        # Valid SSN
        principal = PrincipalCreate(
            merchant_id=1,
            first_name="John",
            last_name="Doe",
            ssn="123-45-6789"
        )
        assert principal.ssn == "123-45-6789"

        # Invalid - starts with 000
        with pytest.raises(ValidationError) as exc_info:
            PrincipalCreate(
                merchant_id=1,
                first_name="John",
                last_name="Doe",
                ssn="000-12-3456"
            )
        assert "Invalid area number" in str(exc_info.value)

        # Invalid - middle is 00
        with pytest.raises(ValidationError):
            PrincipalCreate(
                merchant_id=1,
                first_name="John",
                last_name="Doe",
                ssn="123-00-4567"
            )

    def test_age_validation(self):
        """Test age validation (must be 18+)"""
        from app.schemas.principal import PrincipalCreate
        from datetime import timedelta

        # Valid - over 18
        adult_dob = date.today() - timedelta(days=365 * 25)
        principal = PrincipalCreate(
            merchant_id=1,
            first_name="John",
            last_name="Doe",
            date_of_birth=adult_dob
        )
        assert principal.date_of_birth == adult_dob

        # Invalid - under 18
        minor_dob = date.today() - timedelta(days=365 * 17)
        with pytest.raises(ValidationError) as exc_info:
            PrincipalCreate(
                merchant_id=1,
                first_name="John",
                last_name="Doe",
                date_of_birth=minor_dob
            )
        assert "at least 18 years old" in str(exc_info.value)

    def test_ownership_percentage_validation(self):
        """Test ownership percentage validation"""
        from app.schemas.principal import PrincipalCreate

        # Valid percentages
        for pct in [0, 50.50, 100]:
            principal = PrincipalCreate(
                merchant_id=1,
                first_name="John",
                last_name="Doe",
                ownership_percentage=pct
            )
            assert principal.ownership_percentage == pct

        # Invalid - over 100
        with pytest.raises(ValidationError):
            PrincipalCreate(
                merchant_id=1,
                first_name="John",
                last_name="Doe",
                ownership_percentage=101
            )

        # Invalid - negative
        with pytest.raises(ValidationError):
            PrincipalCreate(
                merchant_id=1,
                first_name="John",
                last_name="Doe",
                ownership_percentage=-1
            )

    def test_address_completeness_validation(self):
        """Test address completeness validation"""
        from app.schemas.principal import PrincipalCreate

        # Valid - all address fields
        principal = PrincipalCreate(
            merchant_id=1,
            first_name="John",
            last_name="Doe",
            home_address="123 Main St",
            city="New York",
            state="NY",
            zip="10001"
        )
        assert principal.city == "New York"

        # Invalid - partial address
        with pytest.raises(ValidationError) as exc_info:
            PrincipalCreate(
                merchant_id=1,
                first_name="John",
                last_name="Doe",
                home_address="123 Main St",
                city="New York"
                # Missing state and zip
            )
        assert "all address fields" in str(exc_info.value)

    def test_primary_contact_requirements(self):
        """Test primary contact validation"""
        from app.schemas.principal import PrincipalCreate

        # Valid primary contact
        principal = PrincipalCreate(
            merchant_id=1,
            first_name="John",
            last_name="Doe",
            is_primary_contact=True,
            email="john@example.com",
            phone="2125551234"
        )
        assert principal.is_primary_contact is True

        # Invalid - primary contact without email/phone
        with pytest.raises(ValidationError) as exc_info:
            PrincipalCreate(
                merchant_id=1,
                first_name="John",
                last_name="Doe",
                is_primary_contact=True
                # Missing email and phone
            )
        assert "must have both email and phone" in str(exc_info.value)


class TestOfferSchema:
    """Test Offer schema validations"""

    def test_valid_offer_create(self):
        """Test creating valid offer"""
        from app.schemas.offer import OfferCreate

        data = {
            "merchant_id": 1,
            "advance": 50000.00,
            "factor": 1.3,
            "specified_percentage": 10.0,
            "payment_frequency": "daily",
            "number_of_periods": 100
        }
        offer = OfferCreate(**data)

        assert offer.advance == 50000.00
        assert offer.factor == 1.3
        assert offer.payment_frequency == "daily"

    def test_financial_validations(self):
        """Test financial field validations"""
        from app.schemas.offer import OfferCreate

        # Invalid - negative advance
        with pytest.raises(ValidationError):
            OfferCreate(
                merchant_id=1,
                advance=-1000,
                factor=1.3,
                specified_percentage=10.0
            )

        # Invalid - factor less than 1
        with pytest.raises(ValidationError):
            OfferCreate(
                merchant_id=1,
                advance=10000,
                factor=0.9,
                specified_percentage=10.0
            )

        # Invalid - percentage over 100
        with pytest.raises(ValidationError):
            OfferCreate(
                merchant_id=1,
                advance=10000,
                factor=1.3,
                specified_percentage=101.0
            )


class TestBankAccountSchema:
    """Test BankAccount schema validations"""

    def test_valid_bank_account_create(self):
        """Test creating valid bank account"""
        from app.schemas.banking import BankAccountCreate

        data = {
            "account_name": "Business Checking",
            "account_number": "1234",
            "routing_number": "123456789",
            "bank_name": "Test Bank",
            "account_type": "checking"
        }
        account = BankAccountCreate(**data)

        assert account.account_number == "1234"
        assert account.routing_number == "123456789"

    def test_account_number_validation(self):
        """Test account number validation (last 4 digits)"""
        from app.schemas.banking import BankAccountCreate

        # Valid
        account = BankAccountCreate(
            account_name="Test",
            account_number="1234",
            routing_number="123456789",
            bank_name="Bank",
            account_type="checking"
        )
        assert account.account_number == "1234"

        # Invalid - not digits
        with pytest.raises(ValidationError):
            BankAccountCreate(
                account_name="Test",
                account_number="ABCD",
                routing_number="123456789",
                bank_name="Bank",
                account_type="checking"
            )

        # Invalid - wrong length
        with pytest.raises(ValidationError):
            BankAccountCreate(
                account_name="Test",
                account_number="12345",
                routing_number="123456789",
                bank_name="Bank",
                account_type="checking"
            )

    def test_routing_number_validation(self):
        """Test routing number validation"""
        from app.schemas.banking import BankAccountCreate

        # Valid
        account = BankAccountCreate(
            account_name="Test",
            account_number="1234",
            routing_number="123456789",
            bank_name="Bank",
            account_type="checking"
        )
        assert account.routing_number == "123456789"

        # Invalid - too short
        with pytest.raises(ValidationError):
            BankAccountCreate(
                account_name="Test",
                account_number="1234",
                routing_number="12345678",
                bank_name="Bank",
                account_type="checking"
            )

    def test_account_type_validation(self):
        """Test account type validation"""
        from app.schemas.banking import BankAccountCreate

        # Valid types
        for account_type in ["checking", "savings"]:
            account = BankAccountCreate(
                account_name="Test",
                account_number="1234",
                routing_number="123456789",
                bank_name="Bank",
                account_type=account_type
            )
            assert account.account_type == account_type

        # Invalid type
        with pytest.raises(ValidationError):
            BankAccountCreate(
                account_name="Test",
                account_number="1234",
                routing_number="123456789",
                bank_name="Bank",
                account_type="investment"
            )