"""Tests for fr.aeris.catalogue (HTTP calls mocked with responses library)."""

import json
import pytest
import responses as rsps

import fr.aeris.catalogue as catalogue
from fr.aeris.catalogue import (
    URL_CATALOGUE,
    URL_CATALOGUE_FATS,
    getMetadataRecord,
    getMetadataRecordFATS,
    getRecords4Project,
    getUUID,
    patchMetadata,
    updateClientTemplateName,
    updateDOI,
    updateOpensearchLink,
    updateDLLink,
    addProject,
)

FAKE_UUID = "aaaaaaaa-0000-0000-0000-bbbbbbbbbbbb"
FAKE_TOKEN = {"access_token": "fake-token"}


@pytest.fixture
def mock_auth(mocker):
    """Prevent any real Keycloak call in write-operation tests."""
    mocker.patch("fr.aeris.catalogue.getToken", return_value=FAKE_TOKEN)


# ---------------------------------------------------------------------------
# Public reads — no auth
# ---------------------------------------------------------------------------

class TestGetMetadataRecord:

    @rsps.activate
    def test_returns_parsed_dict(self):
        payload = {"id": FAKE_UUID, "resourceTitle": {"en": "Test"}}
        rsps.add(rsps.GET, URL_CATALOGUE + "/" + FAKE_UUID, json=payload, status=200)

        result = getMetadataRecord(FAKE_UUID)

        assert result["id"] == FAKE_UUID
        assert result["resourceTitle"]["en"] == "Test"

    @rsps.activate
    def test_calls_correct_url(self):
        rsps.add(rsps.GET, URL_CATALOGUE + "/" + FAKE_UUID, json={}, status=200)
        getMetadataRecord(FAKE_UUID)
        assert rsps.calls[0].request.url == URL_CATALOGUE + "/" + FAKE_UUID


class TestGetMetadataRecordFATS:

    @rsps.activate
    def test_calls_fats_url(self):
        rsps.add(rsps.GET, URL_CATALOGUE_FATS + "/" + FAKE_UUID, json={"id": FAKE_UUID}, status=200)
        result = getMetadataRecordFATS(FAKE_UUID)
        assert result["id"] == FAKE_UUID


class TestGetRecords4Project:

    @rsps.activate
    def test_returns_list_of_ids(self):
        payload = {"results": [{"id": "uuid-1"}, {"id": "uuid-2"}]}
        rsps.add(rsps.GET, URL_CATALOGUE + "/summaries?project=IAGOS", json=payload, status=200)

        result = getRecords4Project("IAGOS")

        assert result == ["uuid-1", "uuid-2"]

    @rsps.activate
    def test_empty_project_returns_empty_list(self):
        rsps.add(rsps.GET, URL_CATALOGUE + "/summaries?project=UNKNOWN", json={"results": []}, status=200)
        assert getRecords4Project("UNKNOWN") == []


class TestGetUUID:

    @rsps.activate
    def test_returns_uuid_string(self):
        rsps.add(rsps.GET, URL_CATALOGUE + "/uuid/random", body=FAKE_UUID, status=200)
        assert getUUID() == FAKE_UUID


# ---------------------------------------------------------------------------
# Authenticated writes
# ---------------------------------------------------------------------------

class TestPatchMetadata:

    @rsps.activate
    def test_sends_patch_with_json_body(self, mock_auth):
        rsps.add(rsps.PATCH, URL_CATALOGUE + FAKE_UUID, status=200)
        payload = {"type": "COLLECTION", "clientTemplateName": "test"}

        patchMetadata(FAKE_UUID, payload)

        req = rsps.calls[0].request
        assert req.method == "PATCH"
        assert json.loads(req.body) == payload

    @rsps.activate
    def test_sends_auth_header(self, mock_auth):
        rsps.add(rsps.PATCH, URL_CATALOGUE + FAKE_UUID, status=200)

        patchMetadata(FAKE_UUID, {"type": "COLLECTION"})

        assert "Authorization" in rsps.calls[0].request.headers


class TestUpdateClientTemplateName:

    @rsps.activate
    def test_patches_correct_field(self, mock_auth):
        rsps.add(rsps.PATCH, URL_CATALOGUE + FAKE_UUID, status=200)

        updateClientTemplateName(FAKE_UUID, "my-template")

        body = json.loads(rsps.calls[0].request.body)
        assert body["clientTemplateName"] == "my-template"
        assert body["type"] == "COLLECTION"


class TestUpdateDOI:

    @rsps.activate
    def test_patches_identifiers(self, mock_auth):
        rsps.add(rsps.PATCH, URL_CATALOGUE + FAKE_UUID, status=200)

        updateDOI(FAKE_UUID, "10.1234/test")

        body = json.loads(rsps.calls[0].request.body)
        assert body["identifiers"][0]["code"] == "10.1234/test"
        assert body["identifiers"][0]["codeSpace"] == "http://dx.doi.org/"


class TestUpdateOpensearchLink:

    @rsps.activate
    def test_patches_opensearch_link(self, mock_auth):
        rsps.add(rsps.PATCH, URL_CATALOGUE + FAKE_UUID, status=200)
        link = "https://api.sedoo.fr/aeris-catalogue-prod/data/"

        updateOpensearchLink(FAKE_UUID, link)

        body = json.loads(rsps.calls[0].request.body)
        assert body["links"][0]["type"] == "OPENSEARCH_LINK"
        assert body["links"][0]["url"] == link


class TestUpdateDLLink:

    @rsps.activate
    def test_patches_all_records_in_project(self, mock_auth):
        rsps.add(
            rsps.GET,
            URL_CATALOGUE + "/summaries?project=IAGOS",
            json={"results": [{"id": "uuid-1"}, {"id": "uuid-2"}]},
        )
        rsps.add(rsps.PATCH, URL_CATALOGUE + "uuid-1", status=200)
        rsps.add(rsps.PATCH, URL_CATALOGUE + "uuid-2", status=200)

        updateDLLink("IAGOS", "https://example.com/data")

        patch_calls = [c for c in rsps.calls if c.request.method == "PATCH"]
        assert len(patch_calls) == 2


class TestAddProject:

    @rsps.activate
    def test_adds_project_when_absent(self, mock_auth):
        existing = {"projectSet": [{"shortName": "EXISTING"}], "type": "COLLECTION"}
        rsps.add(rsps.GET, URL_CATALOGUE + "/summaries?project=BASE", json={"results": [{"id": FAKE_UUID}]})
        rsps.add(rsps.GET, URL_CATALOGUE + "/" + FAKE_UUID, json=existing)
        rsps.add(rsps.PATCH, URL_CATALOGUE + FAKE_UUID, status=200)

        addProject("BASE", {"shortName": "NEW"})

        body = json.loads(rsps.calls[-1].request.body)
        names = [p["shortName"] for p in body["projectSet"]]
        assert "NEW" in names
        assert "EXISTING" in names

    @rsps.activate
    def test_skips_patch_when_project_already_present(self, mock_auth):
        existing = {"projectSet": [{"shortName": "ALREADY"}], "type": "COLLECTION"}
        rsps.add(rsps.GET, URL_CATALOGUE + "/summaries?project=BASE", json={"results": [{"id": FAKE_UUID}]})
        rsps.add(rsps.GET, URL_CATALOGUE + "/" + FAKE_UUID, json=existing)

        addProject("BASE", {"shortName": "ALREADY"})

        patch_calls = [c for c in rsps.calls if c.request.method == "PATCH"]
        assert len(patch_calls) == 0
