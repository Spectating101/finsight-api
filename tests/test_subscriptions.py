"""
Tests for FinSight API - Subscription Management and Billing
Tests for Stripe integration, webhooks, and subscription lifecycle
Adapted from FinRobot's testing discipline
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from fastapi import HTTPException

from src.api.subscriptions import (
    get_subscription_info,
    create_checkout_session,
    cancel_subscription,
    stripe_webhook,
    get_pricing_info
)
from src.billing.stripe_integration import StripeManager
from src.models.user import User, APIKey, PricingTier


@pytest.fixture
def mock_user_free():
    """Create a mock user on free tier"""
    return User(
        user_id="usr_test123",
        email="test@example.com",
        email_verified=True,
        tier=PricingTier.FREE,
        status="active",
        api_calls_this_month=50,
        api_calls_limit=100,
        stripe_customer_id=None,
        stripe_subscription_id=None,
        billing_period_start=None,
        billing_period_end=None,
        created_at=datetime.utcnow()
    )


@pytest.fixture
def mock_user_pro():
    """Create a mock user on professional tier"""
    return User(
        user_id="usr_pro123",
        email="pro@example.com",
        email_verified=True,
        tier=PricingTier.PROFESSIONAL,
        status="active",
        api_calls_this_month=500,
        api_calls_limit=10000,
        stripe_customer_id="cus_test123",
        stripe_subscription_id="sub_test123",
        billing_period_start=datetime.utcnow(),
        billing_period_end=datetime.utcnow() + timedelta(days=30),
        created_at=datetime.utcnow()
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
        total_calls=100,
        calls_this_month=50,
        created_at=datetime.utcnow()
    )


@pytest.fixture
def mock_db_pool():
    """Mock database pool"""
    pool = AsyncMock()
    conn = AsyncMock()
    pool.acquire.return_value.__aenter__.return_value = conn
    pool.acquire.return_value.__aexit__.return_value = None
    return pool, conn


@pytest.fixture
def stripe_manager(mock_db_pool):
    """Create StripeManager with mocked database"""
    pool, conn = mock_db_pool
    return StripeManager(
        api_key="sk_test_fake",
        webhook_secret="whsec_test_fake",
        db_pool=pool
    ), conn


class TestSubscriptionInfo:
    """Test subscription info endpoint"""

    @pytest.mark.asyncio
    async def test_get_subscription_info_free_tier(self, mock_user_free, mock_api_key):
        """Test getting subscription info for free tier user"""

        response = await get_subscription_info(
            auth=(mock_user_free, mock_api_key)
        )

        assert response.user_id == "usr_test123"
        assert response.tier == "free"
        assert response.status == "active"
        assert response.api_calls_this_month == 50
        assert response.api_calls_limit == 100
        assert response.stripe_subscription_id is None
        assert response.billing_period_start is None
        assert response.billing_period_end is None

    @pytest.mark.asyncio
    async def test_get_subscription_info_pro_tier(self, mock_user_pro, mock_api_key):
        """Test getting subscription info for pro tier user"""

        response = await get_subscription_info(
            auth=(mock_user_pro, mock_api_key)
        )

        assert response.user_id == "usr_pro123"
        assert response.tier == "professional"
        assert response.status == "active"
        assert response.api_calls_this_month == 500
        assert response.api_calls_limit == 10000
        assert response.stripe_subscription_id == "sub_test123"
        assert response.billing_period_start is not None
        assert response.billing_period_end is not None


class TestCheckoutSession:
    """Test checkout session creation"""

    @pytest.mark.asyncio
    async def test_create_checkout_success(self, mock_user_free, mock_api_key):
        """Test successful checkout session creation"""

        # Mock Stripe manager
        mock_stripe_mgr = AsyncMock()
        mock_stripe_mgr.create_customer.return_value = "cus_new123"

        # Mock Stripe checkout session
        mock_session = Mock()
        mock_session.id = "cs_test123"
        mock_session.url = "https://checkout.stripe.com/test123"

        from src.api.subscriptions import CreateCheckoutRequest

        request = CreateCheckoutRequest(
            tier=PricingTier.STARTER,
            success_url="https://example.com/success",
            cancel_url="https://example.com/cancel"
        )

        with patch('src.api.subscriptions.stripe.checkout.Session.create') as mock_create:
            mock_create.return_value = mock_session

            response = await create_checkout_session(
                request=request,
                auth=(mock_user_free, mock_api_key),
                stripe_mgr=mock_stripe_mgr
            )

            assert response.checkout_url == "https://checkout.stripe.com/test123"
            assert response.session_id == "cs_test123"

            # Verify Stripe session was created with correct params
            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs['mode'] == 'subscription'
            assert call_kwargs['success_url'] == "https://example.com/success"
            assert call_kwargs['cancel_url'] == "https://example.com/cancel"

    @pytest.mark.asyncio
    async def test_checkout_cannot_downgrade_to_free(self, mock_user_free, mock_api_key):
        """Test that checkout cannot be created for free tier"""

        mock_stripe_mgr = AsyncMock()

        from src.api.subscriptions import CreateCheckoutRequest

        request = CreateCheckoutRequest(
            tier=PricingTier.FREE,
            success_url="https://example.com/success",
            cancel_url="https://example.com/cancel"
        )

        with pytest.raises(HTTPException) as exc:
            await create_checkout_session(
                request=request,
                auth=(mock_user_free, mock_api_key),
                stripe_mgr=mock_stripe_mgr
            )

        assert exc.value.status_code == 400
        assert "Cannot create checkout for free tier" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_checkout_existing_subscription_redirect(self, mock_user_pro, mock_api_key):
        """Test that users with existing subscriptions are redirected"""

        mock_stripe_mgr = AsyncMock()

        from src.api.subscriptions import CreateCheckoutRequest

        request = CreateCheckoutRequest(
            tier=PricingTier.ENTERPRISE,
            success_url="https://example.com/success",
            cancel_url="https://example.com/cancel"
        )

        with pytest.raises(HTTPException) as exc:
            await create_checkout_session(
                request=request,
                auth=(mock_user_pro, mock_api_key),
                stripe_mgr=mock_stripe_mgr
            )

        assert exc.value.status_code == 400
        assert "Use /subscription/upgrade" in str(exc.value.detail)


class TestSubscriptionCancellation:
    """Test subscription cancellation"""

    @pytest.mark.asyncio
    async def test_cancel_subscription_success(self, mock_user_pro, mock_api_key):
        """Test successful subscription cancellation"""

        mock_stripe_mgr = AsyncMock()
        mock_stripe_mgr.cancel_subscription.return_value = True

        response = await cancel_subscription(
            auth=(mock_user_pro, mock_api_key),
            stripe_mgr=mock_stripe_mgr
        )

        assert response["success"] is True
        assert "end of billing period" in response["message"]

        # Verify cancel was called
        mock_stripe_mgr.cancel_subscription.assert_called_once_with("usr_pro123")

    @pytest.mark.asyncio
    async def test_cancel_free_tier_error(self, mock_user_free, mock_api_key):
        """Test that free tier users cannot cancel (no subscription)"""

        mock_stripe_mgr = AsyncMock()

        with pytest.raises(HTTPException) as exc:
            await cancel_subscription(
                auth=(mock_user_free, mock_api_key),
                stripe_mgr=mock_stripe_mgr
            )

        assert exc.value.status_code == 400
        assert "No active subscription" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_cancel_no_subscription_found(self, mock_user_pro, mock_api_key):
        """Test handling when Stripe says no subscription found"""

        mock_stripe_mgr = AsyncMock()
        mock_stripe_mgr.cancel_subscription.return_value = False

        with pytest.raises(HTTPException) as exc:
            await cancel_subscription(
                auth=(mock_user_pro, mock_api_key),
                stripe_mgr=mock_stripe_mgr
            )

        assert exc.value.status_code == 404


class TestStripeManager:
    """Test StripeManager class"""

    @pytest.mark.asyncio
    async def test_create_customer(self, stripe_manager):
        """Test Stripe customer creation"""

        manager, mock_conn = stripe_manager

        mock_customer = Mock()
        mock_customer.id = "cus_new123"

        with patch('stripe.Customer.create') as mock_create:
            mock_create.return_value = mock_customer

            customer_id = await manager.create_customer(
                user_id="usr_123",
                email="test@example.com",
                company_name="Test Corp"
            )

            assert customer_id == "cus_new123"

            # Verify Stripe customer was created
            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs['email'] == "test@example.com"
            assert call_kwargs['metadata']['user_id'] == "usr_123"
            assert call_kwargs['metadata']['company_name'] == "Test Corp"

            # Verify database was updated
            mock_conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_subscription_in_stripe(self, stripe_manager):
        """Test cancelling subscription in Stripe"""

        manager, mock_conn = stripe_manager

        # Mock database response
        mock_conn.fetchrow.return_value = {
            "stripe_subscription_id": "sub_123",
            "tier": "professional"
        }

        with patch('stripe.Subscription.modify') as mock_modify:
            success = await manager.cancel_subscription("usr_123")

            assert success is True

            # Verify Stripe subscription was modified
            mock_modify.assert_called_once_with(
                "sub_123",
                cancel_at_period_end=True
            )

            # Verify history was logged
            assert mock_conn.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_cancel_subscription_no_subscription(self, stripe_manager):
        """Test cancelling when no subscription exists"""

        manager, mock_conn = stripe_manager

        # Mock no subscription
        mock_conn.fetchrow.return_value = None

        success = await manager.cancel_subscription("usr_123")

        assert success is False


class TestWebhooks:
    """Test Stripe webhook handling"""

    @pytest.mark.asyncio
    async def test_webhook_signature_verification(self, stripe_manager):
        """Test that webhook signature is verified"""

        manager, mock_conn = stripe_manager

        payload = b'{"id": "evt_test", "type": "customer.subscription.created"}'
        signature = "fake_signature"

        mock_event = Mock()
        mock_event.id = "evt_test"
        mock_event.type = "customer.subscription.created"
        mock_event.data = Mock()
        mock_event.data.object = Mock()
        mock_event.data.object.metadata = {}
        mock_event.to_dict = lambda: {"id": "evt_test"}

        # Mock no existing event (first time receiving)
        mock_conn.fetchrow.return_value = None

        with patch('stripe.Webhook.construct_event') as mock_construct:
            mock_construct.return_value = mock_event

            result = await manager.handle_webhook(payload, signature)

            # Verify signature was checked
            mock_construct.assert_called_once_with(
                payload, signature, "whsec_test_fake"
            )

            assert result["status"] == "success"
            assert result["event_type"] == "customer.subscription.created"

    @pytest.mark.asyncio
    async def test_webhook_idempotency(self, stripe_manager):
        """Test that duplicate webhooks are handled correctly"""

        manager, mock_conn = stripe_manager

        payload = b'{"id": "evt_test", "type": "customer.subscription.created"}'
        signature = "fake_signature"

        mock_event = Mock()
        mock_event.id = "evt_test"
        mock_event.type = "customer.subscription.created"

        # Mock existing event (duplicate)
        mock_conn.fetchrow.return_value = {
            "event_id": "evt_test",
            "processed": True,
            "processed_at": datetime.utcnow()
        }

        with patch('stripe.Webhook.construct_event') as mock_construct:
            mock_construct.return_value = mock_event

            result = await manager.handle_webhook(payload, signature)

            assert result["status"] == "duplicate"
            assert result["event_id"] == "evt_test"

    @pytest.mark.asyncio
    async def test_webhook_subscription_deleted_downgrades_user(self, stripe_manager):
        """Test that subscription.deleted event downgrades user"""

        manager, mock_conn = stripe_manager

        payload = b'{"id": "evt_test", "type": "customer.subscription.deleted"}'
        signature = "fake_signature"

        mock_subscription = Mock()
        mock_subscription.id = "sub_123"
        mock_subscription.metadata = {"user_id": "usr_123"}

        mock_event = Mock()
        mock_event.id = "evt_test"
        mock_event.type = "customer.subscription.deleted"
        mock_event.data = Mock()
        mock_event.data.object = mock_subscription
        mock_event.to_dict = lambda: {"id": "evt_test"}

        # Mock no existing event
        mock_conn.fetchrow.return_value = None

        with patch('stripe.Webhook.construct_event') as mock_construct:
            mock_construct.return_value = mock_event

            result = await manager.handle_webhook(payload, signature)

            # Verify user was downgraded
            assert any(
                "tier = 'free'" in str(call)
                for call in mock_conn.execute.call_args_list
            )

    @pytest.mark.asyncio
    async def test_webhook_payment_succeeded_resets_usage(self, stripe_manager):
        """Test that payment succeeded resets monthly usage"""

        manager, mock_conn = stripe_manager

        payload = b'{"id": "evt_test", "type": "invoice.payment_succeeded"}'
        signature = "fake_signature"

        mock_invoice = Mock()
        mock_invoice.customer = "cus_123"

        mock_event = Mock()
        mock_event.id = "evt_test"
        mock_event.type = "invoice.payment_succeeded"
        mock_event.data = Mock()
        mock_event.data.object = mock_invoice
        mock_event.to_dict = lambda: {"id": "evt_test"}

        # Mock no existing event
        mock_conn.fetchrow.return_value = None

        with patch('stripe.Webhook.construct_event') as mock_construct:
            mock_construct.return_value = mock_event

            result = await manager.handle_webhook(payload, signature)

            # Verify usage was reset
            assert any(
                "api_calls_this_month = 0" in str(call)
                for call in mock_conn.execute.call_args_list
            )

    @pytest.mark.asyncio
    async def test_webhook_payment_failed_suspends_account(self, stripe_manager):
        """Test that failed payment suspends account"""

        manager, mock_conn = stripe_manager

        payload = b'{"id": "evt_test", "type": "invoice.payment_failed"}'
        signature = "fake_signature"

        mock_invoice = Mock()
        mock_invoice.customer = "cus_123"

        mock_event = Mock()
        mock_event.id = "evt_test"
        mock_event.type = "invoice.payment_failed"
        mock_event.data = Mock()
        mock_event.data.object = mock_invoice
        mock_event.to_dict = lambda: {"id": "evt_test"}

        # Mock no existing event
        mock_conn.fetchrow.return_value = None

        with patch('stripe.Webhook.construct_event') as mock_construct:
            mock_construct.return_value = mock_event

            result = await manager.handle_webhook(payload, signature)

            # Verify account was suspended
            assert any(
                "status = 'suspended'" in str(call)
                for call in mock_conn.execute.call_args_list
            )


class TestPricingInfo:
    """Test pricing info endpoint"""

    @pytest.mark.asyncio
    async def test_get_pricing_info(self):
        """Test getting pricing tier information"""

        response = await get_pricing_info()

        # Verify structure
        assert "tiers" in response
        assert "features_by_tier" in response

        # Verify all tiers are present
        tiers = response["tiers"]
        assert "free" in tiers
        assert "starter" in tiers
        assert "professional" in tiers
        assert "enterprise" in tiers

        # Verify each tier has price and limits
        for tier_name, tier_data in tiers.items():
            assert "price" in tier_data
            assert "limits" in tier_data
            assert "api_calls_per_month" in tier_data["limits"]

        # Verify features are listed
        features = response["features_by_tier"]
        assert len(features["free"]) > 0
        assert len(features["professional"]) > len(features["free"])


class TestWebhookEndpoint:
    """Test the webhook HTTP endpoint"""

    @pytest.mark.asyncio
    async def test_webhook_endpoint_success(self):
        """Test successful webhook processing via HTTP endpoint"""

        mock_request = AsyncMock()
        mock_request.body.return_value = b'{"test": "payload"}'

        mock_stripe_mgr = AsyncMock()
        mock_stripe_mgr.handle_webhook.return_value = {
            "status": "success",
            "event_type": "customer.subscription.created"
        }

        response = await stripe_webhook(
            request=mock_request,
            stripe_signature="test_sig",
            stripe_mgr=mock_stripe_mgr
        )

        assert response["success"] is True

        # Verify webhook was processed
        mock_stripe_mgr.handle_webhook.assert_called_once_with(
            b'{"test": "payload"}',
            "test_sig"
        )

    @pytest.mark.asyncio
    async def test_webhook_endpoint_failure(self):
        """Test webhook endpoint when processing fails"""

        mock_request = AsyncMock()
        mock_request.body.return_value = b'{"test": "payload"}'

        mock_stripe_mgr = AsyncMock()
        mock_stripe_mgr.handle_webhook.side_effect = Exception("Processing error")

        with pytest.raises(HTTPException) as exc:
            await stripe_webhook(
                request=mock_request,
                stripe_signature="test_sig",
                stripe_mgr=mock_stripe_mgr
            )

        assert exc.value.status_code == 400


class TestSubscriptionLifecycle:
    """Test complete subscription lifecycle"""

    @pytest.mark.asyncio
    async def test_full_upgrade_flow(self, stripe_manager):
        """Test complete upgrade flow from free to paid"""

        manager, mock_conn = stripe_manager

        # 1. User starts on free tier
        user_id = "usr_123"
        email = "test@example.com"

        # 2. Create Stripe customer
        mock_customer = Mock()
        mock_customer.id = "cus_123"

        with patch('stripe.Customer.create') as mock_create_customer:
            mock_create_customer.return_value = mock_customer

            customer_id = await manager.create_customer(user_id, email)
            assert customer_id == "cus_123"

        # 3. Create subscription
        mock_conn.fetchrow.return_value = {
            "stripe_customer_id": "cus_123",
            "email": email,
            "company_name": None
        }

        mock_subscription = Mock()
        mock_subscription.id = "sub_123"
        mock_subscription.status = "active"
        mock_subscription.current_period_start = int(datetime.utcnow().timestamp())
        mock_subscription.current_period_end = int((datetime.utcnow() + timedelta(days=30)).timestamp())

        with patch('stripe.PaymentMethod.attach'):
            with patch('stripe.Customer.modify'):
                with patch('stripe.Subscription.create') as mock_create_sub:
                    mock_create_sub.return_value = mock_subscription

                    result = await manager.create_subscription(
                        user_id=user_id,
                        tier=PricingTier.PROFESSIONAL,
                        payment_method_id="pm_123"
                    )

                    assert result["subscription_id"] == "sub_123"
                    assert result["status"] == "active"

        # 4. Later, user cancels
        mock_conn.fetchrow.return_value = {
            "stripe_subscription_id": "sub_123",
            "tier": "professional"
        }

        with patch('stripe.Subscription.modify') as mock_modify:
            success = await manager.cancel_subscription(user_id)
            assert success is True
            mock_modify.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
