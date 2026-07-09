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


# https://docs.github.com/en/rest/git/refs?apiVersion=2022-11-28#get-a-reference
class GitObject(TypedDict):
    type: str
    sha: str
    url: str


class GitRef(TypedDict):
    ref: str
    node_id: str
    url: str
    object: GitObject


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


def get_alternate_tag_for_edge_package_version(
    package_name: str, owner: str = "Sage-Bionetworks"
):
    versions = get_package_versions(owner, package_name)
    edge_version = get_edge_package_version(versions)
    return get_nonedge_tag(edge_version["metadata"]["container"]["tags"])


def get_image_version(
    package_name: str, configured_version: str, owner: str = "Sage-Bionetworks"
) -> str:
    # For 'edge', returns the alternate tag (typically commit SHA) from the edge image.
    # For other versions, returns the configured version as-is.
    if configured_version == "edge":
        return get_alternate_tag_for_edge_package_version(package_name, owner)
    return configured_version


def get_short_commit_sha(
    repo: str,
    image_tag: str,
    configured_version: str,
    owner: str = "Sage-Bionetworks",
    tag_prefix: str = "",
) -> str:
    # Return a short (7 char) commit SHA for the given version.

    # For 'edge', image_tag is typically the commit SHA. However, if a release
    # is created for the same commit, the SHA tag moves to the release image,
    # resulting in image_tag being 'edge'.
    # For other versions, fetches the commit SHA from the git tag.

    if configured_version == "edge":
        return image_tag[:7]
    commit_sha = get_commit_sha_for_tag(owner, repo, f"{tag_prefix}{image_tag}")
    return commit_sha[:7]


def get_git_ref(owner: str, repo: str, tag: str) -> GitRef:
    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        raise SystemExit("Must set environment variable `GITHUB_TOKEN`.")

    url = f"https://api.github.com/repos/{owner}/{repo}/git/ref/tags/{tag}"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {github_token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise SystemExit(f"Error: GitHub Tag API request failed: {e}")


def get_commit_sha_for_tag(owner: str, repo: str, tag: str) -> str:
    ref_data = get_git_ref(owner, repo, tag)

    # The ref points to either a commit or a tag object
    object_type = ref_data["object"]["type"]
    object_sha = ref_data["object"]["sha"]

    if object_type == "commit":
        return object_sha
    else:
        raise SystemExit(
            f"Error: Tag '{tag}' is not a lightweight tag (type: {object_type}). "
            "Only lightweight tags are supported."
        )
