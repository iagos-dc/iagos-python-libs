"""
Encryption utilities for securing credentials.

This module provides Jasypt-compatible encryption/decryption functionality
using PBE (Password-Based Encryption) with MD5 and DES.

Main functions:
    - jasypt_encrypt/jasypt_decrypt: Low-level encryption/decryption
    - encrypt_credentials: High-level function to encrypt email and password
"""

import base64
import hashlib
from cryptography.hazmat.primitives.ciphers import Cipher, modes
try:
    from cryptography.hazmat.decrepit.ciphers.algorithms import TripleDES
except ImportError:
    from cryptography.hazmat.primitives.ciphers.algorithms import TripleDES


# ============================================================================
# Core Encryption/Decryption Functions
# ============================================================================


def jasypt_decrypt(encrypted_text: str, password: str) -> str:
    """
    Decrypt a string encrypted with Jasypt PBEWithMD5AndDES algorithm.

    This function is compatible with Jasypt's default encryption scheme:
    - Algorithm: PBEWithMD5AndDES
    - Iterations: 1000
    - Salt size: 8 bytes

    Args:
        encrypted_text: Base64-encoded encrypted string (without ENC() wrapper).
        password: Password used for encryption.

    Returns:
        str: The decrypted plaintext string.

    Examples:
        >>> encrypted = "base64_encrypted_value"
        >>> password = "my_secret_password"
        >>> plaintext = jasypt_decrypt(encrypted, password)
    """
    # Decode base64
    encrypted_data = base64.b64decode(encrypted_text)

    # Extract salt (first 8 bytes) and ciphertext
    salt = encrypted_data[:8]
    ciphertext = encrypted_data[8:]

    # Generate key and IV using MD5 (Jasypt compatible)
    key_iv = _generate_key_iv(password, salt)
    key = key_iv[:8]  # DES key is 8 bytes
    iv = key_iv[8:16]  # DES IV is 8 bytes

    # Decrypt using DES
    cipher = Cipher(TripleDES(key * 3), modes.CBC(iv))
    decryptor = cipher.decryptor()
    decrypted_padded = decryptor.update(ciphertext) + decryptor.finalize()

    # Remove PKCS5 padding
    padding_length = decrypted_padded[-1]
    decrypted = decrypted_padded[:-padding_length]

    return decrypted.decode('utf-8')


def jasypt_encrypt(plaintext: str, password: str) -> str:
    """
    Encrypt a string using Jasypt PBEWithMD5AndDES algorithm.

    This function is compatible with Jasypt's default encryption scheme:
    - Algorithm: PBEWithMD5AndDES
    - Iterations: 1000
    - Salt size: 8 bytes

    Args:
        plaintext: The string to encrypt.
        password: Password to use for encryption.

    Returns:
        str: Base64-encoded encrypted string.

    Examples:
        >>> password = "my_secret_password"
        >>> encrypted = jasypt_encrypt("my_secret_value", password)
        >>> print(encrypted)
    """
    import os

    # Generate random salt (8 bytes)
    salt = os.urandom(8)

    # Generate key and IV using MD5 (Jasypt compatible)
    key_iv = _generate_key_iv(password, salt)
    key = key_iv[:8]  # DES key is 8 bytes
    iv = key_iv[8:16]  # DES IV is 8 bytes

    # Add PKCS5 padding
    plaintext_bytes = plaintext.encode('utf-8')
    padding_length = 8 - (len(plaintext_bytes) % 8)
    padded_plaintext = plaintext_bytes + bytes([padding_length] * padding_length)

    # Encrypt using DES
    cipher = Cipher(TripleDES(key * 3), modes.CBC(iv))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded_plaintext) + encryptor.finalize()

    # Combine salt and ciphertext, then encode to base64
    encrypted_data = salt + ciphertext
    return base64.b64encode(encrypted_data).decode('utf-8')


# ============================================================================
# Internal Helper Functions
# ============================================================================

def _generate_key_iv(password: str, salt: bytes, iterations: int = 1000) -> bytes:
    """
    Generate key and IV using MD5 hashing (Jasypt compatible).

    Args:
        password: Password string.
        salt: Salt bytes.
        iterations: Number of iterations (default 1000 for Jasypt).

    Returns:
        bytes: Combined key and IV bytes.
    """
    password_bytes = password.encode('utf-8')

    # First round
    digest = hashlib.md5(password_bytes + salt).digest()

    # Additional iterations
    for _ in range(1, iterations):
        digest = hashlib.md5(digest).digest()

    # For more key material, do another round
    digest2 = hashlib.md5(digest + password_bytes + salt).digest()

    return digest + digest2


# ============================================================================
# Credential Encryption Utility
# ============================================================================

def encrypt_credentials(email: str, password: str, master_password: str) -> tuple[str, str]:
    """
    Encrypt user credentials (email and password) using a master password.

    This function encrypts both the email and password using Jasypt-compatible
    encryption. The encrypted values can be stored in authentication.py and
    will be decrypted at runtime using the master password.

    Args:
        email: User email/username to encrypt.
        password: User password to encrypt.
        master_password: Master password used for encryption (must be provided
                        at runtime to decrypt).

    Returns:
        tuple[str, str]: A tuple containing (encrypted_email, encrypted_password).

    Examples:
        >>> encrypted_email, encrypted_password = encrypt_credentials(
        ...     "user@example.com",
        ...     "mypassword",
        ...     "master_secret"
        ... )
        >>> print(f"ENCRYPTED_USER_EMAIL = \\\"{encrypted_email}\\\"")
        >>> print(f"ENCRYPTED_USER_PASSWORD = \\\"{encrypted_password}\\\"")
    """
    encrypted_email = jasypt_encrypt(email, master_password)
    encrypted_password = jasypt_encrypt(password, master_password)

    return encrypted_email, encrypted_password
