# app/tests/unit/test_crud/test_merchant_crud.py
import pytest
from app.crud.merchant import (
    create_merchant, get_merchant, get_merchants,
    update_merchant, delete_merchant, get_merchant_stats,
    DuplicateFEINError, MerchantCRUDError
)
from app.schemas.merchant import MerchantCreate, MerchantUpdate


class TestMerchantCRUD:
    """Test merchant CRUD operations"""

    def test_create_merchant_success(self, db_session):
        """Test successful merchant creation"""
        merchant_data = MerchantCreate(
            company_name="Test Corp",
            fein="123456789",
            email="test@testcorp.com",
            status="lead"
        )

        merchant = create_merchant(db_session, merchant_data)

        assert merchant.id is not None
        assert merchant.company_name == "Test Corp"
        assert merchant.fein == "123456789"
        assert merchant.created_at is not None

    def test_create_merchant_duplicate_fein(self, db_session):
        """Test duplicate FEIN error"""
        # Create first merchant
        merchant_data = MerchantCreate(
            company_name="First Corp",
            fein="987654321"
        )
        create_merchant(db_session, merchant_data)

        # Try to create second with same FEIN
        merchant_data2 = MerchantCreate(
            company_name="Second Corp",
            fein="987654321"
        )

        with pytest.raises(DuplicateFEINError) as exc_info:
            create_merchant(db_session, merchant_data2)

        assert "already exists" in str(exc_info.value)

    def test_get_merchant_by_id(self, db_session, create_test_merchant):
        """Test retrieving merchant by ID"""
        merchant = create_test_merchant(company_name="Get Test Corp")

        retrieved = get_merchant(db_session, merchant.id)

        assert retrieved is not None
        assert retrieved.id == merchant.id
        assert retrieved.company_name == "Get Test Corp"

    def test_get_merchant_not_found(self, db_session):
        """Test getting non-existent merchant"""
        merchant = get_merchant(db_session, 99999)
        assert merchant is None

    def test_get_merchants_pagination(self, db_session):
        """Test merchant list pagination"""
        # Create multiple merchants
        for i in range(5):
            create_merchant(
                db_session,
                MerchantCreate(
                    company_name=f"Company {i}",
                    fein=f"11111111{i}"
                )
            )

        # Test pagination
        page1 = get_merchants(db_session, skip=0, limit=3)
        page2 = get_merchants(db_session, skip=3, limit=3)

        assert len(page1) == 3
        assert len(page2) == 2

    def test_get_merchants_with_filters(self, db_session):
        """Test merchant filtering"""
        # Create merchants with different statuses
        create_merchant(
            db_session,
            MerchantCreate(company_name="Lead Co", status="lead")
        )
        create_merchant(
            db_session,
            MerchantCreate(company_name="Funded Co", status="funded")
        )

        # Filter by status
        leads = get_merchants(db_session, status="lead")
        funded = get_merchants(db_session, status="funded")

        assert len(leads) == 1
        assert leads[0].company_name == "Lead Co"
        assert len(funded) == 1
        assert funded[0].company_name == "Funded Co"

    def test_get_merchants_search(self, db_session):
        """Test merchant search functionality"""
        # Create test merchants
        create_merchant(
            db_session,
            MerchantCreate(
                company_name="ABC Corporation",
                email="contact@abccorp.com"
            )
        )
        create_merchant(
            db_session,
            MerchantCreate(
                company_name="XYZ Industries",
                email="info@xyz.com"
            )
        )

        # Search by company name
        results = get_merchants(db_session, search="ABC")
        assert len(results) == 1
        assert "ABC" in results[0].company_name

        # Search by email
        results = get_merchants(db_session, search="xyz.com")
        assert len(results) == 1
        assert results[0].email == "info@xyz.com"

    def test_update_merchant(self, db_session, create_test_merchant):
        """Test merchant update"""
        merchant = create_test_merchant(
            company_name="Original Name",
            status="lead"
        )

        # Update merchant
        update_data = MerchantUpdate(
            company_name="Updated Name",
            status="approved"
        )

        updated = update_merchant(db_session, merchant.id, update_data)

        assert updated.company_name == "Updated Name"
        assert updated.status == "approved"
        assert updated.updated_at > merchant.created_at

    def test_update_merchant_duplicate_fein(self, db_session):
        """Test update with duplicate FEIN"""
        # Create two merchants
        merchant1 = create_merchant(
            db_session,
            MerchantCreate(company_name="Merchant 1", fein="111111111")
        )
        merchant2 = create_merchant(
            db_session,
            MerchantCreate(company_name="Merchant 2", fein="222222222")
        )

        # Try to update merchant2 with merchant1's FEIN
        update_data = MerchantUpdate(fein="111111111")

        with pytest.raises(DuplicateFEINError):
            update_merchant(db_session, merchant2.id, update_data)

    def test_delete_merchant(self, db_session, create_test_merchant):
        """Test merchant soft delete"""
        merchant = create_test_merchant(company_name="To Delete")

        # Delete merchant
        result = delete_merchant(db_session, merchant.id)

        assert result is True

        # Check merchant is soft deleted
        deleted = get_merchant(db_session, merchant.id)
        assert deleted.status == "closed"

    def test_delete_merchant_with_active_offers(self, db_session, create_test_merchant):
        """Test cannot delete merchant with active offers"""
        from app.models.offer import Offer

        merchant = create_test_merchant()

        # Create active offer
        offer = Offer(
            merchant_id=merchant.id,
            advance=10000,
            factor=1.2,
            specified_percentage=10.0,
            status="sent"
        )
        db_session.add(offer)
        db_session.commit()

        # Try to delete merchant
        with pytest.raises(MerchantCRUDError) as exc_info:
            delete_merchant(db_session, merchant.id)

        assert "active offers" in str(exc_info.value)

    def test_get_merchant_stats(self, db_session):
        """Test merchant statistics"""
        # Create merchants with various statuses
        statuses = ["lead", "lead", "approved", "funded", "declined"]
        for i, status in enumerate(statuses):
            create_merchant(
                db_session,
                MerchantCreate(
                    company_name=f"Company {i}",
                    fein=f"33333333{i}",
                    status=status
                )
            )

        stats = get_merchant_stats(db_session)

        assert stats["total"] == 5
        assert stats["by_status"]["lead"] == 2
        assert stats["by_status"]["approved"] == 1
        assert stats["by_status"]["funded"] == 1
        assert stats["by_status"]["declined"] == 1
        assert stats["recent_count"] >= 5  # All created recently


class TestPrincipalCRUD:
    """Test principal CRUD operations"""

    def test_create_principal_success(self, db_session, create_test_merchant):
        """Test successful principal creation"""
        from app.crud.principal import create_principal
        from app.schemas.principal import PrincipalCreate

        merchant = create_test_merchant()

        principal_data = PrincipalCreate(
            merchant_id=merchant.id,
            first_name="John",
            last_name="Doe",
            ownership_percentage=100.00,
            ssn="123-45-6789",
            is_primary_contact=True,
            email="john@example.com",
            phone="2125551234"
        )

        principal = create_principal(db_session, principal_data)

        assert principal.id is not None
        assert principal.merchant_id == merchant.id
        assert principal.ownership_percentage == 100.00

    def test_create_principal_duplicate_ssn(self, db_session, create_test_merchant):
        """Test duplicate SSN within merchant"""
        from app.crud.principal import create_principal, DuplicateSSNError
        from app.schemas.principal import PrincipalCreate

        merchant = create_test_merchant()

        # Create first principal
        principal_data = PrincipalCreate(
            merchant_id=merchant.id,
            first_name="John",
            last_name="Doe",
            ssn="987-65-4321"
        )
        create_principal(db_session, principal_data)

        # Try to create second with same SSN
        principal_data2 = PrincipalCreate(
            merchant_id=merchant.id,
            first_name="Jane",
            last_name="Smith",
            ssn="987-65-4321"
        )

        with pytest.raises(DuplicateSSNError):
            create_principal(db_session, principal_data2)

    def test_ownership_percentage_validation(self, db_session, create_test_merchant):
        """Test ownership percentage cannot exceed 100%"""
        from app.crud.principal import create_principal, OwnershipExceededError
        from app.schemas.principal import PrincipalCreate

        merchant = create_test_merchant()

        # Create first principal with 60%
        principal_data1 = PrincipalCreate(
            merchant_id=merchant.id,
            first_name="John",
            last_name="Doe",
            ownership_percentage=60.00
        )
        create_principal(db_session, principal_data1)

        # Try to create second with 50% (total would be 110%)
        principal_data2 = PrincipalCreate(
            merchant_id=merchant.id,
            first_name="Jane",
            last_name="Smith",
            ownership_percentage=50.00
        )

        with pytest.raises(OwnershipExceededError) as exc_info:
            create_principal(db_session, principal_data2)

        assert "110" in str(exc_info.value)

    def test_primary_contact_switching(self, db_session, create_test_merchant, create_test_principal):
        """Test only one principal can be primary contact"""
        from app.crud.principal import create_principal
        from app.schemas.principal import PrincipalCreate

        merchant = create_test_merchant()

        # Create first principal as primary
        principal1 = create_test_principal(
            merchant.id,
            first_name="First",
            is_primary_contact=True,
            email="first@example.com",
            phone="1111111111"
        )

        # Create second principal as primary
        principal_data = PrincipalCreate(
            merchant_id=merchant.id,
            first_name="Second",
            last_name="Primary",
            is_primary_contact=True,
            email="second@example.com",
            phone="2222222222"
        )
        principal2 = create_principal(db_session, principal_data)

        # Refresh first principal
        db_session.refresh(principal1)

        # First should no longer be primary
        assert principal1.is_primary_contact is False
        assert principal2.is_primary_contact is True