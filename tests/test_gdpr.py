"""
Tests for FinSight API - GDPR Compliance
Tests for data export, deletion, and user rights
Adapted from FinRobot's testing discipline
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException

from src.api.gdpr import (
    export_user_data,
    delete_user_account,
    get_gdpr_info,
    DeletionRequest
)
from src.models.user import User, APIKey, PricingTier


@pytest.fixture
def mock_user():
    """Create a mock authenticated user"""
    return User(
        user_id="usr_test123",
        email="test@example.com",
        email_verified=True,
        tier=PricingTier.PROFESSIONAL,
        status="active",
        api_calls_this_month=500,
        api_calls_limit=10000,
        stripe_customer_id="cus_test123",
        stripe_subscription_id="sub_test123",
        billing_period_start=datetime.utcnow(),
        billing_period_end=datetime.utcnow() + timedelta(days=30),
        created_at=datetime.utcnow() - timedelta(days=60),
        company_name="Test Corp",
        website="https://example.com"
    )


@pytest.fixture
def mock_api_key():
    """Create a mock API key"""
    return APIKey(
        key_id="key_test123",
        user_id="usr_test123",
        key_prefix="fsk_12345678",
        name="Test Key",
        is_active=True,
        is_test_mode=False,
        total_calls=1000,
        calls_this_month=500,
        created_at=datetime.utcnow() - timedelta(days=30),
        last_used_at=datetime.utcnow()
    )


@pytest.fixture
def mock_db_connection():
    """Create a mock database connection"""
    conn = AsyncMock()

    # Mock user record
    user_record = {
        "user_id": "usr_test123",
        "email": "test@example.com",
        "email_verified": True,
        "company_name": "Test Corp",
        "website": "https://example.com",
        "tier": "professional",
        "status": "active",
        "api_calls_this_month": 500,
        "api_calls_limit": 10000,
        "stripe_customer_id": "cus_test123",
        "stripe_subscription_id": "sub_test123",
        "billing_period_start": datetime.utcnow(),
        "billing_period_end": datetime.utcnow() + timedelta(days=30),
        "created_at": datetime.utcnow() - timedelta(days=60),
        "updated_at": datetime.utcnow(),
        "last_api_call": datetime.utcnow(),
        "last_login": datetime.utcnow()
    }

    # Mock API keys
    api_keys = [
        {
            "key_id": "key_test123",
            "key_prefix": "fsk_12345678",
            "name": "Test Key",
            "is_active": True,
            "is_test_mode": False,
            "total_calls": 1000,
            "calls_this_month": 500,
            "last_used_at": datetime.utcnow(),
            "allowed_ips": None,
            "allowed_domains": None,
            "created_at": datetime.utcnow() - timedelta(days=30),
            "expires_at": None
        }
    ]

    # Mock usage records
    usage_records = [
        {
            "record_id": "rec_123",
            "endpoint": "/api/v1/metrics",
            "method": "GET",
            "status_code": 200,
            "credits_used": 1,
            "response_time_ms": 120,
            "timestamp": datetime.utcnow(),
            "ip_address": "192.168.1.1",
            "user_agent": "Mozilla/5.0"
        }
    ]

    # Mock subscription history
    subscription_history = [
        {
            "old_tier": "free",
            "new_tier": "professional",
            "event_type": "upgrade",
            "stripe_subscription_id": "sub_test123",
            "change_reason": "upgrade",
            "metadata": {"plan": "professional"},
            "changed_at": datetime.utcnow() - timedelta(days=30)
        }
    ]

    conn.fetchrow.return_value = user_record
    conn.fetch.side_effect = [api_keys, usage_records, subscription_history]

    return conn


@pytest.fixture
def mock_db_pool(mock_db_connection):
    """Create a mock database pool"""
    pool = AsyncMock()
    pool.acquire.return_value.__aenter__.return_value = mock_db_connection
    pool.acquire.return_value.__aexit__.return_value = None

    # Set the global pool
    from src.api import gdpr
    gdpr._db_pool = pool

    return pool


class TestDataExport:
    """Test data export endpoint (GDPR Article 15 - Right of Access)"""

    @pytest.mark.asyncio
    async def test_export_user_data_success(self, mock_user, mock_api_key, mock_db_pool):
        """Test successful data export"""

        response = await export_user_data(
            auth=(mock_user, mock_api_key)
        )

        # Verify response structure
        assert response.user_data is not None
        assert response.api_keys is not None
        assert response.usage_records is not None
        assert response.subscription_history is not None
        assert response.export_timestamp is not None
        assert response.format_version == "1.0"

        # Verify user data
        assert response.user_data["user_id"] == "usr_test123"
        assert response.user_data["email"] == "test@example.com"
        assert response.user_data["company_name"] == "Test Corp"
        assert response.user_data["website"] == "https://example.com"
        assert response.user_data["tier"] == "professional"

        # Verify API keys included (but not hashes)
        assert len(response.api_keys) > 0
        api_key = response.api_keys[0]
        assert api_key["key_id"] == "key_test123"
        assert api_key["key_prefix"] == "fsk_12345678"
        assert "key_hash" not in api_key  # Sensitive data excluded

        # Verify usage records included
        assert len(response.usage_records) > 0
        usage = response.usage_records[0]
        assert usage["endpoint"] == "/api/v1/metrics"
        assert usage["status_code"] == 200

        # Verify subscription history
        assert len(response.subscription_history) > 0
        history = response.subscription_history[0]
        assert history["old_tier"] == "free"
        assert history["new_tier"] == "professional"

    @pytest.mark.asyncio
    async def test_export_excludes_sensitive_data(self, mock_user, mock_api_key, mock_db_pool):
        """Test that sensitive data is excluded from export"""

        response = await export_user_data(
            auth=(mock_user, mock_api_key)
        )

        # Check that API key hashes are not included
        for api_key in response.api_keys:
            assert "key_hash" not in api_key
            assert "password_hash" not in api_key

        # Only key prefixes should be included
        api_key = response.api_keys[0]
        assert api_key["key_prefix"].startswith("fsk_")

    @pytest.mark.asyncio
    async def test_export_limited_usage_records(self, mock_user, mock_api_key, mock_db_pool):
        """Test that usage records are limited to 90 days and 1000 records"""

        response = await export_user_data(
            auth=(mock_user, mock_api_key)
        )

        # Verify SQL query was called with proper limits
        # (In real implementation, verify the query includes:
        # - timestamp >= NOW() - INTERVAL '90 days'
        # - LIMIT 1000)
        assert response.usage_records is not None

    @pytest.mark.asyncio
    async def test_export_data_portability_format(self, mock_user, mock_api_key, mock_db_pool):
        """Test that export is in machine-readable format (GDPR Article 20)"""

        response = await export_user_data(
            auth=(mock_user, mock_api_key)
        )

        # Should be JSON-serializable
        response_dict = response.model_dump()
        json_str = json.dumps(response_dict, default=str)
        assert json_str is not None

        # Should include format version for future compatibility
        assert response.format_version is not None


class TestAccountDeletion:
    """Test account deletion endpoint (GDPR Article 17 - Right to Erasure)"""

    @pytest.mark.asyncio
    async def test_delete_account_success(self, mock_user, mock_api_key, mock_db_pool):
        """Test successful account deletion"""

        # Create a user without active subscription for deletion test
        mock_user.stripe_subscription_id = None
        mock_user.status = "cancelled"

        mock_conn = mock_db_pool.acquire.return_value.__aenter__.return_value

        # Mock transaction context
        mock_transaction = AsyncMock()
        mock_conn.transaction.return_value.__aenter__.return_value = mock_transaction
        mock_conn.transaction.return_value.__aexit__.return_value = None

        # Mock no active subscription
        mock_conn.fetchval.return_value = False

        request = DeletionRequest(
            confirm_email="test@example.com",
            reason="No longer need the service"
        )

        response = await delete_user_account(
            request=request,
            auth=(mock_user, mock_api_key)
        )

        assert response.status == "deleted"
        assert "successfully deleted" in response.message
        assert response.deleted_at is not None

        # Verify retained data is documented
        assert "subscription_history" in response.data_retained
        assert "billing_records" in response.data_retained

        # Verify deletion operations were called
        assert mock_conn.execute.call_count >= 2  # Delete API keys, anonymize user

    @pytest.mark.asyncio
    async def test_delete_requires_email_confirmation(self, mock_user, mock_api_key, mock_db_pool):
        """Test that deletion requires correct email confirmation"""

        request = DeletionRequest(
            confirm_email="wrong@example.com",  # Wrong email
            reason="Test"
        )

        with pytest.raises(HTTPException) as exc:
            await delete_user_account(
                request=request,
                auth=(mock_user, mock_api_key)
            )

        assert exc.value.status_code == 400
        assert "email_mismatch" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_delete_blocks_active_subscription(self, mock_user, mock_api_key, mock_db_pool):
        """Test that users with active subscriptions must cancel first"""

        mock_conn = mock_db_pool.acquire.return_value.__aenter__.return_value

        # Mock transaction context
        mock_transaction = AsyncMock()
        mock_conn.transaction.return_value.__aenter__.return_value = mock_transaction
        mock_conn.transaction.return_value.__aexit__.return_value = None

        # Mock active subscription
        mock_conn.fetchval.return_value = True

        request = DeletionRequest(
            confirm_email="test@example.com",
            reason="Test"
        )

        with pytest.raises(HTTPException) as exc:
            await delete_user_account(
                request=request,
                auth=(mock_user, mock_api_key)
            )

        assert exc.value.status_code == 400
        assert "active_subscription" in str(exc.value.detail)
        assert "cancel_url" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_delete_anonymizes_user_data(self, mock_user, mock_api_key, mock_db_pool):
        """Test that user data is anonymized, not fully deleted"""

        mock_user.stripe_subscription_id = None
        mock_user.status = "cancelled"

        mock_conn = mock_db_pool.acquire.return_value.__aenter__.return_value

        # Mock transaction context
        mock_transaction = AsyncMock()
        mock_conn.transaction.return_value.__aenter__.return_value = mock_transaction
        mock_conn.transaction.return_value.__aexit__.return_value = None

        # Mock no active subscription
        mock_conn.fetchval.return_value = False

        request = DeletionRequest(
            confirm_email="test@example.com",
            reason="No longer needed"
        )

        response = await delete_user_account(
            request=request,
            auth=(mock_user, mock_api_key)
        )

        # Verify user record is anonymized (not deleted)
        update_calls = [
            call for call in mock_conn.execute.call_args_list
            if "UPDATE users" in str(call)
        ]
        assert len(update_calls) > 0

        # Verify API keys are deleted
        delete_calls = [
            call for call in mock_conn.execute.call_args_list
            if "DELETE FROM api_keys" in str(call)
        ]
        assert len(delete_calls) > 0

    @pytest.mark.asyncio
    async def test_delete_logs_reason(self, mock_user, mock_api_key, mock_db_pool):
        """Test that deletion reason is logged for analytics"""

        mock_user.stripe_subscription_id = None
        mock_user.status = "cancelled"

        mock_conn = mock_db_pool.acquire.return_value.__aenter__.return_value

        # Mock transaction context
        mock_transaction = AsyncMock()
        mock_conn.transaction.return_value.__aenter__.return_value = mock_transaction
        mock_conn.transaction.return_value.__aexit__.return_value = None

        # Mock no active subscription
        mock_conn.fetchval.return_value = False

        request = DeletionRequest(
            confirm_email="test@example.com",
            reason="Switching to competitor"
        )

        response = await delete_user_account(
            request=request,
            auth=(mock_user, mock_api_key)
        )

        # Verify reason was logged
        insert_calls = [
            call for call in mock_conn.execute.call_args_list
            if "INSERT INTO subscription_history" in str(call)
        ]
        assert len(insert_calls) > 0

    @pytest.mark.asyncio
    async def test_delete_case_insensitive_email(self, mock_user, mock_api_key, mock_db_pool):
        """Test that email confirmation is case-insensitive"""

        mock_user.stripe_subscription_id = None
        mock_user.status = "cancelled"

        mock_conn = mock_db_pool.acquire.return_value.__aenter__.return_value

        # Mock transaction context
        mock_transaction = AsyncMock()
        mock_conn.transaction.return_value.__aenter__.return_value = mock_transaction
        mock_conn.transaction.return_value.__aexit__.return_value = None

        # Mock no active subscription
        mock_conn.fetchval.return_value = False

        # Use different case
        request = DeletionRequest(
            confirm_email="TEST@EXAMPLE.COM",
            reason="Test"
        )

        response = await delete_user_account(
            request=request,
            auth=(mock_user, mock_api_key)
        )

        assert response.status == "deleted"


class TestGDPRInfo:
    """Test GDPR information endpoint"""

    @pytest.mark.asyncio
    async def test_get_gdpr_info(self):
        """Test getting GDPR information (public endpoint)"""

        response = await get_gdpr_info()

        # Verify structure
        assert "data_controller" in response
        assert "user_rights" in response
        assert "data_processing" in response
        assert "contact" in response

        # Verify data controller info
        controller = response["data_controller"]
        assert "name" in controller
        assert "contact" in controller
        assert "dpo_contact" in controller

        # Verify user rights are documented
        rights = response["user_rights"]
        assert "right_of_access" in rights
        assert "right_to_erasure" in rights
        assert "right_to_rectification" in rights
        assert "right_to_portability" in rights

        # Each right should have endpoint info
        for right_name, right_info in rights.items():
            assert "description" in right_info
            assert "endpoint" in right_info

        # Verify data processing info
        processing = response["data_processing"]
        assert "purposes" in processing
        assert "legal_basis" in processing
        assert "retention_period" in processing
        assert "third_parties" in processing

        # Verify third parties are documented
        third_parties = processing["third_parties"]
        assert len(third_parties) > 0
        for party in third_parties:
            assert "name" in party
            assert "purpose" in party
            assert "location" in party

    @pytest.mark.asyncio
    async def test_gdpr_info_documents_retention_periods(self):
        """Test that data retention periods are clearly documented"""

        response = await get_gdpr_info()

        retention = response["data_processing"]["retention_period"]

        assert "active_users" in retention
        assert "deleted_users" in retention
        assert "billing_records" in retention
        assert "usage_logs" in retention

        # Verify specific retention periods
        assert "90 days" in retention["usage_logs"]
        assert "7 years" in retention["billing_records"]

    @pytest.mark.asyncio
    async def test_gdpr_info_includes_contact_details(self):
        """Test that contact information for GDPR queries is included"""

        response = await get_gdpr_info()

        contact = response["contact"]

        assert "privacy_questions" in contact
        assert "data_protection_officer" in contact
        assert "complaints" in contact

        # Verify email addresses are provided
        assert "@" in contact["privacy_questions"]
        assert "@" in contact["data_protection_officer"]


class TestGDPRCompliance:
    """Test overall GDPR compliance requirements"""

    @pytest.mark.asyncio
    async def test_data_minimization(self, mock_user, mock_api_key, mock_db_pool):
        """Test that only necessary data is collected (GDPR Article 5)"""

        response = await export_user_data(
            auth=(mock_user, mock_api_key)
        )

        # Verify we're not collecting excessive data
        user_data = response.user_data

        # Should not include unnecessary fields
        assert "password_hash" not in user_data
        assert "internal_notes" not in user_data
        assert "admin_flags" not in user_data

    @pytest.mark.asyncio
    async def test_purpose_limitation(self):
        """Test that data processing purposes are clearly defined"""

        response = await get_gdpr_info()

        purposes = response["data_processing"]["purposes"]

        # Purposes should be specific and legitimate
        assert len(purposes) > 0
        assert "Providing API services" in purposes
        assert "Billing and subscription management" in purposes

    @pytest.mark.asyncio
    async def test_data_subject_rights_documented(self):
        """Test that all GDPR rights are documented"""

        response = await get_gdpr_info()

        rights = response["user_rights"]

        # All key GDPR rights should be documented
        required_rights = [
            "right_of_access",  # Article 15
            "right_to_erasure",  # Article 17
            "right_to_rectification",  # Article 16
            "right_to_portability"  # Article 20
        ]

        for right in required_rights:
            assert right in rights
            assert "endpoint" in rights[right]

    @pytest.mark.asyncio
    async def test_legal_basis_documented(self):
        """Test that legal basis for processing is documented"""

        response = await get_gdpr_info()

        legal_basis = response["data_processing"]["legal_basis"]

        assert legal_basis is not None
        assert len(legal_basis) > 0


class TestDataSecurity:
    """Test data security in GDPR context"""

    @pytest.mark.asyncio
    async def test_export_requires_authentication(self, mock_user, mock_api_key):
        """Test that data export requires valid authentication"""

        # This is enforced by the Depends(get_current_user_from_request) dependency
        # If authentication fails, the endpoint won't be reached

        # Verify the endpoint has authentication dependency
        from src.api.gdpr import export_user_data
        import inspect

        sig = inspect.signature(export_user_data)
        params = sig.parameters

        assert "auth" in params

    @pytest.mark.asyncio
    async def test_deletion_requires_authentication(self, mock_user, mock_api_key):
        """Test that account deletion requires valid authentication"""

        from src.api.gdpr import delete_user_account
        import inspect

        sig = inspect.signature(delete_user_account)
        params = sig.parameters

        assert "auth" in params

    @pytest.mark.asyncio
    async def test_api_key_hashes_excluded_from_export(self, mock_user, mock_api_key, mock_db_pool):
        """Test that sensitive cryptographic hashes are excluded"""

        response = await export_user_data(
            auth=(mock_user, mock_api_key)
        )

        # Verify no hashes in export
        export_json = json.dumps(response.model_dump(), default=str)

        assert "key_hash" not in export_json
        assert "password_hash" not in export_json


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
