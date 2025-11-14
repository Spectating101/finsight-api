"""
Unit tests for API key management
Tests the core business logic WITHOUT requiring a real database
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, MagicMock, patch
import hashlib

# We'll test the generate_key method directly without DB
from src.auth.api_keys import APIKeyManager


class TestAPIKeyGeneration:
    """Test API key generation logic (no DB required)"""

    def setup_method(self):
        """Setup for each test"""
        # Mock database pool
        self.mock_db_pool = Mock()
        self.manager = APIKeyManager(self.mock_db_pool)

    def test_generate_key_format(self):
        """Test that generated keys have correct format"""
        key, key_hash, key_prefix = self.manager.generate_key()

        # Should start with fsk_
        assert key.startswith("fsk_")

        # Should be at least 40 characters
        assert len(key) >= 40

        # Prefix should be first 12 chars
        assert key_prefix == key[:12]
        assert key_prefix.startswith("fsk_")

    def test_generate_key_uniqueness(self):
        """Test that generated keys are unique"""
        keys = []
        for _ in range(100):
            key, _, _ = self.manager.generate_key()
            keys.append(key)

        # All keys should be unique
        assert len(keys) == len(set(keys))

    def test_hash_deterministic(self):
        """Test that hashing is deterministic"""
        test_key = "fsk_test_key_12345"

        hash1 = hashlib.sha256(test_key.encode()).hexdigest()
        hash2 = hashlib.sha256(test_key.encode()).hexdigest()

        # Same key should produce same hash
        assert hash1 == hash2

    def test_hash_different_inputs(self):
        """Test that different keys produce different hashes"""
        key1 = "fsk_test_key_1"
        key2 = "fsk_test_key_2"

        hash1 = hashlib.sha256(key1.encode()).hexdigest()
        hash2 = hashlib.sha256(key2.encode()).hexdigest()

        # Different keys should produce different hashes
        assert hash1 != hash2

    def test_hash_length(self):
        """Test that hash has expected length (SHA256 = 64 hex chars)"""
        _, key_hash, _ = self.manager.generate_key()

        # SHA256 produces 64 character hex string
        assert len(key_hash) == 64

        # Should be valid hex
        int(key_hash, 16)  # Raises ValueError if not valid hex

    def test_prefix_extraction(self):
        """Test key prefix extraction"""
        key, _, key_prefix = self.manager.generate_key()

        # Prefix should be first 12 characters
        assert key_prefix == key[:12]
        assert len(key_prefix) == 12

    def test_key_prefix_value(self):
        """Test that key prefix is set correctly"""
        assert self.manager.key_prefix == "fsk_"


class TestAPIKeyCreation:
    """Test API key creation with mocked database"""

    def setup_method(self):
        """Setup for each test"""
        self.mock_db_pool = MagicMock()
        self.mock_conn = AsyncMock()
        self.mock_db_pool.acquire.return_value.__aenter__.return_value = self.mock_conn
        self.manager = APIKeyManager(self.mock_db_pool)

    @pytest.mark.asyncio
    async def test_create_api_key_basic(self):
        """Test basic API key creation"""
        user_id = "user_123"
        name = "Test Key"

        full_key, api_key = await self.manager.create_api_key(user_id, name)

        # Check return values
        assert full_key.startswith("fsk_")
        assert api_key.user_id == user_id
        assert api_key.name == name
        assert api_key.key_prefix.startswith("fsk_")

        # Verify database was called
        self.mock_conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_api_key_with_expiration(self):
        """Test API key creation with expiration"""
        user_id = "user_123"
        expires_days = 30

        full_key, api_key = await self.manager.create_api_key(
            user_id,
            expires_days=expires_days
        )

        # Check expiration is set
        assert api_key.expires_at is not None

        # Should be approximately 30 days from now
        expected_expiry = datetime.utcnow() + timedelta(days=expires_days)
        time_diff = abs((api_key.expires_at - expected_expiry).total_seconds())
        assert time_diff < 5  # Within 5 seconds

    @pytest.mark.asyncio
    async def test_create_test_mode_key(self):
        """Test creating test mode API key"""
        user_id = "user_123"

        full_key, api_key = await self.manager.create_api_key(
            user_id,
            test_mode=True
        )

        assert api_key.is_test_mode is True

    @pytest.mark.asyncio
    async def test_create_key_full_key_never_stored(self):
        """Test that full key is never stored in database"""
        user_id = "user_123"

        full_key, api_key = await self.manager.create_api_key(user_id)

        # Check database call - full key should not be in the call
        call_args = self.mock_conn.execute.call_args
        sql, *params = call_args[0]

        # Full key should not be in params
        assert full_key not in params

        # But hash should be
        key_hash = hashlib.sha256(full_key.encode()).hexdigest()
        assert key_hash in params


class TestAPIKeyValidation:
    """Test API key validation with mocked database"""

    def setup_method(self):
        """Setup for each test"""
        self.mock_db_pool = MagicMock()
        self.mock_conn = AsyncMock()
        self.mock_db_pool.acquire.return_value.__aenter__.return_value = self.mock_conn
        self.manager = APIKeyManager(self.mock_db_pool)

    @pytest.mark.asyncio
    async def test_validate_valid_key(self):
        """Test validating a valid API key"""
        test_key = "fsk_test_key_123"
        key_hash = hashlib.sha256(test_key.encode()).hexdigest()

        # Mock database response
        self.mock_conn.fetchrow.return_value = {
            'key_id': 'key_123',
            'user_id': 'user_123',
            'email': 'test@example.com',
            'tier': 'free',
            'status': 'active',
            'api_calls_this_month': 10,
            'api_calls_limit': 1000,
            'stripe_customer_id': None,
            'key_hash': key_hash,
            'key_prefix': test_key[:12],
            'name': 'Test Key',
            'is_active': True,
            'is_test_mode': False,
            'total_calls': 100,
            'last_used_at': None,
            'created_at': datetime.utcnow(),
            'expires_at': None
        }

        result = await self.manager.validate_key(test_key)

        assert result is not None
        user, api_key = result
        assert user.user_id == 'user_123'
        assert user.email == 'test@example.com'
        assert api_key.key_id == 'key_123'

    @pytest.mark.asyncio
    async def test_validate_invalid_key(self):
        """Test validating an invalid API key"""
        test_key = "fsk_invalid_key"

        # Mock database returning None (key not found)
        self.mock_conn.fetchrow.return_value = None

        result = await self.manager.validate_key(test_key)

        assert result is None

    @pytest.mark.asyncio
    async def test_validate_updates_last_used(self):
        """Test that validation updates last_used_at timestamp"""
        test_key = "fsk_test_key_123"
        key_hash = hashlib.sha256(test_key.encode()).hexdigest()

        self.mock_conn.fetchrow.return_value = {
            'key_id': 'key_123',
            'user_id': 'user_123',
            'email': 'test@example.com',
            'tier': 'free',
            'status': 'active',
            'api_calls_this_month': 10,
            'api_calls_limit': 1000,
            'stripe_customer_id': None,
            'key_hash': key_hash,
            'key_prefix': test_key[:12],
            'name': 'Test Key',
            'is_active': True,
            'is_test_mode': False,
            'total_calls': 100,
            'last_used_at': None,
            'created_at': datetime.utcnow(),
            'expires_at': None
        }

        await self.manager.validate_key(test_key)

        # Verify UPDATE was called to update last_used_at
        assert self.mock_conn.execute.call_count == 1


class TestAPIKeyRevocation:
    """Test API key revocation"""

    def setup_method(self):
        """Setup for each test"""
        self.mock_db_pool = MagicMock()
        self.mock_conn = AsyncMock()
        self.mock_db_pool.acquire.return_value.__aenter__.return_value = self.mock_conn
        self.manager = APIKeyManager(self.mock_db_pool)

    @pytest.mark.asyncio
    async def test_revoke_existing_key(self):
        """Test revoking an existing key"""
        key_id = "key_123"
        user_id = "user_123"

        # Mock successful revocation
        self.mock_conn.execute.return_value = "UPDATE 1"

        result = await self.manager.revoke_key(key_id, user_id)

        assert result is True

    @pytest.mark.asyncio
    async def test_revoke_nonexistent_key(self):
        """Test revoking a non-existent key"""
        key_id = "key_invalid"
        user_id = "user_123"

        # Mock no rows updated
        self.mock_conn.execute.return_value = "UPDATE 0"

        result = await self.manager.revoke_key(key_id, user_id)

        assert result is False


class TestAPIKeyRotation:
    """Test API key rotation functionality"""

    def setup_method(self):
        """Setup for each test"""
        self.mock_db_pool = MagicMock()
        self.mock_conn = AsyncMock()
        self.mock_db_pool.acquire.return_value.__aenter__.return_value = self.mock_conn
        self.manager = APIKeyManager(self.mock_db_pool)

    @pytest.mark.asyncio
    async def test_rotate_key_basic(self):
        """Test basic key rotation"""
        old_key_id = "key_old_123"
        user_id = "user_123"

        # Mock old key exists
        self.mock_conn.fetchrow.return_value = {
            'key_id': old_key_id,
            'name': 'Production Key',
            'is_test_mode': False
        }

        # Mock create_api_key call
        with patch.object(self.manager, 'create_api_key', new_callable=AsyncMock) as mock_create:
            from src.models.user import APIKey

            mock_api_key = APIKey(
                key_id='key_new_123',
                user_id=user_id,
                key_hash='hash123',
                key_prefix='fsk_new',
                name='Production Key (Rotated)',
                is_test_mode=False,
                created_at=datetime.utcnow()
            )

            mock_create.return_value = ('fsk_new_key', mock_api_key)

            new_key, new_api_key = await self.manager.rotate_key(old_key_id, user_id)

            # Check new key was created
            assert new_key.startswith('fsk_')
            assert new_api_key.key_id == 'key_new_123'
            assert '(Rotated)' in new_api_key.name

    @pytest.mark.asyncio
    async def test_rotate_invalid_key(self):
        """Test rotating non-existent key"""
        old_key_id = "key_invalid"
        user_id = "user_123"

        # Mock key not found
        self.mock_conn.fetchrow.return_value = None

        with pytest.raises(ValueError, match="API key not found"):
            await self.manager.rotate_key(old_key_id, user_id)


class TestExpiredKeyCleanup:
    """Test expired key cleanup"""

    def setup_method(self):
        """Setup for each test"""
        self.mock_db_pool = MagicMock()
        self.mock_conn = AsyncMock()
        self.mock_db_pool.acquire.return_value.__aenter__.return_value = self.mock_conn
        self.manager = APIKeyManager(self.mock_db_pool)

    @pytest.mark.asyncio
    async def test_cleanup_expired_keys(self):
        """Test cleaning up expired keys"""
        # Mock 5 keys cleaned up
        self.mock_conn.execute.return_value = "UPDATE 5"

        count = await self.manager.cleanup_expired_keys()

        assert count == 5

    @pytest.mark.asyncio
    async def test_cleanup_no_expired_keys(self):
        """Test cleanup when no expired keys"""
        self.mock_conn.execute.return_value = "UPDATE 0"

        count = await self.manager.cleanup_expired_keys()

        assert count == 0
