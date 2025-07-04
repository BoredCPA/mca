# app/tests/integration/test_routes/test_merchant_routes.py
from fastapi import status
from datetime import date, datetime, timedelta


class TestMerchantAPI:
    """Test merchant API endpoints"""

    def test_create_merchant_endpoint(self, client, sample_merchant_data):
        """Test POST /api/v1/merchants/"""
        response = client.post(
            "/api/v1/merchants/",
            json=sample_merchant_data
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["company_name"] == sample_merchant_data["company_name"]
        assert data["fein"] == sample_merchant_data["fein"]
        assert "id" in data
        assert "created_at" in data

    def test_create_merchant_duplicate_fein(self, client, sample_merchant_data):
        """Test creating merchant with duplicate FEIN"""
        # Create first merchant
        response = client.post("/api/v1/merchants/", json=sample_merchant_data)
        assert response.status_code == status.HTTP_201_CREATED

        # Try to create second with same FEIN
        sample_merchant_data["company_name"] = "Different Company"
        response = client.post("/api/v1/merchants/", json=sample_merchant_data)

        assert response.status_code == status.HTTP_409_CONFLICT
        assert "already exists" in response.json()["detail"]

    def test_get_offer_calculations(self, client, create_test_merchant, sample_offer_data):
        """Test offer calculations"""
        merchant = create_test_merchant()
        sample_offer_data["merchant_id"] = merchant.id

        response = client.post("/offers/", json=sample_offer_data)
        data = response.json()

        # Verify calculations
        expected_rtr = sample_offer_data["advance"] * sample_offer_data["factor"]
        expected_net_funds = sample_offer_data["advance"] - sample_offer_data["upfront_fees"]

        assert float(data["rtr"]) == expected_rtr
        assert float(data["net_funds"]) == expected_net_funds

    def test_get_merchant_offers(self, client, create_test_merchant):
        """Test GET /merchants/{id}/offers/"""
        merchant = create_test_merchant()

        # Create multiple offers
        for i in range(3):
            offer_data = {
                "merchant_id": merchant.id,
                "advance": 10000 * (i + 1),
                "factor": 1.2 + (i * 0.1),
                "specified_percentage": 10.0
            }
            client.post("/offers/", json=offer_data)

        response = client.get(f"/merchants/{merchant.id}/offers/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 3

    def test_update_offer_status(self, client, create_test_merchant, sample_offer_data):
        """Test PATCH /offers/{id}/status/{status}"""
        merchant = create_test_merchant()
        sample_offer_data["merchant_id"] = merchant.id

        # Create offer
        create_response = client.post("/offers/", json=sample_offer_data)
        offer_id = create_response.json()["id"]

        # Update status
        response = client.patch(f"/offers/{offer_id}/status/sent")

        assert response.status_code == status.HTTP_200_OK
        assert "sent" in response.json()["message"]

        # Verify status and timestamp
        get_response = client.get(f"/offers/{offer_id}")
        offer_data = get_response.json()
        assert offer_data["status"] == "sent"
        assert offer_data["sent_at"] is not None


class TestBankingAPI:
    """Test banking API endpoints"""

    def test_create_bank_account(self, client, create_test_merchant, sample_bank_account_data):
        """Test POST /merchants/{id}/banking/"""
        merchant = create_test_merchant()

        response = client.post(
            f"/merchants/{merchant.id}/banking/",
            json=sample_bank_account_data
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["account_name"] == sample_bank_account_data["account_name"]
        assert data["is_primary"] is True
        assert "merchant_name" in data

    def test_set_primary_account(self, client, create_test_merchant):
        """Test POST /merchants/{id}/banking/{account_id}/set-primary"""
        merchant = create_test_merchant()

        # Create two accounts
        account1_data = {
            "account_name": "Account 1",
            "account_number": "1111",
            "routing_number": "111111111",
            "bank_name": "Bank 1",
            "account_type": "checking",
            "is_primary": True
        }
        account2_data = {
            "account_name": "Account 2",
            "account_number": "2222",
            "routing_number": "222222222",
            "bank_name": "Bank 2",
            "account_type": "savings",
            "is_primary": False
        }

        response1 = client.post(f"/merchants/{merchant.id}/banking/", json=account1_data)
        response2 = client.post(f"/merchants/{merchant.id}/banking/", json=account2_data)

        account1_id = response1.json()["id"]
        account2_id = response2.json()["id"]

        # Set account 2 as primary
        response = client.post(f"/merchants/{merchant.id}/banking/{account2_id}/set-primary")
        assert response.status_code == status.HTTP_200_OK

        # Verify primary status changed
        accounts = client.get(f"/merchants/{merchant.id}/banking/").json()
        account1 = next(a for a in accounts if a["id"] == account1_id)
        account2 = next(a for a in accounts if a["id"] == account2_id)

        assert account1["is_primary"] is False
        assert account2["is_primary"] is True


class TestDealAPI:
    """Test deal API endpoints"""

    def test_create_deal(self, client, create_test_merchant):
        """Test POST /api/v1/deals/"""
        merchant = create_test_merchant()

        # Create offer first
        offer_data = {
            "merchant_id": merchant.id,
            "advance": 25000,
            "factor": 1.25,
            "specified_percentage": 10.0,
            "payment_frequency": "daily",
            "number_of_periods": 50
        }
        offer_response = client.post("/offers/", json=offer_data)
        offer_id = offer_response.json()["id"]

        # Select offer
        client.patch(f"/offers/{offer_id}/status/selected")

        # Create deal
        deal_data = {
            "merchant_id": merchant.id,
            "offer_id": offer_id,
            "funding_date": str(date.today()),
            "first_payment_date": str(date.today()),
            "notes": "Test deal creation"
        }

        response = client.post("/api/v1/deals/", json=deal_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["merchant_id"] == merchant.id
        assert data["offer_id"] == offer_id
        assert data["status"] == "active"
        assert "deal_number" in data

    def test_get_deal_summary(self, client):
        """Test GET /api/v1/deals/summary"""
        response = client.get("/api/v1/deals/summary")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_deals" in data
        assert "active_deals" in data
        assert "total_funded" in data
        assert "average_factor_rate" in data


class TestPaymentAPI:
    """Test payment API endpoints"""

    def test_create_payment(self, client, create_test_merchant, sample_payment_data):
        """Test POST /api/v1/payments/"""
        # Setup: Create a deal first
        merchant = create_test_merchant()

        # Create and fund offer
        offer_data = {
            "merchant_id": merchant.id,
            "advance": 15000,
            "factor": 1.3,
            "specified_percentage": 10.0
        }
        offer_response = client.post("/offers/", json=offer_data)
        offer_id = offer_response.json()["id"]
        client.patch(f"/offers/{offer_id}/status/selected")

        deal_data = {
            "merchant_id": merchant.id,
            "offer_id": offer_id,
            "funding_date": str(date.today()),
            "first_payment_date": str(date.today())
        }
        deal_response = client.post("/api/v1/deals/", json=deal_data)
        deal_id = deal_response.json()["id"]

        # Create payment
        sample_payment_data["deal_id"] = deal_id
        response = client.post("/api/v1/payments/", json=sample_payment_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["deal_id"] == deal_id
        assert data["amount"] == sample_payment_data["amount"]
        assert data["type"] == sample_payment_data["type"]

    def test_get_payment_summary(self, client, create_test_merchant):
        """Test GET /api/v1/payments/deals/{id}/summary"""
        # Setup: Create deal and payments
        merchant = create_test_merchant()

        offer_data = {
            "merchant_id": merchant.id,
            "advance": 20000,
            "factor": 1.2,
            "specified_percentage": 10.0
        }
        offer_response = client.post("/offers/", json=offer_data)
        offer_id = offer_response.json()["id"]
        client.patch(f"/offers/{offer_id}/status/selected")

        deal_data = {
            "merchant_id": merchant.id,
            "offer_id": offer_id,
            "funding_date": str(date.today()),
            "first_payment_date": str(date.today())
        }
        deal_response = client.post("/api/v1/deals/", json=deal_data)
        deal_id = deal_response.json()["id"]

        # Create payments
        for i in range(3):
            payment_data = {
                "deal_id": deal_id,
                "date": datetime.now().isoformat(),
                "amount": 400.00,
                "type": "ACH"
            }
            client.post("/api/v1/payments/", json=payment_data)

        # Get summary
        response = client.get(f"/api/v1/payments/deals/{deal_id}/summary")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_payments"] == 3
        assert float(data["total_amount"]) == 1200.00
        assert data["average_payment"] == 400.00


class TestRenewalAPI:
    """Test renewal API endpoints"""

    def test_create_renewal_deal(self, client, create_test_merchant):
        """Test POST /api/v1/renewals/deals"""
        merchant = create_test_merchant()

        # Create old deal to renew
        old_offer_data = {
            "merchant_id": merchant.id,
            "advance": 30000,
            "factor": 1.25,
            "specified_percentage": 10.0
        }
        old_offer_response = client.post("/offers/", json=old_offer_data)
        old_offer_id = old_offer_response.json()["id"]
        client.patch(f"/offers/{old_offer_id}/status/selected")

        old_deal_data = {
            "merchant_id": merchant.id,
            "offer_id": old_offer_id,
            "funding_date": str(date.today() - timedelta(days=60)),
            "first_payment_date": str(date.today() - timedelta(days=59))
        }
        old_deal_response = client.post("/api/v1/deals/", json=old_deal_data)
        old_deal_id = old_deal_response.json()["id"]

        # Update balance (simulate some payments)
        client.patch(f"/api/v1/deals/{old_deal_id}/balance")

        # Create renewal offer
        renewal_offer_data = {
            "merchant_id": merchant.id,
            "advance": 50000,
            "factor": 1.3,
            "upfront_fees": 1000,
            "specified_percentage": 10.0
        }
        renewal_offer_response = client.post("/offers/", json=renewal_offer_data)
        renewal_offer_id = renewal_offer_response.json()["id"]
        client.patch(f"/offers/{renewal_offer_id}/status/selected")

        # Create renewal deal
        renewal_data = {
            "merchant_id": merchant.id,
            "offer_id": renewal_offer_id,
            "funding_date": str(date.today()),
            "first_payment_date": str(date.today() + timedelta(days=1)),
            "old_deals": [
                {
                    "old_deal_id": old_deal_id,
                    "transfer_balance": 15000.00,  # Remaining balance
                    "payoff_date": str(date.today())
                }
            ],
            "notes": "Test renewal"
        }

        response = client.post("/api/v1/renewals/deals", json=renewal_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["is_renewal"] is True
        assert float(data["total_transfer_balance"]) == 15000.00
        assert data["net_cash_to_merchant"] is not None

    def test_get_renewal_chain(self, client, create_test_merchant):
        """Test GET /api/v1/renewals/deals/{id}/chain"""
        # Would need to create a renewal deal first
        # This is a placeholder for the test structure
        pass

    def test_get_merchant_by_id(self, client, sample_merchant_data):
        """Test GET /api/v1/merchants/{id}"""
        # Create merchant
        create_response = client.post("/api/v1/merchants/", json=sample_merchant_data)
        merchant_id = create_response.json()["id"]

        # Get merchant
        response = client.get(f"/api/v1/merchants/{merchant_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == merchant_id
        assert data["company_name"] == sample_merchant_data["company_name"]
        """Test GET /api/v1/merchants/{id}"""
        # Create merchant
        create_response = client.post("/api/v1/merchants/", json=sample_merchant_data)
        merchant_id = create_response.json()["id"]

        # Get merchant
        response = client.get(f"/api/v1/merchants/{merchant_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == merchant_id
        assert data["company_name"] == sample_merchant_data["company_name"]

    def test_get_merchant_not_found(self, client):
        """Test getting non-existent merchant"""
        response = client.get("/api/v1/merchants/99999")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_list_merchants(self, client):
        """Test GET /api/v1/merchants/"""
        # Create multiple merchants
        for i in range(3):
            data = {
                "company_name": f"Company {i}",
                "fein": f"11111111{i}",
                "status": "lead"
            }
            client.post("/api/v1/merchants/", json=data)

        # Get list
        response = client.get("/api/v1/merchants/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "merchants" in data
        assert "total" in data
        assert data["total"] >= 3
        assert len(data["merchants"]) >= 3

    def test_list_merchants_with_pagination(self, client):
        """Test merchant list pagination"""
        # Create 5 merchants
        for i in range(5):
            data = {
                "company_name": f"Page Test {i}",
                "fein": f"22222222{i}"
            }
            client.post("/api/v1/merchants/", json=data)

        # Get first page
        response = client.get("/api/v1/merchants/?skip=0&limit=2")
        data = response.json()
        assert len(data["merchants"]) == 2
        assert data["page"] == 1
        assert data["per_page"] == 2

        # Get second page
        response = client.get("/api/v1/merchants/?skip=2&limit=2")
        data = response.json()
        assert len(data["merchants"]) == 2
        assert data["page"] == 2

    def test_search_merchants(self, client):
        """Test merchant search"""
        # Create test merchants
        client.post("/api/v1/merchants/", json={
            "company_name": "ABC Corporation",
            "email": "abc@test.com"
        })
        client.post("/api/v1/merchants/", json={
            "company_name": "XYZ Industries",
            "email": "xyz@test.com"
        })

        # Search by company name
        response = client.get("/api/v1/merchants/?search=ABC")
        data = response.json()
        assert data["total"] == 1
        assert "ABC" in data["merchants"][0]["company_name"]

    def test_filter_merchants_by_status(self, client):
        """Test filtering merchants by status"""
        # Create merchants with different statuses
        client.post("/api/v1/merchants/", json={
            "company_name": "Lead Company",
            "status": "lead"
        })
        client.post("/api/v1/merchants/", json={
            "company_name": "Funded Company",
            "status": "funded"
        })

        # Filter by status
        response = client.get("/api/v1/merchants/?status=funded")
        data = response.json()
        assert all(m["status"] == "funded" for m in data["merchants"])

    def test_update_merchant(self, client, sample_merchant_data):
        """Test PUT /api/v1/merchants/{id}"""
        # Create merchant
        create_response = client.post("/api/v1/merchants/", json=sample_merchant_data)
        merchant_id = create_response.json()["id"]

        # Update merchant
        update_data = {
            "company_name": "Updated Company Name",
            "status": "approved"
        }
        response = client.put(f"/api/v1/merchants/{merchant_id}", json=update_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["company_name"] == "Updated Company Name"
        assert data["status"] == "approved"

    def test_update_merchant_status_only(self, client, sample_merchant_data):
        """Test PATCH /api/v1/merchants/{id}/status"""
        # Create merchant
        create_response = client.post("/api/v1/merchants/", json=sample_merchant_data)
        merchant_id = create_response.json()["id"]

        # Update status only
        response = client.patch(f"/api/v1/merchants/{merchant_id}/status?status=funded")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "funded"
        assert data["company_name"] == sample_merchant_data["company_name"]

    def test_delete_merchant(self, client, sample_merchant_data):
        """Test DELETE /api/v1/merchants/{id}"""
        # Create merchant
        create_response = client.post("/api/v1/merchants/", json=sample_merchant_data)
        merchant_id = create_response.json()["id"]

        # Delete merchant
        response = client.delete(f"/api/v1/merchants/{merchant_id}")
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify merchant is soft deleted
        get_response = client.get(f"/api/v1/merchants/{merchant_id}")
        assert get_response.json()["status"] == "closed"

    def test_get_merchant_stats(self, client):
        """Test GET /api/v1/merchants/stats/summary"""
        # Create some merchants
        statuses = ["lead", "lead", "approved", "funded"]
        for i, status in enumerate(statuses):
            client.post("/api/v1/merchants/", json={
                "company_name": f"Stats Test {i}",
                "fein": f"33333333{i}",
                "status": status
            })

        response = client.get("/api/v1/merchants/stats/summary")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] >= 4
        assert data["by_status"]["lead"] >= 2
        assert data["by_status"]["approved"] >= 1
        assert data["by_status"]["funded"] >= 1


class TestPrincipalAPI:
    """Test principal API endpoints"""

    def test_create_principal(self, client, create_test_merchant, sample_principal_data):
        """Test POST /api/v1/principals/"""
        # Create merchant first
        merchant = create_test_merchant()
        sample_principal_data["merchant_id"] = merchant.id

        response = client.post("/api/v1/principals/", json=sample_principal_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["first_name"] == sample_principal_data["first_name"]
        assert data["merchant_id"] == merchant.id

    def test_create_principal_validation_errors(self, client):
        """Test principal creation with validation errors"""
        invalid_data = {
            "merchant_id": 1,
            "first_name": "John123",  # Invalid - contains numbers
            "last_name": "Doe",
            "ssn": "000-12-3456"  # Invalid SSN
        }

        response = client.post("/api/v1/principals/", json=invalid_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_merchant_principals(self, client, create_test_merchant, create_test_principal):
        """Test GET /api/v1/merchants/{id}/principals/"""
        merchant = create_test_merchant()

        # Create principals
        principal1 = create_test_principal(merchant.id, first_name="John", ownership_percentage=60)
        principal2 = create_test_principal(merchant.id, first_name="Jane", ownership_percentage=40)

        response = client.get(f"/api/v1/merchants/{merchant.id}/principals/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 2
        assert data["merchant_id"] == merchant.id
        assert len(data["principals"]) == 2

    def test_ownership_summary(self, client, create_test_merchant, create_test_principal):
        """Test GET /api/v1/merchants/{id}/principals/ownership-summary"""
        merchant = create_test_merchant()

        # Create principals with ownership
        create_test_principal(merchant.id, first_name="Owner1", ownership_percentage=60)
        create_test_principal(merchant.id, first_name="Owner2", ownership_percentage=40)

        response = client.get(f"/api/v1/merchants/{merchant.id}/principals/ownership-summary")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_ownership_percentage"] == 100.0
        assert data["ownership_allocated"] is True
        assert data["principal_count"] == 2


class TestOfferAPI:
    """Test offer API endpoints"""

    def test_create_offer(self, client, create_test_merchant, sample_offer_data):
        """Test POST /offers/"""
        merchant = create_test_merchant()
        sample_offer_data["merchant_id"] = merchant.id

        response = client.post("/offers/", json=sample_offer_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["advance"] == sample_offer_data["advance"]
        assert data["factor"] == sample_offer_data["factor"]
        assert "rtr" in data  # Calculated field
        assert "net_funds" in data  # Calculated field

    def test_get_offer_by_id(self, client, create_test_merchant, sample_offer_data):
        """Test GET /offers/{id}"""
        merchant = create_test_merchant()
        sample_offer_data["merchant_id"] = merchant.id

        # Create offer
        create_response = client.post("/offers/", json=sample_offer_data)
        offer_id = create_response.json()["id"]

        # Get offer
        response = client.get(f"/offers/{offer_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == offer_id
        assert data["advance"] == sample_offer_data["advance"]