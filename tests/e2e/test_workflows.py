# app/tests/e2e/test_workflows.py
import pytest
from datetime import date, timedelta
from decimal import Decimal


class TestMerchantOnboardingWorkflow:
    """Test complete merchant onboarding workflow"""

    def test_complete_merchant_onboarding(self, client):
        """Test full merchant onboarding process"""
        # Step 1: Create merchant
        merchant_data = {
            "company_name": "E2E Test Company LLC",
            "fein": "987654321",
            "address": "123 Test St",
            "city": "New York",
            "state": "NY",
            "zip": "10001",
            "phone": "2125551234",
            "email": "test@e2ecompany.com",
            "contact_person": "Test Manager",
            "entity_type": "LLC",
            "status": "lead"
        }

        merchant_response = client.post("/api/v1/merchants/", json=merchant_data)
        assert merchant_response.status_code == 201
        merchant_id = merchant_response.json()["id"]

        # Step 2: Add principals
        principal1_data = {
            "merchant_id": merchant_id,
            "first_name": "John",
            "last_name": "Owner",
            "ownership_percentage": 60.00,
            "ssn": "123-45-6789",
            "date_of_birth": "1980-01-01",
            "home_address": "456 Home St",
            "city": "New York",
            "state": "NY",
            "zip": "10002",
            "phone": "2125555678",
            "email": "john@e2ecompany.com",
            "is_primary_contact": True,
            "is_guarantor": True
        }

        principal2_data = {
            "merchant_id": merchant_id,
            "first_name": "Jane",
            "last_name": "Partner",
            "ownership_percentage": 40.00,
            "ssn": "987-65-4321",
            "date_of_birth": "1985-05-15",
            "home_address": "789 Partner Ave",
            "city": "New York",
            "state": "NY",
            "zip": "10003",
            "phone": "2125559876",
            "email": "jane@e2ecompany.com",
            "is_guarantor": True
        }

        principal1_response = client.post("/api/v1/principals/", json=principal1_data)
        principal2_response = client.post("/api/v1/principals/", json=principal2_data)

        assert principal1_response.status_code == 201
        assert principal2_response.status_code == 201

        # Verify ownership totals 100%
        ownership_response = client.get(f"/api/v1/merchants/{merchant_id}/principals/ownership-summary")
        ownership_data = ownership_response.json()
        assert ownership_data["total_ownership_percentage"] == 100.0
        assert ownership_data["ownership_allocated"] is True

        # Step 3: Add bank account
        bank_account_data = {
            "account_name": "E2E Business Checking",
            "account_number": "9999",
            "routing_number": "123456789",
            "bank_name": "E2E Test Bank",
            "account_type": "checking",
            "is_primary": True
        }

        bank_response = client.post(f"/merchants/{merchant_id}/banking/", json=bank_account_data)
        assert bank_response.status_code == 200
        bank_account_id = bank_response.json()["id"]

        # Step 4: Update merchant status to applicant
        status_response = client.patch(f"/api/v1/merchants/{merchant_id}/status?status=applicant")
        assert status_response.status_code == 200

        # Verify complete merchant profile
        merchant_details = client.get(f"/api/v1/merchants/{merchant_id}").json()
        assert merchant_details["status"] == "applicant"

        # Verify all components are linked
        principals = client.get(f"/api/v1/merchants/{merchant_id}/principals/").json()
        assert principals["total"] == 2

        bank_accounts = client.get(f"/merchants/{merchant_id}/banking/").json()
        assert len(bank_accounts) == 1
        assert bank_accounts[0]["is_primary"] is True

        return merchant_id, bank_account_id


class TestOfferToFundingWorkflow:
    """Test offer creation through funding workflow"""

    def test_offer_to_funding_workflow(self, client, create_test_merchant):
        """Test complete offer to funding process"""
        # Setup: Create merchant with bank account
        merchant = create_test_merchant(status="approved")

        bank_data = {
            "account_name": "Funding Account",
            "account_number": "8888",
            "routing_number": "987654321",
            "bank_name": "Funding Bank",
            "account_type": "checking",
            "is_primary": True
        }
        bank_response = client.post(f"/merchants/{merchant.id}/banking/", json=bank_data)
        bank_account_id = bank_response.json()["id"]

        # Step 1: Create multiple offers
        offers = []
        for i in range(3):
            offer_data = {
                "merchant_id": merchant.id,
                "advance": 50000 + (i * 10000),
                "factor": 1.2 + (i * 0.05),
                "upfront_fees": 500 + (i * 100),
                "specified_percentage": 10.0,
                "payment_frequency": "daily",
                "number_of_periods": 100 - (i * 10)
            }
            response = client.post("/offers/", json=offer_data)
            assert response.status_code == 200
            offers.append(response.json())

        # Step 2: Send offers
        for offer in offers:
            response = client.patch(f"/offers/{offer['id']}/status/sent")
            assert response.status_code == 200

        # Step 3: Select best offer
        selected_offer = offers[1]  # Middle offer
        response = client.patch(f"/offers/{selected_offer['id']}/status/selected")
        assert response.status_code == 200

        # Step 4: Create deal from selected offer
        deal_data = {
            "merchant_id": merchant.id,
            "offer_id": selected_offer["id"],
            "bank_account_id": bank_account_id,
            "funding_date": str(date.today()),
            "first_payment_date": str(date.today() + timedelta(days=1)),
            "notes": "E2E test deal",
            "created_by": "test_user"
        }

        deal_response = client.post("/api/v1/deals/", json=deal_data)
        assert deal_response.status_code == 201
        deal = deal_response.json()

        # Verify deal details
        assert deal["funded_amount"] == selected_offer["advance"]
        assert deal["factor_rate"] == selected_offer["factor"]
        assert deal["status"] == "active"
        assert deal["is_renewal"] is False

        # Verify offer status updated
        offer_check = client.get(f"/offers/{selected_offer['id']}").json()
        assert offer_check["status"] == "funded"
        assert offer_check["funded_at"] is not None

        return deal["id"]


class TestPaymentProcessingWorkflow:
    """Test payment processing workflow"""

    def test_payment_processing_workflow(self, client, create_test_merchant):
        """Test payment recording and balance updates"""
        # Setup: Create funded deal
        merchant = create_test_merchant()

        # Create and fund offer
        offer_data = {
            "merchant_id": merchant.id,
            "advance": 10000,
            "factor": 1.3,
            "specified_percentage": 10.0,
            "payment_frequency": "daily",
            "number_of_periods": 20
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
            "first_payment_date": str(date.today())
        }
        deal_response = client.post("/api/v1/deals/", json=deal_data)
        deal_id = deal_response.json()["id"]

        # Record payments
        payment_amount = 650  # 10% of RTR (13,000)
        for i in range(5):
            payment_data = {
                "deal_id": deal_id,
                "date": str(date.today() + timedelta(days=i)),
                "amount": payment_amount,
                "type": "ACH",
                "notes": f"Payment {i + 1}"
            }
            response = client.post("/api/v1/payments/", json=payment_data)
            assert response.status_code == 201

        # Update deal balance
        balance_response = client.patch(f"/api/v1/deals/{deal_id}/balance")
        assert balance_response.status_code == 200

        updated_deal = balance_response.json()
        assert float(updated_deal["total_paid"]) == payment_amount * 5
        assert float(updated_deal["balance_remaining"]) == 13000 - (payment_amount * 5)
        assert updated_deal["payments_remaining"] == 15

        # Test bounced payment
        bounced_payment_data = {
            "deal_id": deal_id,
            "date": str(date.today() + timedelta(days=5)),
            "amount": payment_amount,
            "type": "ACH",
            "bounced": True,
            "notes": "NSF"
        }
        bounced_response = client.post("/api/v1/payments/", json=bounced_payment_data)
        assert bounced_response.status_code == 201

        # Get payment summary
        summary_response = client.get(f"/api/v1/payments/deals/{deal_id}/summary")
        summary = summary_response.json()
        assert summary["total_payments"] == 6
        assert summary["total_bounced"] == 1
        assert float(summary["bounced_amount"]) == payment_amount


class TestRenewalWorkflow:
    """Test deal renewal workflow"""

    def test_renewal_workflow(self, client, create_test_merchant):
        """Test renewing existing deals"""
        merchant = create_test_merchant()

        # Create two existing deals to renew
        old_deals = []
        for i in range(2):
            # Create offer
            offer_data = {
                "merchant_id": merchant.id,
                "advance": 20000 + (i * 5000),
                "factor": 1.25,
                "specified_percentage": 10.0,
                "payment_frequency": "daily",
                "number_of_periods": 50
            }
            offer_response = client.post("/offers/", json=offer_data)
            offer_id = offer_response.json()["id"]

            # Select and fund
            client.patch(f"/offers/{offer_id}/status/selected")

            deal_data = {
                "merchant_id": merchant.id,
                "offer_id": offer_id,
                "funding_date": str(date.today() - timedelta(days=30)),
                "first_payment_date": str(date.today() - timedelta(days=29))
            }
            deal_response = client.post("/api/v1/deals/", json=deal_data)
            deal = deal_response.json()

            # Record some payments (leaving balance)
            for j in range(10):
                payment_data = {
                    "deal_id": deal["id"],
                    "date": str(date.today() - timedelta(days=29 - j)),
                    "amount": float(deal["payment_amount"]),
                    "type": "ACH"
                }
                client.post("/api/v1/payments/", json=payment_data)

            # Update balance
            client.patch(f"/api/v1/deals/{deal['id']}/balance")

            old_deals.append(deal)

        # Create renewal offer
        total_balance = sum(float(d["balance_remaining"]) for d in old_deals)
        renewal_offer_data = {
            "merchant_id": merchant.id,
            "advance": 50000,  # New advance
            "factor": 1.35,
            "upfront_fees": 1000,
            "specified_percentage": 10.0,
            "payment_frequency": "weekly",
            "number_of_periods": 20
        }
        renewal_offer_response = client.post("/offers/", json=renewal_offer_data)
        renewal_offer_id = renewal_offer_response.json()["id"]

        # Select renewal offer
        client.patch(f"/offers/{renewal_offer_id}/status/selected")

        # Create bank account for funding
        bank_data = {
            "account_name": "Renewal Account",
            "account_number": "7777",
            "routing_number": "123123123",
            "bank_name": "Renewal Bank",
            "account_type": "checking"
        }
        bank_response = client.post(f"/merchants/{merchant.id}/banking/", json=bank_data)
        bank_account_id = bank_response.json()["id"]

        # Create renewal deal
        renewal_data = {
            "merchant_id": merchant.id,
            "offer_id": renewal_offer_id,
            "bank_account_id": bank_account_id,
            "funding_date": str(date.today()),
            "first_payment_date": str(date.today() + timedelta(days=7)),
            "old_deals": [
                {
                    "old_deal_id": old_deals[0]["id"],
                    "transfer_balance": float(old_deals[0]["balance_remaining"]),
                    "payoff_date": str(date.today())
                },
                {
                    "old_deal_id": old_deals[1]["id"],
                    "transfer_balance": float(old_deals[1]["balance_remaining"]),
                    "payoff_date": str(date.today())
                }
            ],
            "notes": "Renewal of two existing deals",
            "created_by": "test_user"
        }

        renewal_response = client.post("/api/v1/renewals/deals", json=renewal_data)
        assert renewal_response.status_code == 201

        renewal_deal = renewal_response.json()

        # Verify renewal deal details
        assert renewal_deal["is_renewal"] is True
        assert float(renewal_deal["total_transfer_balance"]) > 0
        expected_net_cash = 50000 - 1000 - float(renewal_deal["total_transfer_balance"])
        assert float(renewal_deal["net_cash_to_merchant"]) == expected_net_cash

        # Verify old deals marked as renewed
        for old_deal in old_deals:
            old_deal_check = client.get(f"/api/v1/deals/{old_deal['id']}").json()
            assert old_deal_check["status"] == "renewed"

        # Check renewal chain
        chain_response = client.get(f"/api/v1/renewals/deals/{renewal_deal['id']}/chain")
        chain = chain_response.json()
        assert chain["is_renewal"] is True
        assert len(chain["renewed_from"]) == 2

        return renewal_deal["id"]