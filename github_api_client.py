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


def build_graphql_query_workflow_filenames(id: str, owner: str, name: str) -> str:
    """Build a GitHub API GraphQL query to get the filenames of all workflows defined in a given
    project (repository). Workflows are presumed to exist at `HEAD:.github/workflows/`."""
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


def build_graphql_query_workflow_file(id: str, owner: str, name: str, filename: str) -> str:
    """Build a GitHub API GraphQL query to get the contents of a given project (repository) YAML
    workflow file. The file is presumed to exist at `HEAD:.github/workflows/{filename}`."""
    return f"""
    {id}: repository(owner: "{owner}", name: "{name}") {{
        object(expression: "HEAD:.github/workflows/{filename}") {{
            ... on Blob {{
                text
            }}
        }}
    }}
    """


def parse_graphql_query_workflow_filenames(res: str):
    """
    Parse the response to a GitHub API GraphQL query getting workflow filnames for a set of
    projects. A dictionary is returned, mapping each repo key (eg. `repo123`) to a non-empty list
    of its workflow filenames. Projects without any workflow files, or those which triggered
    errors, will be omitted from the returned dictionary. Example return value:
    ```
    {
        '123': [
            { "name": "build.yml" },
            { "name": "release.yml" }
        ]
    }
    """
    project_workflows_map = {}

    if 'data' in res and res['data'] is not None:
        for repo_id_key, data_val in res['data'].items():
            if data_val is not None:
                repo_val = res['data'][repo_id_key]
                if 'object' in repo_val and repo_val['object'] is not None:
                    repo_obj = repo_val['object']
                    if 'entries' in repo_obj and repo_obj['entries'] is not None:
                        repo_entires = repo_obj['entries']
                        if len(repo_entires) > 0:
                            repo_id = repo_id_key.replace('repo', '')
                            project_workflows_map[repo_id] = repo_entires

    return project_workflows_map


def get_workflows_for_repos(repos: List[Dict[str, str]],
                            output_filename: OutputFile = None) -> Any:
    queries = [build_graphql_query_workflow_filenames(
        r['id'], r['owner'], r['name']) for r in repos]
    query = ' '.join(queries)
    query = f"{{ {query} }}"
    run_graphql_query(query, output_filename)


def get_workflow_files_for_repos(repos: List[Dict[str, str]],
                                 output_filename: OutputFile = None) -> Any:
    queries = [build_graphql_query_workflow_file(
        r['id'], r['owner'], r['name'], r['filename']) for r in repos]
    query = f"{{ {' '.join(queries)} }}"
    run_graphql_query(query, output_filename)
