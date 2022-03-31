import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from ghtorrent import PROJECT_COLS


def encode_repo_key(repo_id: str) -> str:
    """
    Encode a key for use as an alias in a GraphQL query for a specific repo. Produces a key of
    the form `repo123`, which indicate that the query was for the repo with GHTorrent repo_id of
    123. A single key (str) is returned.
    """
    return f"repo{repo_id}"


def decode_repo_key(graphql_key: str) -> str:
    """
    Decode a key used to alias a GraphQL query for a specific repo. Consumes a key of the form
    `repo123`, which indicate that the query was for the repo with GHTorrent repo_id of 123. The
    repo_id str (eg. `123`) is returned.
    """
    return graphql_key.replace('repo', '')


def encode_repo_and_workflow_key(repo_id: str, workflow_filename_idx: str) -> str:
    """
    Encode a key for use as an alias in a GraphQL query for a specific workflow file. Produces a
    key of the form `repo123workflow456`, which indicate that the query was for the repo with
    GHTorrent repo_id of 123 and workflow filename at index 456 in the project's
    project_workflows_dict entry. A single key (str) is returned.
    """
    return f"repo{repo_id}workflow{workflow_filename_idx}"


def decode_repo_and_workflow_key(graphql_key: str) -> Tuple[str, int]:
    """
    Decode a key used to alias a GraphQL query for a specific workflow file. Consumes a key of
    the form `repo123workflow456`, which indicate that the query was for the repo with GHTorrent
    repo_id of 123 and workflow filename at index 456 in the project's project_workflows_dict
    entry. A tuple is returned, containing the repo_id str (eg. `123`) and workflow filename index
    int (eg. `456`).
    """

    temp = graphql_key.split('workflow')
    repo_id, workflow_idx = temp[0].replace('repo', ''), temp[1]
    return str(repo_id), int(workflow_idx)


def load_projects(input_projects_path: str,
                  should_encode_repo_key: bool = True) -> List[Dict[str, str]]:
    """
    Read GitHub projects from the specified CSV file (ie. in GHTorrent format) into a list of
    dictionaries. Note that only certain columns are retained from the CSV. Example return value:
    ```
    [
        {
            'id': 'repo123', # Use param to decide whether to encode this
            'owner': 'bob',
            'name': 'myproject',
            'language': 'Java'
        },
        ...
    ]
    ```
    """
    # Load projects from JSON
    print("Loading projects...")
    projects_df = pd.read_csv(
        input_projects_path,
        index_col=False,
        names=PROJECT_COLS
    )
    print(f"Loaded {projects_df.shape[0]} projects")

    # Keep pertinent columns only
    return [
        {
            'id': encode_repo_key(r['repo_id']) if should_encode_repo_key else str(r['repo_id']),
            'owner': r['url'].split('/')[-2],
            'name': r['url'].split('/')[-1],
            'language': r['language']
        }
        for r in projects_df.to_dict(orient="records")
    ]


def load_projects_partitioned(input_projects_path: str, num_partitions: int,
                              should_encode_repo_key: bool = True) -> List[List[Dict[str, str]]]:
    """
    Read GitHub projects from the specified CSV file (ie. in GHTorrent format) into a list of
    dictionaries, then partition the dictionaries to form a list of lists of dictionaries.
    Note that only certain columns are retained from the CSV. Example return value:
    ```
    [
        [
            {
                'id': 'repo123', # Use param to decide whether to encode this
                'owner': 'bob',
                'name': 'myproject',
                'language': 'Java'
            },
            ...
        ],
        ...
    ]
    ```
    """
    repos = load_projects(input_projects_path, should_encode_repo_key)

    # Return a partitioning of the loaded projects
    repos_partitions = np.array_split(repos, num_partitions)
    return repos_partitions
