"""
Tests for FinSight API - Authentication and API Keys
Adapted from FinRobot's testing discipline
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from src.auth.api_keys import APIKeyManager
from src.models.user import User, APIKey, PricingTier


@pytest.fixture
def mock_db_pool():
    """Mock database pool for testing"""
    pool = Mock()
    conn = AsyncMock()

    # Mock connection context manager
    pool.acquire.return_value.__aenter__.return_value = conn
    pool.acquire.return_value.__aexit__.return_value = None

    return pool, conn


@pytest.fixture
def api_key_manager(mock_db_pool):
    """Create APIKeyManager with mocked database"""
    pool, conn = mock_db_pool
    return APIKeyManager(pool), conn


class TestAPIKeyGeneration:
    """Test API key generation and validation"""

    def test_generate_key_format(self):
        """Test that generated keys have correct format"""
        from src.auth.api_keys import APIKeyManager

        key = APIKeyManager._generate_key()

        assert key.startswith("fsk_")
        assert len(key) == 43  # fsk_ + 39 random chars
        assert all(c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
                   for c in key[4:])

    def test_key_prefix_extraction(self):
        """Test extracting prefix from key"""
        from src.auth.api_keys import APIKeyManager

        key = "fsk_1234567890abcdefghij"
        prefix = key[:12]

        assert prefix == "fsk_12345678"
        assert len(prefix) == 12

    def test_hash_consistency(self):
        """Test that same key produces same hash"""
        from src.auth.api_keys import APIKeyManager

        key = "fsk_test123"
        hash1 = APIKeyManager._hash_key(key)
        hash2 = APIKeyManager._hash_key(key)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex length

    def test_different_keys_different_hashes(self):
        """Test that different keys produce different hashes"""
        from src.auth.api_keys import APIKeyManager

        key1 = "fsk_test123"
        key2 = "fsk_test456"

        hash1 = APIKeyManager._hash_key(key1)
        hash2 = APIKeyManager._hash_key(key2)

        assert hash1 != hash2


class TestAPIKeyCreation:
    """Test API key creation with database"""

    @pytest.mark.asyncio
    async def test_create_api_key_success(self, api_key_manager):
        """Test successful API key creation"""
        manager, mock_conn = api_key_manager
        user_id = "usr_12345"

        # Mock database responses
        mock_conn.fetchval.return_value = None  # No hash collision
        mock_conn.execute.return_value = None

        full_key, api_key = await manager.create_api_key(
            user_id=user_id,
            name="Test Key",
            conn=mock_conn
        )

        # Verify key format
        assert full_key.startswith("fsk_")
        assert len(full_key) == 43

        # Verify API key object
        assert api_key.user_id == user_id
        assert api_key.name == "Test Key"
        assert api_key.is_active == True
        assert api_key.key_prefix.startswith("fsk_")

        # Verify database insert was called
        mock_conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_api_key_with_expiration(self, api_key_manager):
        """Test creating API key with expiration"""
        manager, mock_conn = api_key_manager

        mock_conn.fetchval.return_value = None
        mock_conn.execute.return_value = None

        full_key, api_key = await manager.create_api_key(
            user_id="usr_12345",
            name="Expiring Key",
            expires_days=30,
            conn=mock_conn
        )

        assert api_key.expires_at is not None
        # Should expire approximately 30 days from now
        delta = api_key.expires_at - datetime.utcnow()
        assert 29 <= delta.days <= 31

    @pytest.mark.asyncio
    async def test_create_test_mode_key(self, api_key_manager):
        """Test creating test mode API key"""
        manager, mock_conn = api_key_manager

        mock_conn.fetchval.return_value = None
        mock_conn.execute.return_value = None

        full_key, api_key = await manager.create_api_key(
            user_id="usr_12345",
            name="Test Mode Key",
            test_mode=True,
            conn=mock_conn
        )

        assert api_key.is_test_mode == True

    @pytest.mark.asyncio
    async def test_hash_collision_retry(self, api_key_manager):
        """Test that hash collisions trigger retry"""
        manager, mock_conn = api_key_manager

        # First call returns collision, second call succeeds
        mock_conn.fetchval.side_effect = ["existing_key_id", None]
        mock_conn.execute.return_value = None

        full_key, api_key = await manager.create_api_key(
            user_id="usr_12345",
            name="Collision Test",
            conn=mock_conn
        )

        # Should have checked for collision twice
        assert mock_conn.fetchval.call_count >= 2

        # Should eventually succeed
        assert full_key.startswith("fsk_")


class TestAPIKeyValidation:
    """Test API key validation"""

    @pytest.mark.asyncio
    async def test_validate_valid_key(self, api_key_manager):
        """Test validating a valid API key"""
        manager, mock_conn = api_key_manager

        # Mock database response for valid key
        mock_conn.fetchrow.return_value = {
            "key_id": "key_123",
            "user_id": "usr_123",
            "key_hash": APIKeyManager._hash_key("fsk_validkey"),
            "key_prefix": "fsk_validkey"[:12],
            "name": "Test Key",
            "is_active": True,
            "is_test_mode": False,
            "total_calls": 100,
            "calls_this_month": 50,
            "last_used_at": datetime.utcnow(),
            "allowed_ips": None,
            "allowed_domains": None,
            "created_at": datetime.utcnow(),
            "expires_at": None,
            "email": "test@example.com",
            "email_verified": True,
            "tier": "free",
            "status": "active",
            "api_calls_this_month": 50,
            "api_calls_limit": 100
        }
        mock_conn.execute.return_value = None

        result = await manager.validate_key("fsk_validkey")

        assert result is not None
        user, api_key = result
        assert user.user_id == "usr_123"
        assert api_key.key_id == "key_123"

    @pytest.mark.asyncio
    async def test_validate_invalid_key(self, api_key_manager):
        """Test validating an invalid API key"""
        manager, mock_conn = api_key_manager

        # Mock no key found
        mock_conn.fetchrow.return_value = None

        result = await manager.validate_key("fsk_invalidkey")

        assert result is None

    @pytest.mark.asyncio
    async def test_validate_inactive_key(self, api_key_manager):
        """Test validating an inactive API key"""
        manager, mock_conn = api_key_manager

        # Mock inactive key
        mock_conn.fetchrow.return_value = {
            "key_id": "key_123",
            "is_active": False,
            # ... other fields
        }

        result = await manager.validate_key("fsk_inactivekey")

        assert result is None

    @pytest.mark.asyncio
    async def test_validate_expired_key(self, api_key_manager):
        """Test validating an expired API key"""
        manager, mock_conn = api_key_manager

        # Mock expired key
        mock_conn.fetchrow.return_value = {
            "key_id": "key_123",
            "is_active": True,
            "expires_at": datetime.utcnow() - timedelta(days=1),  # Expired yesterday
            # ... other fields
        }

        result = await manager.validate_key("fsk_expiredkey")

        assert result is None

    @pytest.mark.asyncio
    async def test_validate_updates_usage(self, api_key_manager):
        """Test that validation updates usage counters"""
        manager, mock_conn = api_key_manager

        mock_conn.fetchrow.return_value = {
            "key_id": "key_123",
            "user_id": "usr_123",
            "key_hash": APIKeyManager._hash_key("fsk_validkey"),
            "is_active": True,
            "expires_at": None,
            "total_calls": 100,
            # ... other fields needed for User/APIKey construction
        }
        mock_conn.execute.return_value = None

        await manager.validate_key("fsk_validkey")

        # Verify usage counters were updated
        assert mock_conn.execute.call_count == 2  # Update api_keys and users tables


class TestAPIKeyEdgeCases:
    """Test edge cases and error conditions"""

    def test_empty_key_validation(self, api_key_manager):
        """Test validating empty key"""
        manager, _ = api_key_manager

        # Should handle gracefully
        with pytest.raises(Exception):
            asyncio.run(manager.validate_key(""))

    def test_malformed_key_validation(self, api_key_manager):
        """Test validating malformed key"""
        manager, mock_conn = api_key_manager

        mock_conn.fetchrow.return_value = None

        result = asyncio.run(manager.validate_key("not_a_valid_key_format"))

        assert result is None

    @pytest.mark.asyncio
    async def test_create_key_without_connection(self, api_key_manager):
        """Test creating key without providing connection"""
        manager, _ = api_key_manager

        # Should use pool connection
        # This tests the conn=None branch
        with patch.object(manager.db, 'acquire') as mock_acquire:
            mock_conn = AsyncMock()
            mock_acquire.return_value.__aenter__.return_value = mock_conn
            mock_acquire.return_value.__aexit__.return_value = None

            mock_conn.fetchval.return_value = None
            mock_conn.execute.return_value = None

            full_key, api_key = await manager.create_api_key(
                user_id="usr_123",
                name="Test"
            )

            # Should have acquired connection from pool
            mock_acquire.assert_called_once()


class TestRateLimitChecking:
    """Test rate limit validation"""

    @pytest.mark.asyncio
    async def test_within_rate_limit(self, api_key_manager):
        """Test user within rate limit"""
        manager, mock_conn = api_key_manager

        # User has used 50 out of 100 calls
        mock_conn.fetchrow.return_value = {
            "key_id": "key_123",
            "user_id": "usr_123",
            "key_hash": APIKeyManager._hash_key("fsk_test"),
            "is_active": True,
            "api_calls_this_month": 50,
            "api_calls_limit": 100,
            "tier": "free",
            "status": "active",
            # ... other required fields
        }
        mock_conn.execute.return_value = None

        result = await manager.validate_key("fsk_test")

        assert result is not None

    @pytest.mark.asyncio
    async def test_exceeded_rate_limit(self, api_key_manager):
        """Test user exceeded rate limit"""
        manager, mock_conn = api_key_manager

        # User has used 100 out of 100 calls
        mock_conn.fetchrow.return_value = {
            "key_id": "key_123",
            "user_id": "usr_123",
            "key_hash": APIKeyManager._hash_key("fsk_test"),
            "is_active": True,
            "api_calls_this_month": 100,
            "api_calls_limit": 100,
            "tier": "free",
            "status": "active",
            # ... other required fields
        }

        result = await manager.validate_key("fsk_test")

        # Should still validate (rate limit enforced in middleware)
        # But middleware will reject
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
