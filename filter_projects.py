# Filter all GHTorrent GitHub projects, using the following stages:
#
# Pass 1: Remove projects which don't contain GitHub Actions workflow file
# Pass 2: Remove projects with few contributors
# Pass 3: Semi-automatically or manually remove projects that don't really use CI
#

import os
import json
from typing import List
import pandas as pd
import numpy as np
from data_io import write_df_to_csv_file, write_dict_to_json_file
from ghtorrent import (
    GHTORRENT_PATH,
    PROJECT_COLS,
    PROJECT_MEMBERS_COLS,
    PROJECT_MEMBERS_PATH
)
from github_api_client import get_workflows_for_repos, parse_graphql_query_workflow_filenames

NUM_PARTITIONS = 10
NUM_GRAPHQL_PARTITIONS = 1000


def filter_by_member_count(output_projects_path: str):
    print("[!] Filtering out projects with < 5 members")

    # Load project_members table
    print('Loading project-member associations...')
    project_members_df = pd.read_csv(
        PROJECT_MEMBERS_PATH,
        index_col=False,
        names=PROJECT_MEMBERS_COLS
    )
    print(f"Loaded {project_members_df.shape[0]} project-member associations")

    # Remove any potential duplicate memberships
    project_members_df.drop_duplicates(
        subset=['repo_id', 'user_id'], inplace=True)
    print(
        f"There are {project_members_df.shape[0]} unique project-member associations")
    print(
        f"There are {project_members_df['repo_id'].nunique()} unique projects associated to members")
    print(project_members_df)

    repo_member_counts = project_members_df['repo_id'].value_counts()
    print(f"Member count mean: {repo_member_counts.mean()}")
    print(f"Member count median: {repo_member_counts.median()}")
    print(f"Member count std: {repo_member_counts.std()}")

    """
    repos_gte1 = repo_member_counts[repo_member_counts >= 1].shape[0]
    repos_gte2 = repo_member_counts[repo_member_counts >= 2].shape[0]
    repos_gte5 = repo_member_counts[repo_member_counts >= 5].shape[0]
    repos_gte10 = repo_member_counts[repo_member_counts >= 10].shape[0]
    repos_gte25 = repo_member_counts[repo_member_counts >= 25].shape[0]

    print(f"{repos_gte1} repos have >= 1 member")
    print(f"{repos_gte2} repos have >= 2 members")
    print(f"{repos_gte5} repos have >= 5 members")
    print(f"{repos_gte10} repos have >= 10 members")
    print(f"{repos_gte25} repos have >= 25 members")
    """

    repos_gte5 = repo_member_counts[repo_member_counts >= 5]
    repos_gte5 = repos_gte5.index.values
    print(f"There are {len(repos_gte5)} projects with >= 5 members")

    for i in range(NUM_PARTITIONS):
        print(f"Loading projects (partition {i+1}/{NUM_PARTITIONS})...")
        projects_path = f"{GHTORRENT_PATH}projects_split{i}.csv"
        projects_df = pd.read_csv(
            projects_path,
            index_col=False,
            names=PROJECT_COLS
        )
        print(f"Loaded {projects_df.shape[0]} projects")
        # print(projects_df)

        projects_df = projects_df[projects_df.repo_id.isin(repos_gte5)]
        print(
            f"Removed projects with < 5 members, there are now {projects_df.shape[0]} projects")

        filtered_projects_path = f"data/projects_gte5_members_split{i}.csv"
        write_df_to_csv_file(projects_df, filtered_projects_path)
        print(f"Wrote to {filtered_projects_path}")

    print(f"Done filtering projects into {NUM_PARTITIONS} partitions")

    # Concatenate all partitioned projects that passed the filter
    os.system(
        f"cat data/projects_gte5_members_split*.csv > {output_projects_path}")
    print(f"[!] Wrote filtered projects file to {output_projects_path}")
    print("[!] Done filtering out projects with < 5 members")


def filter_by_workflows(input_projects_path: str, output_projects_path: str):
    print("[!] Filtering out projects that do not use GitHub Actions")

    # Load the curretn set of projects to be filtered
    print("Loading projects...")
    projects_df = pd.read_csv(
        input_projects_path,
        index_col=False,
        names=PROJECT_COLS
    )
    print(f"Loaded {projects_df.shape[0]} projects")
    repos = [
        {
            'id': f"repo{r['repo_id']}",
            'owner': r['url'].split('/')[-2],
            'name': r['url'].split('/')[-1]
        }
        for r in projects_df.to_dict(orient="records")
    ]

    # Partition the projects, then query for workflows contained in the projects of each partition
    repos_partitions = np.array_split(repos, NUM_GRAPHQL_PARTITIONS)
    for i in range(0, len(repos_partitions)):
        repos_partition = repos_partitions[i]
        actions_output_path = f"data/actions_projects_gte5_members_split{i}.json"
        print(
            f"Querying GitHub Actions usage for projects (partition {i+1}/{NUM_GRAPHQL_PARTITIONS})...")
        get_workflows_for_repos(repos_partition.tolist(), actions_output_path)

    # Parse response to determine which have at least 1 workflow
    query_responses = [
        f"data/actions_projects_gte5_members_split{i}.json" for i in range(NUM_GRAPHQL_PARTITIONS)]
    project_workflows_dict = extract_workflow_filenames_from_projects(
        query_responses)
    print(
        f"There are {len(project_workflows_dict.keys())} projects using GitHub Actions")

    # Write projects to output file
    write_dict_to_json_file(project_workflows_dict, output_projects_path)
    print(f"[!] Wrote filtered projects file to {output_projects_path}")
    print("[!] Done filtering out projects that do not use GitHub Actions")


def extract_workflow_filenames_from_projects(query_response_filenames: List[str]):
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
        with open(filename) as json_file:
            query = json.load(json_file)
            project_workflows_dict = parse_graphql_query_workflow_filenames(
                query)

            # Merge the workflows from this response with all others
            for repo_id, filenames in project_workflows_dict.items():
                if repo_id in all_project_workflows_dict:
                    print(
                        f"WARNING: Workflow files from repo with ID {repo_id} have already been parsed, will replace.")
                all_project_workflows_dict[repo_id] = filenames

    return all_project_workflows_dict


if __name__ == "__main__":
    projects_gte5_members_path = 'data/projects_gte5_members.csv'
    actions_projects_gte5_members_path = 'data/actions_projects_gte5_members.csv'

    # Execute filtering stages (must be done in order, due to partitioning in first pass)
    filter_by_member_count(projects_gte5_members_path)
    filter_by_workflows(projects_gte5_members_path,
                        actions_projects_gte5_members_path)
