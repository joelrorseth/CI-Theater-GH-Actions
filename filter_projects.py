# Filter all GHTorrent GitHub projects, using the following stages:
#
# Pass 1: Remove projects which don't contain GitHub Actions workflow file
# Pass 2: Remove projects with few contributors
# Pass 3: Semi-automatically or manually remove projects that don't really use CI
#

import os
import pandas as pd
import numpy as np
from data_io import (
    read_df_from_csv_file,
    read_dict_from_json_file,
    write_df_to_csv_file,
    write_dict_to_json_file
)
from ghtorrent import (
    GHTORRENT_PATH,
    PROJECT_COLS,
    PROJECT_MEMBERS_COLS,
    PROJECT_MEMBERS_PATH
)
from github_api_client import (
    combine_partitioned_workflow_filenames,
    get_workflow_files_partitioned,
    get_workflows_for_repos
)

NUM_MEMBER_PARTITIONS = 10
NUM_WORKFLOW_PARTITIONS = 1000
NUM_YAML_PARTITIONS = 60


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

    for i in range(NUM_MEMBER_PARTITIONS):
        print(f"Loading projects (partition {i+1}/{NUM_MEMBER_PARTITIONS})...")
        projects_path = f"{GHTORRENT_PATH}projects_split{i}.csv"
        projects_df = pd.read_csv(
            projects_path,
            index_col=False,
            names=PROJECT_COLS
        )
        print(f"Loaded {projects_df.shape[0]} projects")

        # Remove projects whose repo_id is not in the set of repos having >= 5 members
        projects_df = projects_df[projects_df.repo_id.isin(repos_gte5)]
        print(
            f"Removed projects with < 5 members, there are now {projects_df.shape[0]} projects")

        filtered_projects_path = f"data/projects_gte5_members_split{i}.csv"
        write_df_to_csv_file(projects_df, filtered_projects_path)
        print(f"Wrote to {filtered_projects_path}")

    print(f"Done filtering projects into {NUM_MEMBER_PARTITIONS} partitions")

    # Concatenate all partitioned projects that passed the filter
    os.system(
        f"cat data/projects_gte5_members_split*.csv > {output_projects_path}")
    print(f"[!] Wrote filtered projects file to {output_projects_path}")
    print("[!] Done filtering out projects with < 5 members")
    print(f"[!] # remaining projects: ${projects_df.shape[0]}")


def filter_by_workflow_files(input_projects_path: str, output_projects_path: str, output_workflows_path: str):
    print("[!] Filtering out projects that don't have any GitHub Actions workflow files")

    # Load the current set of projects to be filtered
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
    repos_partitions = np.array_split(repos, NUM_WORKFLOW_PARTITIONS)
    for i in range(0, len(repos_partitions)):
        repos_partition = repos_partitions[i]
        actions_output_path = f"data/actions_projects_gte5_members_split{i}.json"
        print(
            f"Querying GitHub Actions usage for projects (partition {i+1}/{NUM_WORKFLOW_PARTITIONS})...")
        get_workflows_for_repos(repos_partition.tolist(), actions_output_path)

    # Parse response to determine which projects have at least 1 workflow
    query_responses = [
        f"data/actions_projects_gte5_members_split{i}.json" for i in range(NUM_WORKFLOW_PARTITIONS)]
    project_workflows_dict = combine_partitioned_workflow_filenames(
        query_responses)

    # Extract repo_ids for projects that contained at least 1 workflow
    remaining_repo_ids = project_workflows_dict.keys()
    projects_df = projects_df[projects_df.repo_id.isin(remaining_repo_ids)]
    print(
        f"There are {len(remaining_repo_ids)} projects containing GitHub Actions workflow(s)")

    # Write the remaining projects and their found workflows to output files
    write_df_to_csv_file(projects_df, output_projects_path)
    write_dict_to_json_file(project_workflows_dict, output_workflows_path)

    print(f"[!] Wrote filtered projects file to {output_projects_path}")
    print(f"[!] Wrote workflow filenames file to {output_workflows_path}")
    print("[!] Done filtering out projects that don't have any GitHub Actions workflow files")
    print(f"[!] # remaining projects: ${projects_df.shape[0]}")


def filter_by_ci_workflow_files(input_projects_path: str, output_projects_path: str,
                                input_workflows_path: str, output_workflows_path: str,
                                yaml_workflows_json_prefix: str):
    print("[!] Filtering out projects lacking any workflow file that use GitHub Actions for CI")

    # Load the current set of projects to be filtered
    print("Loading projects...")
    projects_df = read_df_from_csv_file(input_projects_path, PROJECT_COLS)
    print(f"Loaded {projects_df.shape[0]} projects")

    # Load the current set of workflow filenames associated to the projects
    project_workflows_dict = read_dict_from_json_file(input_workflows_path)

    # Combine the projects and workflow info into objects for the GraphQL query
    get_workflow_files_partitioned(
        projects_df,
        project_workflows_dict,
        NUM_YAML_PARTITIONS,
        yaml_workflows_json_prefix,
        f"{yaml_workflows_json_prefix}.json"
    )

    # TODO: Check the contents of each workflow to determine if it actually uses CI
    print('[!] Done')


if __name__ == "__main__":
    projects_gte5_members_path = 'data/projects_gte5_members.csv'
    projects_gte5_members_using_actions_path = 'data/projects_gte5_members_using_actions.csv'
    projects_gte5_members_using_actions_ci_path = 'data/projects_gte5_members_using_action_ci.csv'

    workflows_projects_gte5_members_path = 'data/workflows_projects_gte5_members.json'
    ci_workflows_projects_gte5_members_path = 'data/ci_workflows_projects_gte5_members.json'

    yaml_workflows_projects_gte5_members_json_prefix = 'data/yaml_workflows_projects_gte5_members'

    # Execute filtering stages (must be done in order, due to partitioning in first pass)
    filter_by_member_count(projects_gte5_members_path)
    filter_by_workflow_files(
        projects_gte5_members_path,
        projects_gte5_members_using_actions_path,
        workflows_projects_gte5_members_path
    )
    filter_by_ci_workflow_files(
        projects_gte5_members_using_actions_path,
        projects_gte5_members_using_actions_ci_path,
        workflows_projects_gte5_members_path,
        ci_workflows_projects_gte5_members_path,
        yaml_workflows_projects_gte5_members_json_prefix
    )
