"""Tests for token encryption utilities."""

import pytest
from pydantic import SecretStr

from gitbrag.services.encryption import decrypt_token, encrypt_token, verify_encryption_roundtrip


def test_encrypt_token_with_secret_str() -> None:
    """Test encrypting a token with SecretStr token and key."""
    token = SecretStr("my-test-token")
    secret_key = SecretStr("my-secret-key-for-testing")

    encrypted = encrypt_token(token, secret_key)

    assert isinstance(encrypted, str)
    assert len(encrypted) > 0
    assert encrypted != token.get_secret_value()


def test_encrypt_token_with_plain_string() -> None:
    """Test encrypting a token with plain string token."""
    token = "my-test-token"
    secret_key = SecretStr("my-secret-key-for-testing")

    encrypted = encrypt_token(token, secret_key)

    assert isinstance(encrypted, str)
    assert len(encrypted) > 0
    assert encrypted != token


def test_encrypt_token_empty_token_raises() -> None:
    """Test that empty token raises ValueError."""
    secret_key = SecretStr("my-secret-key")

    with pytest.raises(ValueError, match="Token cannot be empty"):
        encrypt_token("", secret_key)


def test_encrypt_token_empty_secret_raises() -> None:
    """Test that empty secret key raises ValueError."""
    token = SecretStr("my-token")

    with pytest.raises(ValueError, match="Secret key cannot be empty"):
        encrypt_token(token, SecretStr(""))


def test_decrypt_token_success() -> None:
    """Test successful token decryption."""
    token = SecretStr("my-test-token")
    secret_key = SecretStr("my-secret-key-for-testing")

    encrypted = encrypt_token(token, secret_key)
    decrypted = decrypt_token(encrypted, secret_key)

    assert decrypted is not None
    assert isinstance(decrypted, SecretStr)
    assert decrypted.get_secret_value() == token.get_secret_value()


def test_decrypt_token_wrong_key() -> None:
    """Test decryption with wrong key returns None."""
    token = SecretStr("my-test-token")
    encrypt_key = SecretStr("original-key")
    decrypt_key = SecretStr("different-key")

    encrypted = encrypt_token(token, encrypt_key)
    decrypted = decrypt_token(encrypted, decrypt_key)

    assert decrypted is None


def test_decrypt_token_empty_encrypted() -> None:
    """Test decryption with empty encrypted token returns None."""
    secret_key = SecretStr("my-secret-key")

    decrypted = decrypt_token("", secret_key)

    assert decrypted is None


def test_decrypt_token_empty_secret() -> None:
    """Test decryption with empty secret key returns None."""
    decrypted = decrypt_token("some-encrypted-data", SecretStr(""))

    assert decrypted is None


def test_decrypt_token_invalid_data() -> None:
    """Test decryption with invalid data returns None."""
    secret_key = SecretStr("my-secret-key")

    decrypted = decrypt_token("invalid-encrypted-data", secret_key)

    assert decrypted is None


def test_full_encryption_roundtrip() -> None:
    """Test complete encryption/decryption cycle."""
    original_token = SecretStr("test-oauth-token-12345")
    secret_key = SecretStr("my-secret-encryption-key")

    # Encrypt
    encrypted = encrypt_token(original_token, secret_key)
    assert encrypted != original_token.get_secret_value()

    # Decrypt
    decrypted = decrypt_token(encrypted, secret_key)
    assert decrypted is not None
    assert decrypted.get_secret_value() == original_token.get_secret_value()


def test_verify_encryption_roundtrip_success() -> None:
    """Test the encryption roundtrip test function succeeds with valid key."""
    secret_key = SecretStr("valid-secret-key")

    result = verify_encryption_roundtrip(secret_key)

    assert result is True


def test_verify_encryption_roundtrip_failure() -> None:
    """Test the encryption roundtrip test function fails with empty key."""
    secret_key = SecretStr("")

    result = verify_encryption_roundtrip(secret_key)

    assert result is False


def test_consistent_encryption_different_each_time() -> None:
    """Test that encrypting the same token twice produces different ciphertext (due to IV)."""
    token = SecretStr("my-test-token")
    secret_key = SecretStr("my-secret-key")

    encrypted1 = encrypt_token(token, secret_key)
    encrypted2 = encrypt_token(token, secret_key)

    # Should be different due to random IV
    assert encrypted1 != encrypted2

    # But both should decrypt to the same value
    decrypted1 = decrypt_token(encrypted1, secret_key)
    decrypted2 = decrypt_token(encrypted2, secret_key)
    assert decrypted1 is not None
    assert decrypted2 is not None
    assert decrypted1.get_secret_value() == decrypted2.get_secret_value()
    assert decrypted1.get_secret_value() == token.get_secret_value()
