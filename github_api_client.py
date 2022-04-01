import os
import pandas as pd
import numpy as np
from typing import Any, Dict, List, Optional
from requests.utils import quote
from base_api_client import OptionalParams, get_from_url, post_to_url
from data_io import OutputFile, read_dict_from_json_file, write_dict_to_json_file
from projects import decode_repo_and_workflow_key, decode_repo_key, encode_repo_and_workflow_key
from workflows import WorkflowFilenameDict, WorkflowInfoDict

API_USERNAME = os.environ['api_username']
API_PASSWORD = os.environ['api_password']
GITHUB_BASE_URL = os.environ['github_base_url']
GITHUB_DATE_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
AUTH = (API_USERNAME, API_PASSWORD)


def build_dup_workflow_warning(repo_id, workflow_filename):
    return f"WARNING: Workflow file {workflow_filename} from repo with ID {repo_id} has already been retrieved, will replace."


def build_dup_branch_name_warning(repo_id):
    return f"WARNING: Default branch name for repo with ID {repo_id} has already been retrieved, will replace."


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
    full_url = f"{GITHUB_BASE_URL}{slug}"

    def execute_request_for_page(page: int):
        params_with_page = params if params is not None else {}
        params_with_page['per_page'] = per_page
        params_with_page['page'] = page
        return get_from_url(
            url=full_url,
            output_filename=None,
            auth=AUTH,
            params=params_with_page
        )

    page, all_responses = 1, []
    while page <= max_pages:
        # Get workflow runs for current page
        page_res = execute_request_for_page(page)

        # Check for unexpected omission of res_key in res body, if specified
        if res_key is not None and res_key not in page_res:
            if 'message' in page_res:
                # We skip 'Not Found' errors, add empty list in case previous pages were non-empty
                if page_res['message'] == 'Not Found':
                    print(
                        f"WARNING: GET {full_url} (page {page}) returned 'Not Found', skipping...")
                    page_res[res_key] = []
                else:
                    print(
                        f"ERROR: GET {full_url} (page {page}) returned message: {page_res['message']}, aborting...")
                    exit()
            else:
                print(
                    f"ERROR: Response to GET {full_url} (page {page}) is missing key '{res_key}', aborting...")
                print(page_res)
                exit()

        # Add workflow runs to the running list
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


def build_graphql_query_default_branch(id: str, owner: str, name: str) -> str:
    """Build a GitHub API GraphQL query to get the name of the default branch of a given repo."""
    return f"""
    {id}: repository(owner: "{owner}", name: "{name}") {{
        defaultBranchRef {{
            name
        }}
    }}
    """


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


def parse_graphql_query_default_branch(res: Dict[str, Any]) -> Dict[str, str]:
    """
    Parse the response to a GitHub API GraphQL query getting the default branch name for given
    repos. A dictionary is returned, mapping each repo ID str (eg. `123`) to the repo's default
    branch name. Example return value:
    ```
    {
        '123': 'main',
        '456': 'master',
        ...
    }
    """

    new_branch_names_dict = {}

    if 'data' in res and res['data'] is not None:
        for repo_key, data_val in res['data'].items():
            if data_val is not None:
                repo_val = res['data'][repo_key]
                if 'defaultBranchRef' in repo_val and repo_val['defaultBranchRef'] is not None:
                    branch_obj = repo_val['defaultBranchRef']
                    if 'name' in branch_obj and branch_obj['name'] is not None:
                        # Decode the repo ID, and add the default branch name to the dict
                        default_branch_name = branch_obj['name']
                        repo_id = decode_repo_key(repo_key)
                        new_branch_names_dict[repo_id] = default_branch_name

    return new_branch_names_dict


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


def parse_graphql_query_workflow_file(res: str, old_project_workflows_dict: WorkflowFilenameDict) -> Dict[str, List]:
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


def combine_partitioned_workflow_files(query_response_filenames: List[str],
                                       old_project_workflows_dict: WorkflowFilenameDict) -> WorkflowInfoDict:
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


def get_default_branch_for_repos(projects: List[Dict[str, str]],
                                 output_filename: OutputFile = None) -> Dict[str, str]:
    """
    Get the default branch name for all projects / repos in a given list. Returns a dict mapping
    repo ID str to default branch name.
    """
    queries = [build_graphql_query_default_branch(
        p['id'], p['owner'], p['name']) for p in projects]
    query = ' '.join(queries)
    query = f"{{ {query} }}"
    return parse_graphql_query_default_branch(run_graphql_query(query, output_filename))


def get_default_branch_for_repos_partitioned(partitioned_projects: List[List[Dict[str, str]]],
                                             num_partitions: int,
                                             partition_output_prefix: str) -> Dict[str, str]:
    """
    Get the default branch name for all projects / repos (given in a partitioned list, to support
    partitioned API requests). Returns a dict mapping repo ID str to default branch name.
    """
    branch_names = {}
    for i, projects_partition in enumerate(partitioned_projects):
        # Get branch names for projects in this partition
        partition_output_filename = f"{partition_output_prefix}_split{i}.json"
        print(
            f"Getting default branch names for projects in partition {i+1}/{num_partitions}...")
        new_branch_names = get_default_branch_for_repos(
            projects_partition, partition_output_filename)

        # Combine all results with those from this partition
        for repo_id_str, def_branch_name in new_branch_names.items():
            if repo_id_str in branch_names:
                print(build_dup_branch_name_warning(repo_id_str))
            branch_names[repo_id_str] = def_branch_name

    output_filename = f"{partition_output_prefix}.json"
    if output_filename is not None:
        write_dict_to_json_file(branch_names, output_filename)
        print(
            f"Wrote default branch names for {len(branch_names.keys())} projects to {output_filename}")

    return branch_names


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
                                   partition_output_prefix: str) -> Dict[str, Dict[str, Dict[str, str]]]:
    """
    Get the text (YAML) content of all workflow files in a given dict (`project_workflows_dict`).
    More specifically, return an augmented version of `project_workflows_dict` that contains the
    YAML content of each workflow file, in addition to the workflow filename already present.
    Workflow file content is queried from the GitHub API GraphQL, in multiple partitioned requests.
    Example `project_workflows_dict`:
    ```
    {
        "123": [
            { "name": "release.yml" },
            { "name": "test.yml" },
            ...
        ],
        ...
    }
    ```
    Example return value:
    ```
    {
        "123": {
            "0": { "name": "release.yml", "text": "These are release YAML contents" },
            "1": { "name": "test.yml", "text": "These are test YAML contents" },
            ...
        },
        ...
    }
    ```
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

    output_filename = f"{partition_output_prefix}.json"
    if output_filename is not None:
        write_dict_to_json_file(new_workflows_dict, output_filename)
        print(
            f"Wrote YAML workflows for {len(new_workflows_dict.keys())} projects to {output_filename}")

    return new_workflows_dict
