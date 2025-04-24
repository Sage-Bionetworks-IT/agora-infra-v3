import requests
import os
from typing import TypedDict, List, Literal

# https://docs.github.com/en/rest/packages/packages?apiVersion=2022-11-28#list-package-versions-for-a-package-owned-by-an-organization


class ContainerMetadata(TypedDict):
    tags: List[str]


class PackageMetadata(TypedDict):
    package_type: Literal["container"]
    container: ContainerMetadata


class PackageVersion(TypedDict):
    id: int
    id: int
    name: str
    url: str
    package_html_url: str
    created_at: str
    updated_at: str
    html_url: str
    metadata: PackageMetadata


class PackageVersionList:
    List[PackageVersion]


def get_package_versions(owner: str, package_name: str) -> PackageVersionList:
    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        raise SystemExit("Must set environment variable `GITHUB_TOKEN`.")

    url = f"https://api.github.com/orgs/{owner}/packages/container/{package_name}/versions"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {github_token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        raise SystemExit(f"Error: API request failed: {e}")


def get_edge_package_version(versions: PackageVersionList) -> PackageVersion:
    version: PackageVersion
    for version in versions:
        if "edge" in version["metadata"]["container"]["tags"]:
            return version


def get_nonedge_tag(tags: List[str]) -> str:
    if len(tags) == 1:
        return tags[0]
    return [tag for tag in tags if tag != "edge"][0]


def get_alternate_tag_for_edge_package_version(owner: str, package_name: str):
    versions = get_package_versions(owner, package_name)
    edge_version = get_edge_package_version(versions)
    return get_nonedge_tag(edge_version["metadata"]["container"]["tags"])
