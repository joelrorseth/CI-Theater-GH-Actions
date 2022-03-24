import os
import pandas as pd
import numpy as np
from typing import Any, Dict, List, Optional, Tuple
from requests.utils import quote
from base_api_client import OptionalParams, get_from_url, post_to_url
from data_io import OutputFile, read_dict_from_json_file, write_dict_to_json_file

API_USERNAME = os.environ['api_username']
API_PASSWORD = os.environ['api_password']
GITHUB_BASE_URL = os.environ['github_base_url']
AUTH = (API_USERNAME, API_PASSWORD)


def encode_repo_and_workflow_key(repo_id: str, workflow_filename_idx: str) -> str:
    """
    Encode a key for use as an alias in a GraphQL query for a specific workflow file. These keys
    are of the form `repo123workflow456`, which indicate that the query was for the repo with
    GHTorrent repo_id of 123 and workflow filename at index 456 in the project's
    project_workflows_dict entry. A single key (str) is returned.
    """
    return f"repo{repo_id}workflow{workflow_filename_idx}"


def decode_repo_and_workflow_key(graphql_key: str) -> Tuple[str, int]:
    """
    Decode a key used to alias a GraphQL query for a specific workflow file. These keys are of
    the form `repo123workflow456`, which indicate that the query was for the repo with GHTorrent
    repo_id of 123 and workflow filename at index 456 in the project's project_workflows_dict
    entry. A tuple is returned, containing the repo_id (str) and workflow filename index (int).
    """

    temp = graphql_key.split('workflow')
    repo_id, workflow_idx = temp[0].replace('repo', ''), temp[1]
    return str(repo_id), int(workflow_idx)


def build_dup_workflow_warning(repo_id, workflow_filename):
    return f"WARNING: Workflow file {workflow_filename} from repo with ID {repo_id} has already been retrieved, will replace."


def get_from_github(slug: str, output_filename: OutputFile = None, params: OptionalParams = None):
    return get_from_url(f"{GITHUB_BASE_URL}{slug}", output_filename, AUTH, params)


def get_from_github_paged(slug: str, per_page: int, max_pages: int,
                          params: OptionalParams = None, output_filename: OutputFile = None,
                          res_key: Optional[str] = None) -> List[Any]:
    """
    Repeatedly execute a GET request (to page through all available results), then return the
    aggregation of all paged results (in a combined list). The `per_page` size (the number of
    results per page) and `max_pages` (maximum number of pages to execute) are also required. An
    optional `res_key` can be provided to extract the aggregated response objects 1 layer deep in
    the json (ie. res[res_key]), else the response will be assumed to be an array of objects to be
    aggregated.
    """
    def execute_request_for_page(page: int):
        params_with_page = params if params is not None else {}
        params_with_page['per_page'] = per_page
        params_with_page['page'] = page
        return get_from_url(
            url=f"{GITHUB_BASE_URL}{slug}",
            output_filename=None,
            auth=AUTH,
            params=params_with_page
        )

    page, all_responses = 1, []
    while page <= max_pages:
        # Get workflow runs for current page, add to the running list
        page_res = execute_request_for_page(page)
        page_workflow_runs = page_res[res_key] if res_key is not None else page_res
        all_responses.extend(page_workflow_runs)

        # Stop paging when we recieve less results than the page size requested
        if len(page_workflow_runs) < per_page:
            break
        page += 1

    # Now that all results have been aggregated, write results to JSON file
    write_dict_to_json_file(all_responses, output_filename)
    return all_responses


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


def get_runs_for_workflow(owner: str, repo: str, branch: str, workflow_id_or_filename: str,
                          output_filename: OutputFile = None, max_pages: Optional[int] = 3,
                          per_page: Optional[int] = 100) -> List[Any]:
    """
    Return all workflow runs for a workflow (identified by its workflow_id or file name).
    Only workflows triggered on the specified branch, by a push event, are returned. Results will
    be aggregated across pages, if specified.
    https://docs.github.com/en/rest/reference/actions#list-workflow-runs
    """
    return get_from_github_paged(
        f"/repos/{owner}/{repo}/actions/workflows/{workflow_id_or_filename}/runs",
        per_page,
        max_pages,
        {'branch': branch, 'event': 'push', 'exclude_pull_requests': True},
        output_filename,
        'workflow_runs'
    )


def get_all_workflow_runs(owner: str, repo: str, branch: str, output_filename: OutputFile = None,
                          max_pages: Optional[int] = 20, per_page: Optional[int] = 100) -> List[Any]:
    """
    Return all workflow runs for a repository. Only workflows triggered on the specified branch,
    by a push event, are returned. Results will be aggregated across pages, if specified.
    https://docs.github.com/en/rest/reference/actions#list-workflow-runs-for-a-repository
    """
    return get_from_github_paged(
        f"/repos/{owner}/{repo}/actions/runs",
        per_page,
        max_pages,
        {'branch': branch, 'event': 'push', 'exclude_pull_requests': True},
        output_filename,
        'workflow_runs'
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
            { "name": "release.yml" },
            ...
        ],
        ...
    }
    """
    project_workflows_dict = {}

    if 'data' in res and res['data'] is not None:
        for repo_id_key, data_val in res['data'].items():
            if data_val is not None:
                repo_val = res['data'][repo_id_key]
                if 'object' in repo_val and repo_val['object'] is not None:
                    repo_obj = repo_val['object']
                    if 'entries' in repo_obj and repo_obj['entries'] is not None:
                        repo_entries = repo_obj['entries']
                        if len(repo_entries) > 0:
                            repo_id = repo_id_key.replace('repo', '')
                            project_workflows_dict[repo_id] = repo_entries

    return project_workflows_dict


def parse_graphql_query_workflow_file(res: str, old_project_workflows_dict: Dict[str, Dict[str, str]]) -> Dict[str, List]:
    """
    Parse the response to a GitHub API GraphQL query getting workflow filnames for a set of
    projects. A dictionary is returned, mapping each repo key (eg. `repo123`) to a non-empty list
    of its workflow filenames. Projects without any workflow files, or those which triggered
    errors, will be omitted from the returned dictionary. The list of repos used for the original
    query is required, in order to reconstruct the workflow filename (which is not returned in the
    query response). Example return value:
    ```
    {
        '123': {
            '0': { "name": "build.yml", "text": "These are my YAML contents" },
            '1': { "name": "release.yml", "text": "These are my YAML contents" },
            ...
        },
        ...
    }
    """
    new_project_workflows_dict = {}

    if 'data' in res and res['data'] is not None:
        for query_id_key, data_val in res['data'].items():
            if data_val is not None:
                repo_val = res['data'][query_id_key]
                if 'object' in repo_val and repo_val['object'] is not None:
                    repo_obj = repo_val['object']
                    if 'text' in repo_obj and repo_obj['text'] is not None:
                        repo_id, workflow_filename_idx = decode_repo_and_workflow_key(
                            query_id_key
                        )
                        workflow_filename_key = str(workflow_filename_idx)
                        workflow_filename = old_project_workflows_dict[
                            repo_id][workflow_filename_idx]['name']
                        workflow_yaml_text = repo_obj['text']

                        if repo_id in new_project_workflows_dict:
                            if workflow_filename_key in new_project_workflows_dict[repo_id]:
                                print(build_dup_workflow_warning(
                                    repo_id, workflow_filename)
                                )
                        else:
                            new_project_workflows_dict[repo_id] = {}

                        # Populate the new project workflows dict (merge the filename and text)
                        # NOTE: Workflow filename index is used as a key in the new dict
                        new_project_workflows_dict[repo_id][workflow_filename_key] = {
                            'name': workflow_filename,
                            'text': workflow_yaml_text
                        }

    return new_project_workflows_dict


def combine_partitioned_workflow_filenames(query_response_filenames: List[str]):
    """
    Given a list of filenames, each whose file is a response to a (partitioned) query to get repo
    workflow filenames, parse and return the filenames ONLY for repos that had any. A dictionary
    is returned, mapping each repo_id to a non-empty list of its workflow filenames, eg:
    ```
    {
        '123': [
            { "name": "build.yml" },
            { "name": "release.yml" }
        ]
    }
    ```
    """
    all_project_workflows_dict = {}

    for filename in query_response_filenames:
        query = read_dict_from_json_file(filename)
        project_workflows_dict = parse_graphql_query_workflow_filenames(
            query)

        # Merge the workflows from this response with all others
        for repo_id, filenames in project_workflows_dict.items():
            if repo_id in all_project_workflows_dict:
                print(
                    f"WARNING: Workflow files from repo with ID {repo_id} have already been parsed, will replace.")
            all_project_workflows_dict[repo_id] = filenames

    return all_project_workflows_dict


def combine_partitioned_workflow_files(query_response_filenames: List[str], old_project_workflows_dict: Dict[str, Dict[str, str]]) -> Dict[str, Dict[str, Dict[str, str]]]:
    """
    Given a list of filenames, each whose file is a response to a (partitioned) query to get the
    content of all project workflows, combine the partitioned results into a single dictionary. A
    dictionary is returned, mapping each repo_id to a dictionary, which itself maps workflow
    filename indices (represented as str) to dictionaries containing workflow filename and YAML
    content. Example return value:
    ```
    {
        '123': {
            '0': { "name": "build.yml", "text": "These are my YAML contents" },
            '1': { "name": "release.yml", "text": "These are my YAML contents" },
            ...
        },
        ...
    }
    ```
    """
    all_project_workflows_dict = {}

    for filename in query_response_filenames:
        query = read_dict_from_json_file(filename)
        project_workflows_dict = parse_graphql_query_workflow_file(
            query, old_project_workflows_dict)

        # Merge the workflows from this response with all others
        for repo_id, repo_workflows in project_workflows_dict.items():
            for workflow_filename_idx, workflow in repo_workflows.items():

                if repo_id in all_project_workflows_dict:
                    if workflow_filename_idx in all_project_workflows_dict[repo_id]:
                        print(build_dup_workflow_warning(
                            repo_id, workflow_filename_idx)
                        )
                else:
                    all_project_workflows_dict[repo_id] = {}

                # NOTE: Workflow filename index is used as a key (treat it like a workflow id)
                all_project_workflows_dict[repo_id][workflow_filename_idx] = {
                    'name': workflow['name'],
                    'text': workflow['text']
                }

    return all_project_workflows_dict


def get_workflows_for_repos(repos: List[Dict[str, str]],
                            output_filename: OutputFile = None) -> Any:
    queries = [build_graphql_query_workflow_filenames(
        r['id'], r['owner'], r['name']) for r in repos]
    query = ' '.join(queries)
    query = f"{{ {query} }}"
    return run_graphql_query(query, output_filename)


def get_workflow_files(workflow_queries: List[Dict[str, str]], output_filename: OutputFile = None) -> Any:
    queries = [build_graphql_query_workflow_file(
        r['id'], r['owner'], r['name'], r['filename']) for r in workflow_queries]
    query = f"{{ {' '.join(queries)} }}"
    return run_graphql_query(query, output_filename)


def get_workflow_files_partitioned(projects_df: pd.DataFrame,
                                   project_workflows_dict: Dict[str, Dict[str, str]],
                                   num_partitions: int,
                                   partition_output_prefix: str,
                                   output_filename: OutputFile = None) -> None:
    """
    Get the specified set of workflow files (their YAML content) for a specified set of projects,
    while partitioning GitHub API GraphQL requests.
    Example `project_workflows_dict`:
    ```
    {
        '123': [
            {'name': 'release.yml'},
            ...
        ],
        ...
    }
    ```
    Example return value:
    ```
    {
        '123': {
            '0': { "name": "release.yml", "text": "These are my YAML contents" },
            ...
        },
        ...
    }
    """

    # Flatten to get one dict for each project-workflow combo
    queries = []
    for r in projects_df.to_dict(orient="records"):
        repo_id = str(r['repo_id'])
        workflow_filenames = project_workflows_dict[repo_id]
        for i, workflow_filename in enumerate(workflow_filenames):
            queries.append({
                'id': encode_repo_and_workflow_key(repo_id, i),
                'owner': r['url'].split('/')[-2],
                'name': r['url'].split('/')[-1],
                'filename': workflow_filename['name']
            })

    # Partition the projects
    query_partitions = np.array_split(queries, num_partitions)

    # Execute a combined query for each partition
    for i in range(0, num_partitions):
        query_partition = query_partitions[i]
        output_path = f"{partition_output_prefix}_split{i}.json"
        print(
            f"Getting workflow YAML for projects in partition {i+1}/{num_partitions}...")
        get_workflow_files(query_partition.tolist(), output_path)

    # Combine the partitioned responses into a single dict
    new_workflows_dict = combine_partitioned_workflow_files(
        [f"{partition_output_prefix}_split{i}.json" for i in range(
            num_partitions)],
        project_workflows_dict
    )

    if output_filename is not None:
        write_dict_to_json_file(new_workflows_dict, output_filename)
        print(
            f"Wrote YAML workflows for {len(new_workflows_dict.keys())} projects to {output_filename}")

    return new_workflows_dict
