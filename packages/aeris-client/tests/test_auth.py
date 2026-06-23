"""Tests for fr.aeris.auth (Keycloak token fetching — mocked)."""

import pytest

from fr.aeris.auth import getToken


@pytest.mark.integration
def test_get_token_aeris_live():
    """Live test — calls the real AERIS Keycloak SSO.

    Reads credentials from .env at the repo root.
    Prompts for the master password interactively if AERIS_MASTER_PASSWORD is not set.

    Run with:
        pytest -m integration -s
    """
    token = getToken()

    assert isinstance(token, dict), "getToken() should return a dict"
    assert "access_token" in token, "token should have an access_token key"
    assert isinstance(token["access_token"], str), "access_token should be a string"
    assert len(token["access_token"]) > 0, "access_token should not be empty"
