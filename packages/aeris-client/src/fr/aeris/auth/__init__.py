"""Authentication and encryption utilities for AERIS and DATA-TERRA services."""

__version__ = "0.1.0"

from .authentication import (
    # Dataclasses
    ClientCredentialsConfig,
    PasswordGrantConfig,
    # Pre-built configs
    AERIS_CONFIG,
    DATA_TERRA_M1_CONFIG,
    DATA_TERRA_M2_CONFIG,
    # Authentication functions
    get_token_password_grant,
    get_token_client_credentials,
    get_token_authorization_code,
    # Backward-compatible wrapper
    getToken,
    # Utilities
    prompt_api_key,
    prompt_token,
    build_auth_header,
)
from .encryption import (
    jasypt_encrypt,
    jasypt_decrypt,
    encrypt_credentials,
)

__all__ = [
    "ClientCredentialsConfig",
    "PasswordGrantConfig",
    "AERIS_CONFIG",
    "DATA_TERRA_M1_CONFIG",
    "DATA_TERRA_M2_CONFIG",
    "get_token_password_grant",
    "get_token_client_credentials",
    "get_token_authorization_code",
    "getToken",
    "prompt_api_key",
    "prompt_token",
    "build_auth_header",
    "jasypt_encrypt",
    "jasypt_decrypt",
    "encrypt_credentials",
]
