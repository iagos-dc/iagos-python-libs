"""
Authentication module for Keycloak SSO services.

Credentials are stored Jasypt-encrypted in .env (project root).
The master password is never stored — it must be provided via:
  - master_password argument (recommended for scripts)
  - AERIS_MASTER_PASSWORD or DATA_TERRA_MASTER_PASSWORD environment variable
  - Interactive prompt (fallback)

Supported grant types
---------------------
- password grant       : get_token_password_grant()      — AERIS SSO
- client_credentials   : get_token_client_credentials()  — DATA-TERRA / IRISCC machine-to-machine
- authorization_code   : get_token_authorization_code()  — DATA-TERRA / IRISCC user login (headless)

Pre-built configs
-----------------
AERIS_CONFIG          — sso.aeris-data.fr,  realm aeris,     password grant
DATA_TERRA_M1_CONFIG  — sso.earth-data.fr,  realm gaia-data, client_credentials
DATA_TERRA_M2_CONFIG  — sso.earth-data.fr,  realm gaia-data, authorization_code
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv, find_dotenv
from keycloak import KeycloakOpenID

try:
    from .encryption import jasypt_decrypt
except ImportError:
    from fr.aeris.auth.encryption import jasypt_decrypt

# Load encrypted credentials from the nearest .env found up the directory tree
load_dotenv(find_dotenv())


# ---------------------------------------------------------------------------
# Configuration dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ClientCredentialsConfig:
    """Configuration for the client_credentials grant (machine-to-machine)."""
    server_url: str
    realm: str
    client_id: str
    encrypted_client_secret: str


@dataclass
class PasswordGrantConfig:
    """
    Configuration for password grant (AERIS) and authorization_code headless (DATA-TERRA).

    redirect_uri is only required for the authorization_code flow.
    """
    server_url: str
    realm: str
    client_id: str
    encrypted_username: str
    encrypted_password: str
    redirect_uri: str = field(default="http://localhost")


# ---------------------------------------------------------------------------
# Pre-built configs loaded from .env
# ---------------------------------------------------------------------------

AERIS_CONFIG = PasswordGrantConfig(
    server_url=os.getenv("AERIS_KC_SERVER_URL", "https://sso.aeris-data.fr/auth/"),
    realm=os.getenv("AERIS_KC_REALM",           "aeris"),
    client_id=os.getenv("AERIS_KC_CLIENT_ID",   "aeris-public"),
    encrypted_username=os.getenv("AERIS_ENCRYPTED_EMAIL",    ""),
    encrypted_password=os.getenv("AERIS_ENCRYPTED_PASSWORD", ""),
)

DATA_TERRA_M1_CONFIG = ClientCredentialsConfig(
    server_url=os.getenv("DATA_TERRA_KC_SERVER_URL", "https://sso.earth-data.fr"),
    realm=os.getenv("DATA_TERRA_KC_REALM",           "gaia-data"),
    client_id=os.getenv("IRISCC_KC_CLIENT_ID",       "aeris-iriscc-va-admin-iagos"),
    encrypted_client_secret=os.getenv("IRISCC_KC_ENCRYPTED_CLIENT_SECRET", ""),
)

DATA_TERRA_M2_CONFIG = PasswordGrantConfig(
    server_url=os.getenv("DATA_TERRA_KC_SERVER_URL",  "https://sso.earth-data.fr"),
    realm=os.getenv("DATA_TERRA_KC_REALM",            "gaia-data"),
    client_id=os.getenv("IRISCC_KC_CLIENT_ID_2",      "aeris-iriscc-va-portal-api"),
    encrypted_username=os.getenv("DATA_TERRA_KC_ENCRYPTED_USERNAME", ""),
    encrypted_password=os.getenv("DATA_TERRA_KC_ENCRYPTED_PASSWORD", ""),
    redirect_uri=os.getenv(
        "IRISCC_KC_REDIRECT_URI",
        "https://aeris-services.ipsl.fr/iriscc-va/api/swagger-ui/oauth2-redirect.html",
    ),
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_master_password(master_password: str = None, env_var: str = "AERIS_MASTER_PASSWORD") -> str:
    """
    Resolve the master password from argument, environment variable, or interactive prompt.

    Args:
        master_password: Master password passed directly by the caller.
        env_var:         Environment variable name to check if master_password is None.
    """
    from getpass import getpass
    if master_password is None:
        master_password = os.environ.get(env_var)
    if master_password is None:
        master_password = os.environ.get("DATA_TERRA_MASTER_PASSWORD")
    if master_password is None:
        master_password = getpass("Please enter master password for decryption: ")
    return master_password


# ---------------------------------------------------------------------------
# Authentication functions
# ---------------------------------------------------------------------------

def get_token_password_grant(config: PasswordGrantConfig, master_password: str = None) -> dict:
    """
    Retrieve a Keycloak token using the password grant (Resource Owner Password Credentials).

    Uses python-keycloak. Intended for AERIS SSO (sso.aeris-data.fr).

    Args:
        config:          PasswordGrantConfig instance (use AERIS_CONFIG for AERIS SSO).
        master_password: Master password for decrypting credentials.

    Returns:
        dict: Token dictionary from Keycloak (contains access_token, refresh_token, etc.).

    Raises:
        ValueError: If encrypted credentials are not set in config.

    Examples:
        >>> token = get_token_password_grant(AERIS_CONFIG, master_password="my_secret")
        >>> token = get_token_password_grant(AERIS_CONFIG)  # reads env var or prompts
    """
    if not config.encrypted_username or not config.encrypted_password:
        raise ValueError(
            f"encrypted_username or encrypted_password not set in config. "
            "Fill in the corresponding fields in .env and rebuild the config."
        )

    mp = _resolve_master_password(master_password)
    username = jasypt_decrypt(config.encrypted_username, mp)
    password = jasypt_decrypt(config.encrypted_password, mp)

    keycloak_openid = KeycloakOpenID(
        server_url=config.server_url,
        client_id=config.client_id,
        realm_name=config.realm,
        verify=True,
    )
    return keycloak_openid.token(username, password)


def get_token_client_credentials(
    config: ClientCredentialsConfig,
    master_password: str = None,
) -> str:
    """
    Retrieve a Keycloak access token using the client_credentials grant (machine-to-machine).

    Args:
        config:          ClientCredentialsConfig instance (use DATA_TERRA_M1_CONFIG for IRISCC).
        master_password: Master password for decrypting the client secret.

    Returns:
        str: The JWT access token.

    Raises:
        ValueError: If the encrypted client secret is not set or the response contains no token.
        requests.HTTPError: On HTTP errors.

    Examples:
        >>> token = get_token_client_credentials(DATA_TERRA_M1_CONFIG, master_password="my_secret")
    """
    import requests

    if not config.encrypted_client_secret:
        raise ValueError(
            "encrypted_client_secret not set in config. "
            "Fill in IRISCC_KC_ENCRYPTED_CLIENT_SECRET in .env."
        )

    client_secret = jasypt_decrypt(
        config.encrypted_client_secret, _resolve_master_password(master_password)
    )

    token_endpoint = f"{config.server_url}/realms/{config.realm}/protocol/openid-connect/token"
    response = requests.post(
        token_endpoint,
        data={
            "client_id": config.client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
        },
        timeout=10,
    )
    response.raise_for_status()

    payload = response.json()
    token = payload.get("access_token")
    if not token:
        raise ValueError(f"No access_token in response: {payload}")
    return token


def get_token_authorization_code(
    config: PasswordGrantConfig,
    master_password: str = None,
    username: str = None,
    password: str = None,
) -> str:
    """
    Retrieve a Keycloak access token using the authorization_code flow (headless).

    Submits credentials directly to the Keycloak login form without a browser.
    Intended for DATA-TERRA / IRISCC user login (sso.earth-data.fr).

    When username or password are None, they are decrypted from the config.

    Steps:
      1. GET the Keycloak login page to obtain the form action URL.
      2. POST username/password to that URL.
      3. Intercept the redirect to extract the authorization code.
      4. Exchange the code for an access token.

    Args:
        config:          PasswordGrantConfig instance (use DATA_TERRA_M2_CONFIG for IRISCC).
        master_password: Master password for decrypting credentials (used if username/password are None).
        username:        Username override — if None, decrypted from config.
        password:        Password override — if None, decrypted from config.

    Returns:
        str: The JWT access token.

    Raises:
        ValueError: If any step fails (form not found, no code, no token).
        requests.HTTPError: On HTTP errors.

    Examples:
        >>> token = get_token_authorization_code(DATA_TERRA_M2_CONFIG, master_password="my_secret")
        >>> token = get_token_authorization_code(DATA_TERRA_M2_CONFIG, username="u", password="p")
    """
    import re
    import requests
    from urllib.parse import urlparse, parse_qs

    if username is None or password is None:
        mp = _resolve_master_password(master_password)
        if username is None:
            username = jasypt_decrypt(config.encrypted_username, mp)
        if password is None:
            password = jasypt_decrypt(config.encrypted_password, mp)

    session = requests.Session()

    # Step 1 — get the login page
    auth_url = f"{config.server_url}/realms/{config.realm}/protocol/openid-connect/auth"
    resp = session.get(auth_url, params={
        "client_id": config.client_id,
        "redirect_uri": config.redirect_uri,
        "response_type": "code",
        "scope": "openid",
    }, timeout=10)
    if not resp.ok:
        raise requests.HTTPError(
            f"{resp.status_code} {resp.reason} — {resp.text}", response=resp
        )

    # Step 2 — extract the form action and submit credentials
    match = re.search(r'action="([^"]+)"', resp.text)
    if not match:
        raise ValueError("Could not find login form in Keycloak response")
    form_action = match.group(1).replace("&amp;", "&")

    resp = session.post(form_action, data={
        "username": username,
        "password": password,
    }, allow_redirects=False, timeout=10)

    # Step 3 — extract the authorization code from the redirect Location
    location = resp.headers.get("Location", "")
    params = parse_qs(urlparse(location).query)
    if "error" in params:
        raise ValueError(
            f"Keycloak login failed: {params.get('error')} — {params.get('error_description')}"
        )
    code = params.get("code", [None])[0]
    if not code:
        raise ValueError(f"No authorization code in redirect location: {location!r}")

    # Step 4 — exchange code for access token
    token_url = f"{config.server_url}/realms/{config.realm}/protocol/openid-connect/token"
    resp = session.post(token_url, data={
        "grant_type": "authorization_code",
        "client_id": config.client_id,
        "code": code,
        "redirect_uri": config.redirect_uri,
    }, timeout=10)
    if not resp.ok:
        raise requests.HTTPError(
            f"{resp.status_code} {resp.reason} — {resp.text}", response=resp
        )

    payload = resp.json()
    token = payload.get("access_token")
    if not token:
        raise ValueError(f"No access_token in response: {payload}")
    return token


# ---------------------------------------------------------------------------
# Backward-compatible wrappers
# ---------------------------------------------------------------------------

def getToken(master_password: str = None) -> dict:
    """
    Retrieve token using AERIS Keycloak SSO (password grant).

    This method will be deprecated in a near future.
    Use get_token_password_grant(AERIS_CONFIG, master_password) instead.

    Args:
        master_password: Master password for decrypting credentials.

    Returns:
        dict: Token dictionary from Keycloak.
    """
    return get_token_password_grant(AERIS_CONFIG, master_password=master_password)


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def prompt_api_key() -> str:
    """
    Prompt user to enter their AERIS API key.

    API keys can be obtained at: https://www.sedoo.fr/aeris-key-manager/

    Returns:
        str: The API key entered by the user.
    """
    return input("Please enter your AERIS API Key (get one at https://www.sedoo.fr/aeris-key-manager/): ")


def prompt_token() -> str:
    """
    Prompt user to enter their AERIS SSO token.

    Returns:
        str: The SSO token entered by the user.
    """
    return input("Please enter your AERIS SSO token: ")


def build_auth_header(method: str, credential: str) -> dict:
    """
    Build authentication header for AERIS API requests.

    Args:
        method:     Authentication method — 'key' or 'token'.
        credential: API key or access token string.

    Returns:
        dict: HTTP headers with Authorization and Accept fields.

    Raises:
        ValueError: If method is not 'key' or 'token'.

    Examples:
        >>> build_auth_header('key', 'my-api-key')
        {'Authorization': 'X-API-Key my-api-key', 'Accept': '*/*'}

        >>> build_auth_header('token', 'eyJhbG...')
        {'Authorization': 'Bearer eyJhbG...', 'Accept': '*/*'}
    """
    if method == "key":
        auth_value = f"X-API-Key {credential}"
    elif method == "token":
        auth_value = f"Bearer {credential}"
    else:
        raise ValueError(f"Invalid authentication method: '{method}'. Must be 'key' or 'token'.")

    return {"Authorization": auth_value, "Accept": "*/*"}
