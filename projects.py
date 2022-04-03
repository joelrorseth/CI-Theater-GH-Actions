import os
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from config import MEMBER_COUNT_SIZES_MAP
from data_io import read_df_from_csv_file, write_df_to_csv_file

GHTORRENT_PATH = os.environ['ghtorrent_path']
PROJECT_MEMBERS_PATH = f"{GHTORRENT_PATH}project_members.csv"
PROJECT_COLS = ['repo_id', 'url', 'owner_id', 'name', 'descriptor',
                'language', 'created_at', 'forked_from', 'deleted', 'updated_at', 'dummy']
PROJECT_MEMBERS_COLS = ['repo_id', 'user_id', 'created_at']
NULL_SYMBOL = "\\N"

Projects = List[Dict[str, str]]
PartitionedProjects = List[Projects]


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


def load_original_project_members(quiet: bool = False) -> pd.DataFrame:
    """
    Read GHTorrent GitHub project member associations into a `pd.DataFrame`. Note that all
    original columns are maintained ('repo_id', 'user_id', and 'created_at').
    """
    if not quiet:
        print('Loading project-member associations...')
    project_members_df = read_df_from_csv_file(
        PROJECT_MEMBERS_PATH, PROJECT_MEMBERS_COLS)

    # Remove any potential duplicate memberships
    project_members_df.drop_duplicates(
        subset=['repo_id', 'user_id'], inplace=True)

    num_associations = project_members_df.shape[0]
    num_projects = project_members_df['repo_id'].nunique()
    if not quiet:
        print(
            f"Loaded {num_associations} unique member associations to {num_projects} projects")
    return project_members_df


def get_member_count_sizes_for_projects(unencoded_projects: Projects) -> Dict[str, str]:
    """
    Get a dict mapping specified project ids to the corresponding member count size category.
    Input projects must have unencoded 'repo_id'. Example return value:
    ```
    {
        '123': 'Very Small',
        '456': 'Medium',
        ...
    }
    ```
    """
    def get_size_for_num_members(num_members: int) -> str:
        for size, size_range in MEMBER_COUNT_SIZES_MAP:
            if num_members >= size_range[0] and num_members <= size_range[1]:
                return size
        return 'Unknown'

    project_members_df = load_original_project_members(True)
    member_counts = project_members_df['repo_id'].value_counts()
    target_repo_ids = set([proj['id'] for proj in unencoded_projects])
    sizes_map = {}

    # Extract member count for specified projects, bin these numbers into size categories
    for idx, repo_id in enumerate(member_counts.index.tolist()):
        repo_id_str = str(repo_id)
        num_members = member_counts[idx]
        if repo_id_str in target_repo_ids:
            sizes_map[repo_id_str] = get_size_for_num_members(num_members)

    return sizes_map


def load_full_projects(input_projects_path: str, quiet: bool = False) -> pd.DataFrame:
    """
    Read GitHub projects from the specified CSV file (ie. in GHTorrent format) into a
    pd.DataFrame, without modifying the data in any way.
    """
    if not quiet:
        print(f"Loading projects from {input_projects_path}...")
    projects_df = read_df_from_csv_file(input_projects_path, PROJECT_COLS)
    if not quiet:
        print(f"Loaded {projects_df.shape[0]} projects")
    return projects_df


def save_full_projects_df(projects_df: pd.DataFrame, output_projects_path: str) -> None:
    """Write a pd.DataFrame containing full projects to CSV file."""
    write_df_to_csv_file(projects_df, output_projects_path)
    print(f"Wrote {projects_df.shape[0]} projects to {output_projects_path}")


def load_projects(input_projects_path: str,
                  should_encode_repo_key: bool = True) -> Projects:
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
    projects_df = load_full_projects(input_projects_path)
    return [
        {
            'id': encode_repo_key(r['repo_id']) if should_encode_repo_key else str(r['repo_id']),
            'owner': r['url'].split('/')[-2],
            'name': r['url'].split('/')[-1],
            'language': r['language']
        }
        for r in projects_df.to_dict(orient="records")
    ]


def load_projects_and_partition(input_projects_path: str, num_partitions: int,
                                should_encode_repo_key: bool = True) -> PartitionedProjects:
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
