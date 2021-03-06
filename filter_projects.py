# Filter all GHTorrent GitHub projects, using the following stages:
#
# Pass 1: Remove projects which don't contain GitHub Actions workflow file
# Pass 2: Remove projects with few contributors
# Pass 3: Semi-automatically or manually remove projects that don't really use CI
#

import os
from typing import List
import pandas as pd
from branches import load_default_branches
from config import (
    NUM_MEMBER_PARTITIONS,
    NUM_REQUIRED_WORKFLOW_RUNS,
    NUM_WORKFLOW_PARTITIONS,
    NUM_YAML_PARTITIONS
)
from github_api_client import (
    combine_partitioned_workflow_filenames,
    get_workflow_files_partitioned,
    get_workflows_for_repos
)
from projects import (
    GHTORRENT_PATH,
    NULL_SYMBOL,
    load_full_projects,
    load_original_project_members,
    load_projects,
    load_projects_and_partition,
    save_full_projects_df
)
from workflows import (
    encode_workflow_runs_path,
    get_workflows_using_ci,
    load_workflow_runs,
    load_workflows,
    save_workflows
)


def get_initial_projects(output_projects_path: str):
    print("[!] Building initial set of projects by cross-referencing project members")

    if os.path.isfile(output_projects_path):
        print(f"[!] {output_projects_path} already exists, skipping...")
        return

    # Load project_members and determine project membership count
    project_members_df = load_original_project_members()
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
    project_workflows_dict = load_workflows(input_workflow_filenames_path)

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


def filter_by_default_branch_existence(input_projects_path: str, output_projects_path: str,
                                       default_branches_path: str):
    print("[!] Filtering out projects for which we could not determine the default branch name")

    if os.path.isfile(output_projects_path):
        print(
            f"[!] {output_projects_path} already exists, skipping...")
        return

    # Load full version of unpartitioned input projects
    projects_df = load_full_projects(input_projects_path, quiet=True)
    num_projects_before = projects_df.shape[0]
    default_branches_dict = load_default_branches(default_branches_path)

    # Remove projects that do not have an entry in the default branch dict
    projects_df = projects_df[projects_df.repo_id.isin(
        [int(repo_id) for repo_id in default_branches_dict.keys()])]
    print(
        f"{num_projects_before} projects were reduced to {projects_df.shape[0]}")

    # Write the remaining projects and their found workflows to output files
    save_full_projects_df(projects_df, output_projects_path)
    print("[!] Done filtering out projects with missing default branch name")


def filter_by_workflow_run_history(input_projects_path: str, output_projects_path: str,
                                   input_workflows_path: str, output_workflows_path: str,
                                   workflow_runs_prefix: str):
    print(
        f"[!] Filtering out projects with < {NUM_REQUIRED_WORKFLOW_RUNS} workflow runs")

    if os.path.isfile(output_projects_path) and os.path.isfile(output_workflows_path):
        print(
            f"[!] {output_projects_path} and {output_workflows_path} already exist, skipping...")
        return

    projects = load_projects(input_projects_path, False)
    workflows_dict = load_workflows(input_workflows_path)
    repo_ids_to_keep = []

    # Iterate through each workflow for each project
    for i, project in enumerate(projects):
        if i % 100 == 0:
            print(
                f"Filtering projects by # of workflow runs ({i}/{len(projects)})...")
        workflow_ids_to_remove = []
        repo_id_str = project['id']
        for workflow_idx_str, _ in workflows_dict[repo_id_str].items():
            workflow_runs_path = encode_workflow_runs_path(
                workflow_runs_prefix, repo_id_str, workflow_idx_str)
            workflow_runs = load_workflow_runs(workflow_runs_path)

            # Mark workflow for removal if unsufficient workflow runs exist for it
            if len(workflow_runs) < NUM_REQUIRED_WORKFLOW_RUNS:
                workflow_ids_to_remove.append(workflow_idx_str)

        # Remove workflows that were flagged
        for workflow_id_to_remove in workflow_ids_to_remove:
            workflows_dict[repo_id_str].pop(workflow_id_to_remove)

        # If no workflows remain, remove the project from workflows dict
        if not workflows_dict[repo_id_str]:
            workflows_dict.pop(repo_id_str)
        else:
            repo_ids_to_keep.append(int(repo_id_str))

    # Remove any projects that had 0 workflows left after filtering
    projects_df = load_full_projects(input_projects_path, quiet=True)
    num_projects_before = projects_df.shape[0]
    projects_df = projects_df[projects_df.repo_id.isin(repo_ids_to_keep)]
    print(
        f"{num_projects_before} projects were reduced to {projects_df.shape[0]}")

    # Write the remaining projects and workflows dict to JSON
    # NOTE: Useless workflow runs are not removed from disk
    save_full_projects_df(projects_df, output_projects_path)
    save_workflows(workflows_dict, output_workflows_path)
    print("[!] Done filtering out projects with too few workflow runs")
