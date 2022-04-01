# Filter all GHTorrent GitHub projects, using the following stages:
#
# Pass 1: Remove projects which don't contain GitHub Actions workflow file
# Pass 2: Remove projects with few contributors
# Pass 3: Semi-automatically or manually remove projects that don't really use CI
#

import os
from typing import List
import pandas as pd
from data_io import (
    read_df_from_csv_file,
    read_dict_from_json_file,
    write_df_to_csv_file
)
from github_api_client import (
    combine_partitioned_workflow_filenames,
    get_workflow_files_partitioned,
    get_workflows_for_repos
)
from projects import (
    GHTORRENT_PATH,
    NULL_SYMBOL,
    PROJECT_COLS,
    load_full_projects,
    load_project_members,
    load_projects_and_partition,
    save_full_projects_df
)
from workflows import get_workflows_using_ci, save_workflows

NUM_MEMBER_PARTITIONS = 10
NUM_WORKFLOW_PARTITIONS = 1500
NUM_YAML_PARTITIONS = 60


def get_initial_projects(output_projects_path: str):
    print("[!] Building initial set of projects by cross-referencing project members")

    if os.path.isfile(output_projects_path):
        print(f"[!] {output_projects_path} already exists, skipping...")
        return

    # Load project_members and determine project membership count
    project_members_df = load_project_members()
    repo_member_counts = project_members_df['repo_id'].value_counts()

    # Filter out projects that don't have more than a single member (which is most)
    repos_gte2 = repo_member_counts[repo_member_counts >= 2]
    repos_gte2 = repos_gte2.index.values
    project_members_df = project_members_df[project_members_df.repo_id.isin(
        repos_gte2)]
    num_removed = len(repo_member_counts) - len(repos_gte2)
    print(
        f"Removed {num_removed}/{len(repo_member_counts)} projects that have < 2 members")

    filtered_projects_df = None
    ghtorrent_projects_count = 0

    for i in range(NUM_MEMBER_PARTITIONS):
        # Load current partition of GHTorrent projects
        print(
            f"Loading GHTorrent projects (partition {i+1}/{NUM_MEMBER_PARTITIONS})...")
        projects_path = f"{GHTORRENT_PATH}projects_split{i}.csv"
        projects_df = load_full_projects(projects_path, quiet=True)
        ghtorrent_projects_count += projects_df.shape[0]

        # Remove projects whom do not have adequate project membership
        projects_df = projects_df[projects_df.repo_id.isin(
            project_members_df['repo_id'])]

        # Add to running DataFrame
        if filtered_projects_df is not None:
            filtered_projects_df = pd.concat(
                [filtered_projects_df, projects_df])
        else:
            filtered_projects_df = projects_df

    print(f"[!] {ghtorrent_projects_count} GHTorrent projects were reduced to {filtered_projects_df.shape[0]}")

    # Concatenate all partitioned projects that passed the filter
    save_full_projects_df(filtered_projects_df, output_projects_path)
    print(f"[!] Done building initial set of projects")


def filter_forked_projects(input_projects_path: str, output_projects_path: str):
    print("[!] Filtering out projects that are forked from another project")

    if os.path.isfile(output_projects_path):
        print(f"[!] {output_projects_path} already exists, skipping...")
        return

    # Remove projects whose 'forked_from' attribute is non-empty
    projects_df = load_full_projects(input_projects_path)
    num_projects_before = projects_df.shape[0]
    projects_df = projects_df[projects_df['forked_from'] == NULL_SYMBOL]
    print(
        f"{num_projects_before} projects were reduced to {projects_df.shape[0]}")
    save_full_projects_df(projects_df, output_projects_path)
    print("[!] Done filtering out forked projects")


def filter_projects_by_lang(supported_languages: List[str], input_projects_path: str,
                            output_projects_path: str):
    print("[!] Filtering out projects that use an unsupported language")

    if os.path.isfile(output_projects_path):
        print(f"[!] {output_projects_path} already exists, skipping...")
        return

    projects_df = load_full_projects(input_projects_path)
    num_projects_before = projects_df.shape[0]

    # Keep only those projects whose language is in the set of allowed languages
    # print(set(projects_df['language']))
    projects_df = projects_df[projects_df.language.isin(supported_languages)]

    print(
        f"{num_projects_before} projects were reduced to {projects_df.shape[0]}")
    save_full_projects_df(projects_df, output_projects_path)
    print("[!] Done filtering out projects that use an unsupported language")


# TODO: Refactor / delete
def filter_by_member_count(output_projects_path: str):
    print("[!] Filtering out projects with < 5 members")

    # Load project_members and determine project membership count
    project_members_df = load_project_members()
    repo_member_counts = project_members_df['repo_id'].value_counts()

    # Filter out projects with < 5 members
    repos_gte5 = repo_member_counts[repo_member_counts >= 5]
    repos_gte5 = repos_gte5.index.values
    print(f"There are {len(repos_gte5)} projects with >= 5 members")

    for i in range(NUM_MEMBER_PARTITIONS):
        print(f"Loading projects (partition {i+1}/{NUM_MEMBER_PARTITIONS})...")
        projects_path = f"{GHTORRENT_PATH}projects_split{i}.csv"
        projects_df = read_df_from_csv_file(projects_path, PROJECT_COLS)
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


def filter_by_workflow_files(input_projects_path: str, output_projects_path: str,
                             output_workflows_prefix: str):
    print("[!] Filtering out projects that don't have any GitHub Actions workflow files")

    output_workflows_path = f"{output_workflows_prefix}.json"
    if os.path.isfile(output_projects_path) and os.path.isfile(output_workflows_path):
        print(
            f"[!] {output_projects_path} and {output_workflows_path} already exist, skipping...")
        return

    # Partition the projects, then query for workflows contained in the projects of each partition
    repos_partitions = load_projects_and_partition(
        input_projects_path, NUM_WORKFLOW_PARTITIONS)

    # Get workflows for projects in each partition, if not already cached
    for i in range(0, len(repos_partitions)):
        print(
            f"Finding GitHub Actions workflows in projects (partition {i+1}/{NUM_WORKFLOW_PARTITIONS})...")
        actions_output_path = f"{output_workflows_prefix}_split{i}.json"
        if not os.path.isfile(actions_output_path):
            repos_partition = repos_partitions[i]
            get_workflows_for_repos(
                repos_partition.tolist(), actions_output_path)

    # Parse and combine responses
    query_responses = [
        f"{output_workflows_prefix}_split{i}.json" for i in range(NUM_WORKFLOW_PARTITIONS)]
    project_workflows_dict = combine_partitioned_workflow_filenames(
        query_responses)

    # Load full version of unpartitioned input projects
    projects_df = load_full_projects(input_projects_path, quiet=True)
    num_projects_before = projects_df.shape[0]

    # Extract repo_ids for projects that contained at least 1 workflow
    remaining_repo_ids = [int(repo_id)
                          for repo_id in project_workflows_dict.keys()]
    projects_df = projects_df[projects_df.repo_id.isin(remaining_repo_ids)]
    print(
        f"There are {len(remaining_repo_ids)} projects with at least 1 GitHub Actions workflow")
    print(
        f"{num_projects_before} projects were reduced to {projects_df.shape[0]}")

    # Write the remaining projects and their found workflows to output files
    save_full_projects_df(projects_df, output_projects_path)
    save_workflows(project_workflows_dict, output_workflows_path)
    print("[!] Done filtering out projects that don't have any GitHub Actions workflow files")


def filter_by_using_ci(input_projects_path: str, output_projects_path: str,
                       input_workflow_filenames_path: str, output_workflows_path: str,
                       yaml_workflows_json_prefix: str):
    print("[!] Filtering out projects lacking any workflow file that use GitHub Actions for CI")

    if os.path.isfile(output_projects_path) and os.path.isfile(output_workflows_path):
        print(
            f"[!] {output_projects_path} and {output_workflows_path} already exist, skipping...")
        return

    # Load the current set of projects and workflow filenames
    projects_df = load_full_projects(input_projects_path)
    num_projects_before = projects_df.shape[0]
    project_workflows_dict = read_dict_from_json_file(
        input_workflow_filenames_path)

    # Create augmented dict containing workflow YAML filename and text content
    get_workflow_files_partitioned(
        projects_df,
        project_workflows_dict,
        NUM_YAML_PARTITIONS,
        yaml_workflows_json_prefix
    )

    # Create new filtered workflows dict, omitting workflows that don't actually use CI
    print('Retrieved all workflow YAML contents, checking for CI usage...')
    ci_project_workflows_dict = get_workflows_using_ci(
        f"{yaml_workflows_json_prefix}.json")

    # Create new filtered projects df, omitting projects that no longer have any valid workflows
    remaining_repo_ids = [int(repo_id)
                          for repo_id in ci_project_workflows_dict.keys()]
    projects_df = projects_df[projects_df.repo_id.isin(remaining_repo_ids)]
    print(
        f"There are {len(remaining_repo_ids)} projects using GitHub Actions for CI")

    save_workflows(ci_project_workflows_dict, output_workflows_path)
    save_full_projects_df(projects_df, output_projects_path)

    print(
        f"{num_projects_before} projects were reduced to {projects_df.shape[0]}")
    print("[!] Done filtering out projects that don't use GitHub Actions for CI")


"""
if __name__ == "__main__":
    projects_gte5_members_path = 'data/projects_gte5_members.csv'
    projects_gte5_members_using_actions_path = 'data/projects_gte5_members_using_actions.csv'
    projects_gte5_members_using_actions_ci_path = 'data/projects_gte5_members_using_action_ci.csv'
    projects_unique_gte5_members_using_ci_path = 'data/projects_unique_gte5_members_using_ci.csv'
    projects_final_path = 'data/projects_final.csv'

    workflows_projects_gte5_members_path = 'data/workflows_projects_gte5_members.json'
    ci_workflows_projects_gte5_members_path = 'data/ci_workflows_projects_gte5_members.json'
    ci_workflows_final_path = 'data/ci_workflows_final.json'

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
    filter_forked_projects(
        projects_gte5_members_using_actions_ci_path,
        projects_unique_gte5_members_using_ci_path
    )

    print('[!] All filtering stages are now finished')
    os.system(
        f"cp {projects_unique_gte5_members_using_ci_path} {projects_final_path}")
    os.system(
        f"cp {ci_workflows_projects_gte5_members_path} {ci_workflows_final_path}")
    print(f"[!] Wrote final projects file to {projects_final_path}")
    print(f"[!] Wrote final workflows file to {ci_workflows_final_path}")
    print('[!] Done filtering.')
"""
