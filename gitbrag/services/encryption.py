"""Token encryption utilities for secure OAuth token storage.

This module provides encryption/decryption functions for OAuth tokens
using the cryptography library (Fernet symmetric encryption).
"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from pydantic import SecretStr


def _derive_key(secret: str) -> bytes:
    """Derive a Fernet-compatible key from the session secret using PBKDF2.

    Args:
        secret: The session secret key

    Returns:
        A 32-byte key suitable for Fernet encryption
    """
    # Use PBKDF2 to derive a key from the secret
    # Salt is fixed since we're deriving from a secret key, not a password
    salt = b"gitbrag-session-encryption"
    kdf_output = hashlib.pbkdf2_hmac(
        "sha256",
        secret.encode("utf-8"),
        salt,
        iterations=100000,
        dklen=32,
    )
    # Fernet requires base64-encoded keys
    return base64.urlsafe_b64encode(kdf_output)


def encrypt_token(token: SecretStr | str, secret_key: SecretStr) -> str:
    """Encrypt an OAuth token for storage in Redis.

    Args:
        token: The OAuth token to encrypt (as SecretStr or str)
        secret_key: The session secret key for deriving encryption key

    Returns:
        Base64-encoded encrypted token blob

    Raises:
        ValueError: If token or secret_key is empty
    """
    # Extract string from SecretStr if needed
    token_str = token.get_secret_value() if isinstance(token, SecretStr) else token
    secret_str = secret_key.get_secret_value()

    if not token_str:
        raise ValueError("Token cannot be empty")
    if not secret_str:
        raise ValueError("Secret key cannot be empty")

    # Derive encryption key and create Fernet instance
    key = _derive_key(secret_str)
    fernet = Fernet(key)

    # Encrypt and return as string
    encrypted = fernet.encrypt(token_str.encode("utf-8"))
    return encrypted.decode("utf-8")


def decrypt_token(encrypted_token: str, secret_key: SecretStr) -> SecretStr | None:
    """Decrypt an OAuth token from Redis storage.

    Args:
        encrypted_token: The base64-encoded encrypted token blob
        secret_key: The session secret key for deriving decryption key

    Returns:
        Decrypted token as SecretStr, or None if decryption fails

    Note:
        Returns None instead of raising exception to gracefully handle
        key rotation or corrupted data scenarios.
    """
    try:
        secret_str = secret_key.get_secret_value()
        if not secret_str or not encrypted_token:
            return None

        # Derive decryption key and create Fernet instance
        key = _derive_key(secret_str)
        fernet = Fernet(key)

        # Decrypt and return as SecretStr
        decrypted = fernet.decrypt(encrypted_token.encode("utf-8"))
        return SecretStr(decrypted.decode("utf-8"))

    except (InvalidToken, ValueError, Exception):
        # Return None on any decryption failure
        # This handles key rotation, corrupted data, etc.
        return None


def verify_encryption_roundtrip(secret_key: SecretStr) -> bool:
    """Test that encryption/decryption works with the given secret key.

    Args:
        secret_key: The session secret key to test

    Returns:
        True if encryption roundtrip succeeds, False otherwise
    """
    test_token = SecretStr("test-token-12345")
    try:
        encrypted = encrypt_token(test_token, secret_key)
        decrypted = decrypt_token(encrypted, secret_key)
        return decrypted is not None and decrypted.get_secret_value() == test_token.get_secret_value()
    except Exception:
        return False
