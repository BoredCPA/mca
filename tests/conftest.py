# app/tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient
from typing import Generator
import os
from datetime import date, datetime
from decimal import Decimal

# Add app to path
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base, get_db
from app.main import app  # You'll need to create this
from app.models import *  # Import all models

# Test database URL
TEST_DATABASE_URL = "sqlite:///./test_mca_crm.db"

# Create test engine
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# Create test session
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Create a fresh database session for each test"""
    # Create tables
    Base.metadata.create_all(bind=engine)

    # Create session
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        # Clean up - drop all tables after test
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Create a test client with overridden database dependency"""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# Test data fixtures
@pytest.fixture
def sample_merchant_data():
    """Sample merchant data for testing"""
    return {
        "company_name": "Test Company LLC",
        "address": "123 Main St",
        "city": "New York",
        "state": "NY",
        "zip": "10001",
        "fein": "123456789",
        "phone": "2125551234",
        "entity_type": "LLC",
        "email": "test@testcompany.com",
        "contact_person": "John Doe",
        "status": "lead",
        "submitted_date": str(date.today())
    }


@pytest.fixture
def sample_principal_data():
    """Sample principal data for testing"""
    return {
        "merchant_id": 1,
        "first_name": "John",
        "last_name": "Doe",
        "ownership_percentage": 50.00,
        "ssn": "123-45-6789",
        "date_of_birth": "1980-01-01",
        "home_address": "456 Oak St",
        "city": "New York",
        "state": "NY",
        "zip": "10002",
        "phone": "2125555678",
        "email": "john.doe@email.com",
        "is_primary_contact": True,
        "is_guarantor": True
    }


@pytest.fixture
def sample_offer_data():
    """Sample offer data for testing"""
    return {
        "merchant_id": 1,
        "advance": 50000.00,
        "factor": 1.3,
        "upfront_fees": 500.00,
        "specified_percentage": 10.0,
        "payment_frequency": "daily",
        "number_of_periods": 100
    }


@pytest.fixture
def sample_bank_account_data():
    """Sample bank account data for testing"""
    return {
        "account_name": "Business Checking",
        "account_number": "1234",  # Last 4 digits
        "routing_number": "123456789",
        "bank_name": "Test Bank",
        "account_type": "checking",
        "is_primary": True
    }


@pytest.fixture
def sample_deal_data():
    """Sample deal data for testing"""
    return {
        "merchant_id": 1,
        "offer_id": 1,
        "bank_account_id": 1,
        "funding_date": str(date.today()),
        "first_payment_date": str(date.today()),
        "notes": "Test deal",
        "created_by": "test_user"
    }


@pytest.fixture
def sample_payment_data():
    """Sample payment data for testing"""
    return {
        "deal_id": 1,
        "date": datetime.now().isoformat(),
        "amount": 500.00,
        "type": "ACH",
        "bounced": False,
        "notes": "Regular payment"
    }


# Helper fixtures for creating test objects
@pytest.fixture
def create_test_merchant(db_session: Session):
    """Factory fixture to create test merchants"""

    def _create_merchant(**kwargs):
        from app.crud.merchant import create_merchant
        from app.schemas.merchant import MerchantCreate

        merchant_data = {
            "company_name": "Test Company",
            "fein": "987654321",
            "status": "lead",
            **kwargs
        }

        merchant = create_merchant(
            db_session,
            MerchantCreate(**merchant_data)
        )
        db_session.commit()
        return merchant

    return _create_merchant


@pytest.fixture
def create_test_principal(db_session: Session):
    """Factory fixture to create test principals"""

    def _create_principal(merchant_id: int, **kwargs):
        from app.crud.principal import create_principal
        from app.schemas.principal import PrincipalCreate

        principal_data = {
            "merchant_id": merchant_id,
            "first_name": "Test",
            "last_name": "Principal",
            "ownership_percentage": 100.00,
            **kwargs
        }

        principal = create_principal(
            db_session,
            PrincipalCreate(**principal_data)
        )
        db_session.commit()
        return principal

    return _create_principal


# Cleanup fixture
@pytest.fixture(autouse=True)
def cleanup_test_db():
    """Ensure test database is cleaned up"""
    yield
    # Remove test database file if it exists
    if os.path.exists("test_mca_crm.db"):
        try:
            os.remove("test_mca_crm.db")
        except:
            pass