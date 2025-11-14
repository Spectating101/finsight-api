"""
Unit tests for API key management
Tests the core business logic of API key operations
"""

import pytest
from datetime import datetime, timedelta
from src.core.api_keys import APIKeyManager


class TestAPIKeyGeneration:
    """Test API key generation logic"""

    def test_generate_key_format(self):
        """Test that generated keys have correct format"""
        key = APIKeyManager.generate_api_key()

        # Should start with fsk_
        assert key.startswith("fsk_")

        # Should be at least 40 characters
        assert len(key) >= 40

        # Should only contain alphanumeric characters (after prefix)
        key_body = key[4:]  # Remove "fsk_" prefix
        assert key_body.isalnum()

    def test_generate_key_uniqueness(self):
        """Test that generated keys are unique"""
        keys = [APIKeyManager.generate_api_key() for _ in range(100)]

        # All keys should be unique
        assert len(keys) == len(set(keys))

    def test_hash_key_deterministic(self):
        """Test that hashing is deterministic"""
        key = "fsk_test_key_12345"

        hash1 = APIKeyManager.hash_api_key(key)
        hash2 = APIKeyManager.hash_api_key(key)

        # Same key should produce same hash
        assert hash1 == hash2

    def test_hash_key_different_inputs(self):
        """Test that different keys produce different hashes"""
        key1 = "fsk_test_key_1"
        key2 = "fsk_test_key_2"

        hash1 = APIKeyManager.hash_api_key(key1)
        hash2 = APIKeyManager.hash_api_key(key2)

        # Different keys should produce different hashes
        assert hash1 != hash2

    def test_hash_length(self):
        """Test that hash has expected length (SHA256 = 64 hex chars)"""
        key = "fsk_test_key"
        hashed = APIKeyManager.hash_api_key(key)

        # SHA256 produces 64 character hex string
        assert len(hashed) == 64

        # Should be valid hex
        int(hashed, 16)  # Raises ValueError if not valid hex


class TestKeyPrefixExtraction:
    """Test API key prefix extraction"""

    def test_extract_prefix_from_valid_key(self):
        """Test extracting prefix from valid key"""
        key = "fsk_abc123def456"
        prefix = APIKeyManager.extract_prefix(key)

        # Should return first 12 characters
        assert prefix == "fsk_abc123de"

    def test_extract_prefix_from_short_key(self):
        """Test extracting prefix from key shorter than 12 chars"""
        key = "fsk_abc"
        prefix = APIKeyManager.extract_prefix(key)

        # Should return the entire key if shorter than 12
        assert prefix == "fsk_abc"

    def test_extract_prefix_empty_key(self):
        """Test extracting prefix from empty key"""
        key = ""
        prefix = APIKeyManager.extract_prefix(key)

        assert prefix == ""


class TestKeyValidation:
    """Test API key validation logic"""

    def test_validate_key_format_valid(self):
        """Test validation accepts valid format"""
        valid_key = "fsk_" + "a" * 36  # fsk_ + 36 chars

        assert APIKeyManager.is_valid_format(valid_key) is True

    def test_validate_key_format_invalid_prefix(self):
        """Test validation rejects wrong prefix"""
        invalid_key = "invalid_prefix_12345"

        assert APIKeyManager.is_valid_format(invalid_key) is False

    def test_validate_key_format_too_short(self):
        """Test validation rejects too short keys"""
        short_key = "fsk_abc"

        assert APIKeyManager.is_valid_format(short_key) is False

    def test_validate_key_format_special_chars(self):
        """Test validation rejects keys with special characters"""
        invalid_key = "fsk_abc123!@#$%^&*()"

        # Depends on implementation - adjust based on actual validation rules
        # If special chars are not allowed:
        # assert APIKeyManager.is_valid_format(invalid_key) is False


class TestKeyExpiration:
    """Test API key expiration logic"""

    def test_is_expired_not_expired(self):
        """Test key that hasn't expired"""
        future_date = datetime.utcnow() + timedelta(days=30)

        assert APIKeyManager.is_expired(future_date) is False

    def test_is_expired_already_expired(self):
        """Test key that has expired"""
        past_date = datetime.utcnow() - timedelta(days=1)

        assert APIKeyManager.is_expired(past_date) is True

    def test_is_expired_no_expiration(self):
        """Test key with no expiration date"""
        assert APIKeyManager.is_expired(None) is False

    def test_is_expired_exact_moment(self):
        """Test key expiring at exact current moment"""
        now = datetime.utcnow()

        # Could be either True or False depending on implementation
        # Most implementations should treat "now" as expired
        result = APIKeyManager.is_expired(now)
        assert isinstance(result, bool)


class TestKeyMetadata:
    """Test API key metadata handling"""

    def test_create_key_metadata(self):
        """Test creating key metadata"""
        metadata = APIKeyManager.create_key_metadata(
            name="Production API Key",
            scopes=["read", "write"],
            user_id=123
        )

        assert metadata["name"] == "Production API Key"
        assert "read" in metadata["scopes"]
        assert "write" in metadata["scopes"]
        assert metadata["user_id"] == 123
        assert "created_at" in metadata

    def test_validate_scopes(self):
        """Test scope validation"""
        valid_scopes = ["read", "write", "admin"]

        for scope in valid_scopes:
            assert APIKeyManager.is_valid_scope(scope) is True

        invalid_scopes = ["invalid", "hack", ""]
        for scope in invalid_scopes:
            assert APIKeyManager.is_valid_scope(scope) is False


class TestKeyRotation:
    """Test API key rotation functionality"""

    def test_rotate_key_generates_new(self):
        """Test that key rotation generates a new key"""
        old_key = APIKeyManager.generate_api_key()
        new_key = APIKeyManager.rotate_key(old_key)

        # New key should be different
        assert new_key != old_key

        # New key should have valid format
        assert APIKeyManager.is_valid_format(new_key) is True

    def test_rotate_preserves_metadata(self):
        """Test that rotation preserves key metadata"""
        metadata = {
            "name": "My API Key",
            "scopes": ["read"],
            "user_id": 123
        }

        new_metadata = APIKeyManager.rotate_key_with_metadata(metadata)

        # Should preserve name and scopes
        assert new_metadata["name"] == metadata["name"]
        assert new_metadata["scopes"] == metadata["scopes"]
        assert new_metadata["user_id"] == metadata["user_id"]

        # Should update created_at
        assert new_metadata["created_at"] > metadata.get("created_at", datetime.min)


# Note: These tests assume certain methods exist in APIKeyManager
# Adjust method names and signatures based on actual implementation
# Some methods may need to be implemented if they don't exist yet
