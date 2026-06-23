"""
AERIS catalogue REST API client.

Provides read and write helpers for the AERIS catalogue (aeris-catalogue-prod)
and the metadata template service.

Write operations are authenticated via the AERIS SSO token (fr.aeris.auth.getToken).
Public read endpoints require no authentication.
"""

import json
import logging
from typing import Any, Dict, List

import requests

from fr.aeris.auth import getToken, build_auth_header

logger = logging.getLogger(__name__)

URL_CATALOGUE = "https://api.sedoo.fr/aeris-catalogue-prod/metadata/"
URL_TEMPLATES = "https://api.sedoo.fr/aeris-metadata-template-rest/template/v2"
URL_CATALOGUE_FATS = "https://api.sedoo.fr/aeris-catalogue-prod-fats/metadata/"


def _auth_header(master_password: str = None) -> Dict[str, str]:
    token = getToken(master_password=master_password)
    return build_auth_header("token", token["access_token"])


def getPublic(url: str) -> requests.Response:
    """Fetch a public (unauthenticated) URL."""
    return requests.get(url)


def getPrivate(url: str, master_password: str = None) -> requests.Response:
    """Fetch an authenticated URL using the AERIS SSO token."""
    return requests.get(url, headers=_auth_header(master_password))


def patchMetadata(record_id: str, payload: Dict[str, Any], master_password: str = None):
    """PATCH a catalogue metadata record with a partial payload dict."""
    r = requests.patch(URL_CATALOGUE + record_id, json.dumps(payload), headers=_auth_header(master_password))
    logger.info("PATCH %s → %s", record_id, r.status_code)


def getUUID() -> str:
    """Return a new random UUID from the catalogue service."""
    response = requests.get(URL_CATALOGUE + '/uuid/random')
    return response.text


def updateClientTemplateName(record_id: str, project: str, master_password: str = None):
    """Set the clientTemplateName field of a catalogue record."""
    template = {
        "clientTemplateName": project,
        "type": "COLLECTION"
    }
    patchMetadata(record_id, template, master_password)


def getMetadataRecord(record_id: str) -> Dict[str, Any]:
    """Fetch and return a single catalogue metadata record by UUID."""
    response = getPublic(URL_CATALOGUE + "/" + record_id)
    return json.loads(response.text)


def getMetadataRecordFATS(record_id: str) -> Dict[str, Any]:
    """Fetch and return a single FATS catalogue metadata record by UUID."""
    response = getPublic(URL_CATALOGUE_FATS + "/" + record_id)
    return json.loads(response.text)


def getRecords4Project(project: str) -> List[str]:
    """Return the list of record UUIDs belonging to a project."""
    response = getPublic(URL_CATALOGUE + "/summaries?project=" + project)
    data = json.loads(response.text)
    return [metadata['id'] for metadata in data['results']]


def updateOpensearchLink(record_id: str, link: str, master_password: str = None):
    """Set the OPENSEARCH_LINK on a catalogue record."""
    links = {
        "links": [{
            "type": "OPENSEARCH_LINK",
            "url": link,
            "name": "",
            "description": None
        }],
        "type": "COLLECTION"
    }
    logger.debug("updateOpensearchLink payload: %s", links)
    patchMetadata(record_id, links, master_password)


def updateDLLink(project: str, link: str, master_password: str = None):
    """Set the OPENSEARCH_LINK on all records of a project."""
    record_ids = getRecords4Project(project)
    for i, record_id in enumerate(record_ids, start=1):
        logger.info("update record: %s %d/%d", record_id, i, len(record_ids))
        updateOpensearchLink(record_id, link, master_password)


def addProject(base_project: str, additional_project: Dict, master_password: str = None):
    """Add a project entry to all records of base_project if not already present."""
    record_ids = getRecords4Project(base_project)
    for i, record_id in enumerate(record_ids, start=1):
        logger.info("update record: %s %d/%d", record_id, i, len(record_ids))
        data = getMetadataRecord(record_id)
        project_set = data['projectSet']
        if not any(d['shortName'] == additional_project['shortName'] for d in project_set):
            project_set.append(additional_project)
            patchMetadata(record_id, {
                "projectSet": project_set,
                "type": "COLLECTION"
            }, master_password)


def updateTemplate(project: str, name: str, master_password: str = None):
    """Set the clientTemplateName on all records of a project."""
    record_ids = getRecords4Project(project)
    for i, record_id in enumerate(record_ids, start=1):
        logger.info("update record: %s %d/%d", record_id, i, len(record_ids))
        patchMetadata(record_id, {
            "clientTemplateName": name,
            "type": "COLLECTION"
        }, master_password)


def findTemplates():
    """Print template names that reference 'metadata-upload'."""
    response = getPublic(URL_TEMPLATES + "/list")
    data = json.loads(response.text)
    for metadata in data:
        response = getPublic(URL_TEMPLATES + "/byname/" + metadata['name'] + "?source=true")
        if "metadata-upload" in response.text:
            logger.info("template with metadata-upload: %s", metadata['name'])


def findWithTemplate(templates: List[str]):
    """Print UUIDs of catalogue records whose clientTemplateName is in the given list."""
    response = getPublic(URL_CATALOGUE + "/summaries")
    summaries = json.loads(response.text)
    results = summaries['results']
    for i, summary in enumerate(results, start=1):
        logger.debug("scanning record %d/%d", i, len(results))
        record = getMetadataRecord(summary['id'])
        if record['clientTemplateName'] in templates:
            logger.info("match: %s", summary['id'])


def updateDOI(record_id: str, doi: str, master_password: str = None):
    """Set the DOI identifier on a catalogue record."""
    md = {
        "identifiers": [{
            "code": doi,
            "codeSpace": "http://dx.doi.org/"
        }],
        "type": "COLLECTION"
    }
    patchMetadata(record_id, md, master_password)


def updateLicenceCCBY(record_id: str, master_password: str = None):
    """Set the CC BY 4.0 licence on a catalogue record."""
    licence = {
        "distributionInformation": {
            "embargoStartDate": "",
            "embargoDuration": 0,
            "registrationNeeded": False,
            "authenticationNeeded": False,
            "dataPolicyDescription": {"en": "", "fr": ""},
            "dataPolicyUrl": "",
            "licenceName": "Creative Commons Attribution 4.0 International licence",
            "licenceVersion": "CC BY 4.0",
            "licenceUrl": "https://creativecommons.org/licenses/by/4.0/deed.en",
            "description": {
                "en": (
                    "All data are licensed under the Creative Commons Attribution 4.0 "
                    "International license (CC BY 4.0) "
                    "![CC BY 4.0](https://permalink.aeris-data.fr/cc-by \"CC BY 4.0\"). "
                    "This license allows potential users to distribute, remix, adapt, and "
                    "build upon the material in any medium or format. Proper credit should, "
                    "however, be extended to data providers, along with the appropriate "
                    "citation of the datasets."
                ),
                "fr": ""
            }
        },
        "type": "COLLECTION"
    }
    patchMetadata(record_id, licence, master_password)


def testOSLink():
    response = getPublic(URL_CATALOGUE + "summaries?project=")
    data = json.loads(response.text)
    for summary in data['results']:
        print(summary)
    import sys
    sys.exit(0)
    # Kept for reference — bulk update of legacy opensearch links
    # for summary in data['results']:
    #     record = getMetadataRecord(summary['id'])
    #     if "SAFIRE+" in [project['shortName'] for project in record['projectSet']]:
    #         print("IGNORE SAFIRE")
    #     elif record['links'] is None:
    #         print("NO LINK")
    #     else:
    #         for link in record['links']:
    #             if "OPENSEARCH_LINK" in link['type'] and "sedoo-campaigns-rest" in link["url"]:
    #                 updateOpensearchLink(summary['id'], "https://api.sedoo.fr/aeris-catalogue-prod/data/")


def testOS():
    response = getPublic(URL_CATALOGUE + "summaries?project=")
    data = json.loads(response.text)
    results = data['results']
    for i, summary in enumerate(results, start=1):
        print(f"update record: {summary} {i}/{len(results)}")
        record = getMetadataRecord(summary['id'])
        if record['links'] is None:
            print("NO LINK")
        else:
            for link in record['links']:
                if (
                    "OPENSEARCH_LINK" in link['type']
                    and "https://api.sedoo.fr/sedoo-campaigns-rest/dataset/v1_0" in link["url"]
                ):
                    print("TO UPDATE!!!!!!!")


if __name__ == '__main__':
    testOS()
