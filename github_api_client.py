import os
from requests.utils import quote
from base_api_client import OptionalStr, get_from_url

API_USERNAME = os.environ['api_username']
API_PASSWORD = os.environ['api_password']
GITHUB_BASE_URL = os.environ['github_base_url']
AUTH = (API_USERNAME, API_PASSWORD)


def get_from_github(slug: str, output_filename: OptionalStr = None):
    return get_from_url(f"{GITHUB_BASE_URL}{slug}", AUTH, output_filename)


def get_user(username):
    return get_from_github(f"/users/{username}")


def run_search(output_filename: OptionalStr = None):
    query = "build test path:.github/workflows extension:yml"
    return get_from_github(f"/search/code?q={quote(query)}", output_filename)


def get_workflow(owner: str, repo: str, workflow_id_or_filename: str,
                 output_filename: OptionalStr = None):
    return get_from_github(
        f"/repos/{owner}/{repo}/actions/workflows/{workflow_id_or_filename}",
        output_filename
    )


def get_workflow_runs(owner: str, repo: str, workflow_id_or_filename: str,
                      output_filename: OptionalStr = None):
    return get_from_github(
        f"/repos/{owner}/{repo}/actions/workflows/{workflow_id_or_filename}/runs",
        output_filename
    )
