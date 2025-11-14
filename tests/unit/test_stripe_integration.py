"""
Unit tests for Stripe billing integration
Tests billing logic, webhook handling, and subscription management
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from src.integrations.stripe_integration import StripeBillingManager, PRICING_TIERS


class TestPricingConfiguration:
    """Test pricing tier configuration"""

    def test_all_tiers_defined(self):
        """Test that all pricing tiers are properly defined"""
        required_tiers = ["free", "starter", "professional", "enterprise"]

        for tier in required_tiers:
            assert tier in PRICING_TIERS
            assert "price_monthly" in PRICING_TIERS[tier]
            assert "requests_per_minute" in PRICING_TIERS[tier]
            assert "requests_per_month" in PRICING_TIERS[tier]

    def test_tier_pricing_values(self):
        """Test that tier pricing is correct"""
        assert PRICING_TIERS["free"]["price_monthly"] == 0
        assert PRICING_TIERS["starter"]["price_monthly"] == 49
        assert PRICING_TIERS["professional"]["price_monthly"] == 199
        assert PRICING_TIERS["enterprise"]["price_monthly"] == 999

    def test_tier_limits_increase(self):
        """Test that rate limits increase with tier"""
        free_rpm = PRICING_TIERS["free"]["requests_per_minute"]
        starter_rpm = PRICING_TIERS["starter"]["requests_per_minute"]
        pro_rpm = PRICING_TIERS["professional"]["requests_per_minute"]
        ent_rpm = PRICING_TIERS["enterprise"]["requests_per_minute"]

        assert free_rpm < starter_rpm < pro_rpm < ent_rpm

    def test_monthly_limits_realistic(self):
        """Test that monthly limits are realistic for tier pricing"""
        # Starter tier should give good value
        starter_monthly = PRICING_TIERS["starter"]["requests_per_month"]
        assert starter_monthly >= 10000  # At least 10k requests/month

        # Enterprise should be generous
        ent_monthly = PRICING_TIERS["enterprise"]["requests_per_month"]
        assert ent_monthly >= 100000  # At least 100k requests/month


class TestCheckoutSessionCreation:
    """Test Stripe checkout session creation"""

    @pytest.mark.asyncio
    @patch('stripe.checkout.Session.create')
    async def test_create_checkout_session_starter(self, mock_stripe):
        """Test creating checkout session for starter tier"""
        mock_stripe.return_value = Mock(id="cs_test123", url="https://checkout.stripe.com/test")

        manager = StripeBillingManager(api_key="sk_test_123")
        session = await manager.create_checkout_session(
            user_id=123,
            email="test@example.com",
            tier="starter",
            success_url="https://example.com/success",
            cancel_url="https://example.com/cancel"
        )

        # Verify Stripe was called correctly
        mock_stripe.assert_called_once()
        call_args = mock_stripe.call_args[1]

        assert call_args["mode"] == "subscription"
        assert call_args["customer_email"] == "test@example.com"
        assert call_args["success_url"] == "https://example.com/success"
        assert call_args["cancel_url"] == "https://example.com/cancel"

        # Verify return value
        assert session["id"] == "cs_test123"
        assert session["url"] == "https://checkout.stripe.com/test"

    @pytest.mark.asyncio
    async def test_create_checkout_invalid_tier(self):
        """Test creating checkout with invalid tier"""
        manager = StripeBillingManager(api_key="sk_test_123")

        with pytest.raises(ValueError, match="Invalid tier"):
            await manager.create_checkout_session(
                user_id=123,
                email="test@example.com",
                tier="invalid_tier",
                success_url="https://example.com/success",
                cancel_url="https://example.com/cancel"
            )

    @pytest.mark.asyncio
    async def test_create_checkout_free_tier(self):
        """Test creating checkout for free tier (should fail)"""
        manager = StripeBillingManager(api_key="sk_test_123")

        with pytest.raises(ValueError, match="Cannot create checkout for free tier"):
            await manager.create_checkout_session(
                user_id=123,
                email="test@example.com",
                tier="free",
                success_url="https://example.com/success",
                cancel_url="https://example.com/cancel"
            )


class TestWebhookHandling:
    """Test Stripe webhook event handling"""

    @pytest.mark.asyncio
    async def test_handle_subscription_created(self):
        """Test handling subscription.created webhook"""
        manager = StripeBillingManager(api_key="sk_test_123")

        event = {
            "type": "customer.subscription.created",
            "data": {
                "object": {
                    "id": "sub_123",
                    "customer": "cus_123",
                    "status": "active",
                    "items": {
                        "data": [{
                            "price": {"id": "price_starter"}
                        }]
                    }
                }
            }
        }

        result = await manager.handle_webhook_event(event)

        assert result["status"] == "processed"
        assert result["event_type"] == "customer.subscription.created"

    @pytest.mark.asyncio
    async def test_handle_subscription_updated(self):
        """Test handling subscription.updated webhook"""
        manager = StripeBillingManager(api_key="sk_test_123")

        event = {
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_123",
                    "customer": "cus_123",
                    "status": "active",
                    "items": {
                        "data": [{
                            "price": {"id": "price_professional"}
                        }]
                    }
                }
            }
        }

        result = await manager.handle_webhook_event(event)

        assert result["status"] == "processed"
        # Should update user's tier to professional

    @pytest.mark.asyncio
    async def test_handle_subscription_deleted(self):
        """Test handling subscription.deleted webhook"""
        manager = StripeBillingManager(api_key="sk_test_123")

        event = {
            "type": "customer.subscription.deleted",
            "data": {
                "object": {
                    "id": "sub_123",
                    "customer": "cus_123",
                    "status": "canceled"
                }
            }
        }

        result = await manager.handle_webhook_event(event)

        assert result["status"] == "processed"
        # Should downgrade user to free tier

    @pytest.mark.asyncio
    async def test_handle_payment_failed(self):
        """Test handling invoice.payment_failed webhook"""
        manager = StripeBillingManager(api_key="sk_test_123")

        event = {
            "type": "invoice.payment_failed",
            "data": {
                "object": {
                    "id": "in_123",
                    "customer": "cus_123",
                    "amount_due": 4900,
                    "attempt_count": 2
                }
            }
        }

        result = await manager.handle_webhook_event(event)

        assert result["status"] == "processed"
        # Should notify user or take action based on attempt count

    @pytest.mark.asyncio
    async def test_handle_unknown_event_type(self):
        """Test handling unknown webhook event type"""
        manager = StripeBillingManager(api_key="sk_test_123")

        event = {
            "type": "unknown.event.type",
            "data": {"object": {}}
        }

        result = await manager.handle_webhook_event(event)

        # Should not error, just log and skip
        assert result["status"] in ["skipped", "ignored"]


class TestWebhookSignatureVerification:
    """Test webhook signature verification"""

    def test_verify_signature_valid(self):
        """Test verifying valid webhook signature"""
        manager = StripeBillingManager(api_key="sk_test_123")

        payload = '{"event": "test"}'
        signature = "t=1234567890,v1=valid_signature_hash"
        secret = "whsec_test"

        # This would call Stripe's verification in real implementation
        # Here we're testing the wrapper logic
        with patch('stripe.Webhook.construct_event') as mock_verify:
            mock_verify.return_value = {"event": "test"}

            event = manager.verify_webhook_signature(payload, signature, secret)

            assert event == {"event": "test"}
            mock_verify.assert_called_once_with(payload, signature, secret)

    def test_verify_signature_invalid(self):
        """Test verifying invalid webhook signature"""
        manager = StripeBillingManager(api_key="sk_test_123")

        payload = '{"event": "test"}'
        signature = "invalid_signature"
        secret = "whsec_test"

        with patch('stripe.Webhook.construct_event', side_effect=ValueError("Invalid signature")):
            with pytest.raises(ValueError, match="Invalid signature"):
                manager.verify_webhook_signature(payload, signature, secret)


class TestSubscriptionManagement:
    """Test subscription management operations"""

    @pytest.mark.asyncio
    @patch('stripe.Subscription.retrieve')
    async def test_get_subscription_status(self, mock_retrieve):
        """Test getting subscription status"""
        mock_retrieve.return_value = Mock(
            id="sub_123",
            status="active",
            current_period_end=1234567890
        )

        manager = StripeBillingManager(api_key="sk_test_123")
        status = await manager.get_subscription_status("sub_123")

        assert status["id"] == "sub_123"
        assert status["status"] == "active"
        assert status["current_period_end"] == 1234567890

    @pytest.mark.asyncio
    @patch('stripe.Subscription.modify')
    async def test_cancel_subscription(self, mock_modify):
        """Test canceling subscription"""
        mock_modify.return_value = Mock(
            id="sub_123",
            status="canceled",
            canceled_at=1234567890
        )

        manager = StripeBillingManager(api_key="sk_test_123")
        result = await manager.cancel_subscription("sub_123")

        assert result["status"] == "canceled"
        mock_modify.assert_called_once_with("sub_123", cancel_at_period_end=True)

    @pytest.mark.asyncio
    @patch('stripe.Subscription.modify')
    async def test_upgrade_subscription(self, mock_modify):
        """Test upgrading subscription tier"""
        mock_modify.return_value = Mock(
            id="sub_123",
            status="active"
        )

        manager = StripeBillingManager(api_key="sk_test_123")
        result = await manager.upgrade_subscription(
            subscription_id="sub_123",
            new_tier="professional"
        )

        assert result["status"] == "active"
        mock_modify.assert_called_once()


class TestUsageMetering:
    """Test usage metering and reporting"""

    @pytest.mark.asyncio
    async def test_record_usage(self):
        """Test recording API usage"""
        manager = StripeBillingManager(api_key="sk_test_123")

        await manager.record_usage(
            user_id=123,
            requests=10,
            timestamp=datetime.utcnow()
        )

        # Should store usage in database or Stripe
        # Verify through mocked database calls

    @pytest.mark.asyncio
    async def test_get_usage_current_month(self):
        """Test getting current month usage"""
        manager = StripeBillingManager(api_key="sk_test_123")

        with patch.object(manager, 'db') as mock_db:
            mock_db.get_usage.return_value = 1500

            usage = await manager.get_monthly_usage(user_id=123)

            assert usage == 1500

    @pytest.mark.asyncio
    async def test_check_usage_limit_within(self):
        """Test checking if user is within usage limit"""
        manager = StripeBillingManager(api_key="sk_test_123")

        with patch.object(manager, 'get_monthly_usage', return_value=5000):
            within_limit = await manager.is_within_usage_limit(
                user_id=123,
                tier="starter"  # 10000/month limit
            )

            assert within_limit is True

    @pytest.mark.asyncio
    async def test_check_usage_limit_exceeded(self):
        """Test checking if user exceeded usage limit"""
        manager = StripeBillingManager(api_key="sk_test_123")

        with patch.object(manager, 'get_monthly_usage', return_value=15000):
            within_limit = await manager.is_within_usage_limit(
                user_id=123,
                tier="starter"  # 10000/month limit
            )

            assert within_limit is False


class TestPriceCalculation:
    """Test price calculation and prorating"""

    def test_calculate_prorated_amount(self):
        """Test calculating prorated amount for mid-cycle upgrade"""
        manager = StripeBillingManager(api_key="sk_test_123")

        # Upgrade from starter ($49) to professional ($199) halfway through month
        prorated = manager.calculate_prorated_amount(
            current_tier="starter",
            new_tier="professional",
            days_remaining=15,
            days_in_period=30
        )

        # Should charge difference prorated for 15/30 days
        expected = (199 - 49) * (15 / 30)
        assert abs(prorated - expected) < 0.01

    def test_calculate_annual_discount(self):
        """Test calculating annual subscription discount"""
        manager = StripeBillingManager(api_key="sk_test_123")

        monthly_price = 199
        annual_price = manager.calculate_annual_price(monthly_price)

        # Should offer ~20% discount for annual
        expected = monthly_price * 12 * 0.8
        assert abs(annual_price - expected) < 1.0


# Note: Some methods assume database access or async operations
# Adjust tests based on actual StripeBillingManager implementation
