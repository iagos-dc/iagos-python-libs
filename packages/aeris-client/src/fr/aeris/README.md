# aeris-client

Python client for AERIS SSO authentication and catalogue REST API.

Provides two modules:
- `fr.aeris.auth` — Keycloak authentication (password grant, client_credentials, authorization_code)
- `fr.aeris.catalogue` — Read/write helpers for the AERIS catalogue REST API

Install (editable, from the repo root):
```bash
pip install -e packages/aeris-client
```

---

## Supported grant types

| Function | Grant type | Default config | Service |
|---|---|---|---|
| `get_token_password_grant()` | password | `AERIS_CONFIG` | `sso.aeris-data.fr` |
| `get_token_client_credentials()` | client_credentials | `DATA_TERRA_M1_CONFIG` | `sso.earth-data.fr` |
| `get_token_authorization_code()` | authorization_code (headless) | `DATA_TERRA_M2_CONFIG` | `sso.earth-data.fr` |

---

## Configuration dataclasses

```python
@dataclass
class ClientCredentialsConfig:
    server_url: str
    realm: str
    client_id: str
    encrypted_client_secret: str

@dataclass
class PasswordGrantConfig:
    server_url: str
    realm: str
    client_id: str
    encrypted_username: str
    encrypted_password: str
    redirect_uri: str = "http://localhost"
```

Pre-built configs are loaded from `.env` at the project root:
- `AERIS_CONFIG` — AERIS SSO, password grant
- `DATA_TERRA_M1_CONFIG` — DATA-TERRA, client_credentials (IRISCC machine-to-machine)
- `DATA_TERRA_M2_CONFIG` — DATA-TERRA, authorization_code (IRISCC user login)

---

## Usage

```python
from fr.aeris.auth import (
    get_token_password_grant,      AERIS_CONFIG,
    get_token_client_credentials,  DATA_TERRA_M1_CONFIG,
    get_token_authorization_code,  DATA_TERRA_M2_CONFIG,
    build_auth_header,
)

# AERIS SSO — password grant
token = get_token_password_grant(AERIS_CONFIG, master_password="my_secret")
header = build_auth_header("token", token["access_token"])

# DATA-TERRA — client_credentials (machine-to-machine)
access_token = get_token_client_credentials(DATA_TERRA_M1_CONFIG, master_password="my_secret")

# DATA-TERRA — authorization_code (user login)
access_token = get_token_authorization_code(DATA_TERRA_M2_CONFIG, master_password="my_secret")

# API key
header = build_auth_header("key", "my-api-key")
```

### Backward-compatible wrapper (AERIS only)

```python
from fr.aeris.auth import getToken
token = getToken(master_password="my_secret")
```

---

## Credential encryption

Credentials are stored Jasypt-encrypted (PBEWithMD5AndDES) in `.env` at the project root.

To generate encrypted values:

```python
import sys
sys.path.insert(0, "src")
from fr.aeris.auth.encryption import jasypt_encrypt

enc = jasypt_encrypt("plain_value", "my_master_password")
print(enc)
```

Or for AERIS email + password together:

```python
from fr.aeris.auth import encrypt_credentials
enc_email, enc_pwd = encrypt_credentials("user@example.com", "password", "master_pwd")
```

Then fill the corresponding variables in `.env`.

---

## Master password

The master password for decryption is resolved in this order:

1. `master_password` argument passed to the function
2. `AERIS_MASTER_PASSWORD` or `DATA_TERRA_MASTER_PASSWORD` environment variable
3. Interactive prompt

**From the command line** (recommended for scripts):
```bash
python script.py --master-password "my_secret"
# or
AERIS_MASTER_PASSWORD="my_secret" python script.py
DATA_TERRA_MASTER_PASSWORD="my_secret" python script.py
```

---

## `.env` variables

| Variable | Description | Encrypted |
|---|---|---|
| `AERIS_KC_SERVER_URL` | AERIS Keycloak server URL | No |
| `AERIS_KC_REALM` | AERIS realm | No |
| `AERIS_KC_CLIENT_ID` | AERIS client ID | No |
| `AERIS_ENCRYPTED_EMAIL` | AERIS login email | Yes |
| `AERIS_ENCRYPTED_PASSWORD` | AERIS login password | Yes |
| `DATA_TERRA_KC_SERVER_URL` | DATA-TERRA Keycloak server URL | No |
| `DATA_TERRA_KC_REALM` | DATA-TERRA realm | No |
| `DATA_TERRA_KC_ENCRYPTED_USERNAME` | DATA-TERRA login username | Yes |
| `DATA_TERRA_KC_ENCRYPTED_PASSWORD` | DATA-TERRA login password | Yes |
| `IRISCC_KC_CLIENT_ID` | IRISCC client ID (method 1) | No |
| `IRISCC_KC_ENCRYPTED_CLIENT_SECRET` | IRISCC client secret (method 1) | Yes |
| `IRISCC_KC_CLIENT_ID_2` | IRISCC client ID (method 2) | No |
| `IRISCC_KC_REDIRECT_URI` | IRISCC redirect URI (method 2) | No |
| `IRISCC_API_BASE_URL` | IRISCC VA API base URL | No |

---

## Catalogue API (`fr.aeris.catalogue`)

```python
import fr.aeris.catalogue as catalogue

# Public reads (no auth)
record = catalogue.getMetadataRecord("some-uuid")
ids = catalogue.getRecords4Project("IAGOS")

# Authenticated writes
catalogue.updateLicenceCCBY("some-uuid", master_password="my_secret")
catalogue.updateDOI("some-uuid", "10.xxxx/yyyy", master_password="my_secret")
catalogue.patchMetadata("some-uuid", {"type": "COLLECTION", ...}, master_password="my_secret")
```

Write operations authenticate automatically via `fr.aeris.auth.getToken`.

---

## Files

| File | Description |
|------|-------------|
| `auth/authentication.py` | Dataclasses, pre-built configs, all authentication functions |
| `auth/encryption.py` | `jasypt_encrypt/decrypt`, `encrypt_credentials` |
| `auth/__init__.py` | Public API re-exports |
| `catalogue.py` | AERIS catalogue REST API client |
