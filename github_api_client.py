import os
from typing import Any, Dict, List
from requests.utils import quote
from base_api_client import get_from_url, post_to_url
from data_io import OutputFile

API_USERNAME = os.environ['api_username']
API_PASSWORD = os.environ['api_password']
GITHUB_BASE_URL = os.environ['github_base_url']
AUTH = (API_USERNAME, API_PASSWORD)


def get_from_github(slug: str, output_filename: OutputFile = None):
    return get_from_url(f"{GITHUB_BASE_URL}{slug}", AUTH, output_filename)


def run_graphql_query(query: str, output_filename: OutputFile = None):
    return post_to_url(
        f"{GITHUB_BASE_URL}/graphql",
        {'query': query},
        AUTH,
        output_filename
    )


def get_user(username):
    return get_from_github(f"/users/{username}")


def run_search(output_filename: OutputFile = None):
    query = 'build test path:.github/workflows extension:yml'
    return get_from_github(f"/search/code?q={quote(query)}", output_filename)


def get_workflow(owner: str, repo: str, workflow_id_or_filename: str,
                 output_filename: OutputFile = None):
    return get_from_github(
        f"/repos/{owner}/{repo}/actions/workflows/{workflow_id_or_filename}",
        output_filename
    )


def get_workflow_runs(owner: str, repo: str, workflow_id_or_filename: str,
                      output_filename: OutputFile = None):
    return get_from_github(
        f"/repos/{owner}/{repo}/actions/workflows/{workflow_id_or_filename}/runs",
        output_filename
    )


def build_graphql_query_repo_workflows(id: str, owner: str, name: str) -> str:
    return f"""
    {id}: repository(owner: "{owner}", name: "{name}") {{
        object(expression: "HEAD:.github/workflows") {{
            ... on Tree {{
                entries {{
                    name
                }}
            }}
        }}
    }}
    """


def get_workflows_for_repos(repos: List[Dict[str, str]],
                            output_filename: OutputFile = None) -> Any:
    queries = [build_graphql_query_repo_workflows(
        r['id'], r['owner'], r['name']) for r in repos]
    query = ' '.join(queries)
    query = f"{{ {query} }}"
    run_graphql_query(query, output_filename)
