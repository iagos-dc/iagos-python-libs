"""
Encryption utilities for securing credentials.

This module provides password-based encryption/decryption using
AES-256-GCM with PBKDF2-SHA256 key derivation.

Main functions:
    - jasypt_encrypt/jasypt_decrypt: Low-level encryption/decryption
    - encrypt_credentials: High-level function to encrypt email and password
"""

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


_PBKDF2_ITERATIONS = 600_000
_SALT_SIZE = 16
_NONCE_SIZE = 12
_KEY_SIZE = 32


# ============================================================================
# Core Encryption/Decryption Functions
# ============================================================================


def jasypt_decrypt(encrypted_text: str, password: str) -> str:
    """
    Decrypt a string encrypted with jasypt_encrypt.

    Args:
        encrypted_text: Base64-encoded encrypted string.
        password: Password used for encryption.

    Returns:
        str: The decrypted plaintext string.
    """
    data = base64.b64decode(encrypted_text)
    salt = data[:_SALT_SIZE]
    nonce = data[_SALT_SIZE:_SALT_SIZE + _NONCE_SIZE]
    ciphertext = data[_SALT_SIZE + _NONCE_SIZE:]

    key = _derive_key(password, salt)
    plaintext = AESGCM(key).decrypt(nonce, ciphertext, None)
    return plaintext.decode("utf-8")


def jasypt_encrypt(plaintext: str, password: str) -> str:
    """
    Encrypt a string using AES-256-GCM with PBKDF2-SHA256 key derivation.

    Args:
        plaintext: The string to encrypt.
        password: Password to use for encryption.

    Returns:
        str: Base64-encoded encrypted string.
    """
    salt = os.urandom(_SALT_SIZE)
    nonce = os.urandom(_NONCE_SIZE)

    key = _derive_key(password, salt)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), None)

    return base64.b64encode(salt + nonce + ciphertext).decode("utf-8")


# ============================================================================
# Internal Helper Functions
# ============================================================================


def _derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(algorithm=SHA256(), length=_KEY_SIZE, salt=salt, iterations=_PBKDF2_ITERATIONS)
    return kdf.derive(password.encode("utf-8"))


# ============================================================================
# Credential Encryption Utility
# ============================================================================


def encrypt_credentials(email: str, password: str, master_password: str) -> tuple[str, str]:
    """
    Encrypt user credentials (email and password) using a master password.

    The encrypted values can be stored in a .env file and will be decrypted
    at runtime using the master password.

    Args:
        email: User email/username to encrypt.
        password: User password to encrypt.
        master_password: Master password used for encryption.

    Returns:
        tuple[str, str]: A tuple containing (encrypted_email, encrypted_password).

    Examples:
        >>> encrypted_email, encrypted_password = encrypt_credentials(
        ...     "user@example.com",
        ...     "mypassword",
        ...     "master_secret"
        ... )
        >>> print(f"ENCRYPTED_USER_EMAIL = \\"{encrypted_email}\\"")
        >>> print(f"ENCRYPTED_USER_PASSWORD = \\"{encrypted_password}\\"")
    """
    return jasypt_encrypt(email, master_password), jasypt_encrypt(password, master_password)
