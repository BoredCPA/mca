# app/tests/unit/test_models/test_merchant_model.py
import pytest
from sqlalchemy.exc import IntegrityError
from app.models.merchant import Merchant
from datetime import datetime


class TestMerchantModel:
    """Test Merchant model validation and constraints"""

    def test_create_merchant_minimal(self, db_session):
        """Test creating merchant with minimal required fields"""
        merchant = Merchant(
            company_name="Test Company",
            status="lead"
        )
        db_session.add(merchant)
        db_session.commit()

        assert merchant.id is not None
        assert merchant.company_name == "Test Company"
        assert merchant.status == "lead"
        assert merchant.created_at is not None

    def test_unique_fein_constraint(self, db_session):
        """Test FEIN uniqueness constraint"""
        # Create first merchant
        merchant1 = Merchant(
            company_name="Company 1",
            fein="123456789"
        )
        db_session.add(merchant1)
        db_session.commit()

        # Try to create second with same FEIN
        merchant2 = Merchant(
            company_name="Company 2",
            fein="123456789"
        )
        db_session.add(merchant2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_merchant_relationships(self, db_session, create_test_merchant):
        """Test merchant relationships with other models"""
        merchant = create_test_merchant()

        # Test relationships exist
        assert hasattr(merchant, 'offers')
        assert hasattr(merchant, 'principals')
        assert hasattr(merchant, 'bank_accounts')

        # Test empty relationships
        assert len(merchant.offers) == 0
        assert len(merchant.principals) == 0
        assert len(merchant.bank_accounts) == 0


class TestPrincipalModel:
    """Test Principal model validation and relationships"""

    def test_create_principal(self, db_session, create_test_merchant):
        """Test creating a principal"""
        from app.models.principal import Principal

        merchant = create_test_merchant()

        principal = Principal(
            merchant_id=merchant.id,
            first_name="John",
            last_name="Doe",
            ownership_percentage=100.00,
            is_primary_contact=True
        )
        db_session.add(principal)
        db_session.commit()

        assert principal.id is not None
        assert principal.merchant_id == merchant.id
        assert principal.ownership_percentage == 100.00
        assert principal.is_guarantor is True  # Default value

    def test_principal_merchant_relationship(self, db_session, create_test_merchant):
        """Test principal-merchant relationship"""
        from app.models.principal import Principal

        merchant = create_test_merchant()

        principal = Principal(
            merchant_id=merchant.id,
            first_name="Jane",
            last_name="Smith"
        )
        db_session.add(principal)
        db_session.commit()

        # Refresh to load relationships
        db_session.refresh(merchant)

        assert len(merchant.principals) == 1
        assert merchant.principals[0].first_name == "Jane"
        assert principal.merchant.company_name == merchant.company_name


class TestOfferModel:
    """Test Offer model and calculations"""

    def test_create_offer(self, db_session, create_test_merchant):
        """Test creating an offer"""
        from app.models.offer import Offer

        merchant = create_test_merchant()

        offer = Offer(
            merchant_id=merchant.id,
            advance=50000.00,
            factor=1.3,
            upfront_fees=500.00,
            specified_percentage=10.0,
            payment_frequency="daily"
        )
        db_session.add(offer)
        db_session.commit()

        assert offer.id is not None
        assert offer.advance == 50000.00
        assert offer.factor == 1.3
        assert offer.status == "draft"  # Default value

    def test_offer_unique_deal_id(self, db_session, create_test_merchant):
        """Test deal_id uniqueness constraint"""
        from app.models.offer import Offer

        merchant = create_test_merchant()

        # Create first offer with deal_id
        offer1 = Offer(
            merchant_id=merchant.id,
            advance=10000,
            factor=1.2,
            specified_percentage=10.0,
            deal_id="DEAL-001"
        )
        db_session.add(offer1)
        db_session.commit()

        # Try to create second with same deal_id
        offer2 = Offer(
            merchant_id=merchant.id,
            advance=20000,
            factor=1.3,
            specified_percentage=10.0,
            deal_id="DEAL-001"
        )
        db_session.add(offer2)

        with pytest.raises(IntegrityError):
            db_session.commit()


class TestBankAccountModel:
    """Test BankAccount model validation"""

    def test_create_bank_account(self, db_session, create_test_merchant):
        """Test creating a bank account"""
        from app.models.banking import BankAccount

        merchant = create_test_merchant()

        bank_account = BankAccount(
            merchant_id=merchant.id,
            account_name="Business Checking",
            account_number="1234",
            routing_number="123456789",
            bank_name="Test Bank",
            account_type="checking",
            is_primary=True
        )
        db_session.add(bank_account)
        db_session.commit()

        assert bank_account.id is not None
        assert bank_account.is_active is True  # Default value
        assert bank_account.merchant.id == merchant.id

    def test_account_type_constraint(self, db_session, create_test_merchant):
        """Test account type constraint"""
        from app.models.banking import BankAccount

        merchant = create_test_merchant()

        # Try invalid account type
        bank_account = BankAccount(
            merchant_id=merchant.id,
            account_name="Invalid Account",
            account_number="5678",
            routing_number="987654321",
            bank_name="Test Bank",
            account_type="invalid_type"  # Should fail
        )
        db_session.add(bank_account)

        with pytest.raises(IntegrityError):
            db_session.commit()


class TestDealModel:
    """Test Deal model and renewal logic"""

    def test_create_deal(self, db_session, create_test_merchant):
        """Test creating a deal"""
        from app.models.deal import Deal
        from app.models.offer import Offer
        from datetime import date

        merchant = create_test_merchant()

        # Create offer first
        offer = Offer(
            merchant_id=merchant.id,
            advance=50000,
            factor=1.3,
            specified_percentage=10.0
        )
        db_session.add(offer)
        db_session.commit()

        # Create deal
        deal = Deal(
            merchant_id=merchant.id,
            offer_id=offer.id,
            deal_number="MCA-2024-0001",
            funded_amount=50000,
            factor_rate=1.3,
            rtr_amount=65000,
            payment_amount=650,
            payment_frequency="daily",
            number_of_payments=100,
            funding_date=date.today(),
            first_payment_date=date.today(),
            maturity_date=date.today(),
            balance_remaining=65000,
            payments_remaining=100
        )
        db_session.add(deal)
        db_session.commit()

        assert deal.id is not None
        assert deal.status == "active"
        assert deal.is_renewal is False
        assert deal.total_paid == 0

    def test_deal_number_uniqueness(self, db_session, create_test_merchant):
        """Test deal number uniqueness"""
        from app.models.deal import Deal
        from app.models.offer import Offer
        from datetime import date

        merchant = create_test_merchant()

        # Create offer
        offer = Offer(
            merchant_id=merchant.id,
            advance=10000,
            factor=1.2,
            specified_percentage=10.0
        )
        db_session.add(offer)
        db_session.commit()

        # Create first deal
        deal1 = Deal(
            merchant_id=merchant.id,
            offer_id=offer.id,
            deal_number="MCA-2024-0001",
            funded_amount=10000,
            factor_rate=1.2,
            rtr_amount=12000,
            payment_amount=120,
            payment_frequency="daily",
            number_of_payments=100,
            funding_date=date.today(),
            first_payment_date=date.today(),
            maturity_date=date.today(),
            balance_remaining=12000,
            payments_remaining=100
        )
        db_session.add(deal1)
        db_session.commit()

        # Try to create second deal with same number
        deal2 = Deal(
            merchant_id=merchant.id,
            offer_id=offer.id,
            deal_number="MCA-2024-0001",  # Duplicate
            funded_amount=10000,
            factor_rate=1.2,
            rtr_amount=12000,
            payment_amount=120,
            payment_frequency="daily",
            number_of_payments=100,
            funding_date=date.today(),
            first_payment_date=date.today(),
            maturity_date=date.today(),
            balance_remaining=12000,
            payments_remaining=100
        )
        db_session.add(deal2)

        with pytest.raises(IntegrityError):
            db_session.commit()