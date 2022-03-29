# Augment the final project selection with additional required data.
# This script must be run after filter_projects.py has established a final list of projects.
#
# - Get the default branch name of every GitHub project
# - Get workflow run data for all push builds on the default branch of all projects
#

import os
from datetime import datetime
from typing import Any, Dict, List
from coveralls_api_client import get_coveralls_report_for_github_commit
from data_io import read_dict_from_json_file
from github_api_client import get_default_branch_for_repos_partitioned, get_runs_for_workflow
from projects import encode_repo_and_workflow_key, encode_repo_key, load_projects, load_projects_partitioned

# Number of workflow runs to fetch (ie. build history window)
NUM_PARTITIONS_DEFAULT_BRANCH = 60

# Github can retrieve a max of 100 results per page
NUM_WORKFLOW_RUNS = 300

MAX_GITHUB_RESULTS_PER_PAGE = 100
NUM_PAGES = NUM_WORKFLOW_RUNS / MAX_GITHUB_RESULTS_PER_PAGE


def encode_workflow_runs_filename(repo_id: str, workflow_idx_str: str) -> str:
    """
    Encode a filename for a JSON file containing all workflow runs for a given project / workflow.
    Produces a filename of the form `workflow_runs_repo123workflow456.json`, which indicates that
    the file contains workflow runs for workflow 456 in repo 123.
    """
    return f"workflow_runs_{encode_repo_and_workflow_key(repo_id, workflow_idx_str)}.json"


def encode_coveralls_report_filename(repo_id: str, sha: str) -> str:
    """
    Encode a filename for a JSON file containing all workflow runs for a given project / workflow.
    Produces a filename of the form `workflow_runs_repo123workflow456.json`, which indicates that
    the file contains workflow runs for workflow 456 in repo 123.
    """
    return f"coveralls_report_repo{repo_id}sha{sha}.json"


def verify_projects_have_augmented_data(projects: List[Dict[str, str]],
                                        augmented_data_dict: Dict[str, Dict[str, Any]]) -> None:
    """
    Verify that all projects have an associated entry in a dict of augmented data dicts.
    If any project is missing any augmented data, abort program execution.
    """
    num_projects_missing_stuff = 0
    print('Verifying that all projects have required augmented data...')

    # Verify that each project has an entry in all dictionaries containing augmented data
    for project in projects:
        for augmented_data_name, augmented_data in augmented_data_dict.items():
            if project['id'] not in augmented_data:
                print(
                    f"ERROR: Missing {augmented_data_name} for project with ID {project['id']}")
                num_projects_missing_stuff += 1

    # If any project is missing any augmented data, exit
    if num_projects_missing_stuff > 0:
        print('ERROR: One or more projects are missing required augmented data, aborting!')
        exit()


def get_default_branches_for_projects(projects_path: str, default_branches_path_prefix: str) -> None:
    print(f"[!] Retrieving the default branch name for each project")
    partitioned_projects = load_projects_partitioned(
        projects_path, NUM_PARTITIONS_DEFAULT_BRANCH)
    get_default_branch_for_repos_partitioned(
        partitioned_projects, NUM_PARTITIONS_DEFAULT_BRANCH, default_branches_path_prefix)
    print(
        f"[!] Wrote default branch names file to {default_branches_path_prefix}.json")
    print(f"[!] Done retrieving default branch names")


def get_workflow_runs(projects_path: str, workflows_path: str, default_branches_path: str) -> None:
    print(
        f"[!] Retrieving the {NUM_WORKFLOW_RUNS} most recent runs for each project workflow")

    # Load the projects, along with workflow and default branch data
    projects = load_projects(projects_path, False)
    workflows_dict = read_dict_from_json_file(workflows_path)
    default_branches_dict = read_dict_from_json_file(default_branches_path)

    # Verify that workflows and default branches exist for all projects
    verify_projects_have_augmented_data(
        projects, {'workflows': workflows_dict, 'default branch': default_branches_dict})

    # Get workflow runs for all workflows in all projects
    # NOTE: This will take a while, and may likely require restarting due to GitHub API rate limits
    for i, project in enumerate(projects):
        print(f"Getting workflow runs for project {i+1}/{len(projects)}")
        for workflow_idx_str, workflow in workflows_dict[project['id']].items():
            # Get workflow runs for this workflow if we haven't already
            output_filename = f"data/{encode_workflow_runs_filename(project['id'], workflow_idx_str)}"
            if not os.path.isfile(output_filename):
                get_runs_for_workflow(
                    project['owner'],
                    project['name'],
                    default_branches_dict[project['id']],
                    workflow['name'],
                    output_filename,
                    NUM_PAGES,
                    MAX_GITHUB_RESULTS_PER_PAGE
                )

    print('[!] Done retrieving workflow runs')


def get_coveralls_info(projects_path: str, workflows_path: str) -> None:
    print('[!] Retrieving Coveralls code coverage info for each project')
    reports_found = 0

    # Load projects and workflows
    projects = load_projects(projects_path, False)
    workflows_dict = read_dict_from_json_file(workflows_path)
    verify_projects_have_augmented_data(
        projects, {'workflows': workflows_dict})

    # Get Coveralls report for each project
    for i, project in enumerate(projects):
        print(f"Getting Coveralls report for project {i+1}/{len(projects)}")

        # Get SHAs (identifiers) for the head commits of every workflow run
        proj_commits = {}
        for workflow_idx_str, _ in workflows_dict[project['id']].items():
            workflow_runs_filename = f"data/{encode_workflow_runs_filename(project['id'], workflow_idx_str)}"
            if not os.path.isfile(workflow_runs_filename):
                print(
                    f"ERROR: Workflow runs file does not exist at {workflow_runs_filename}, aborting!")
                exit()

            workflow_runs = read_dict_from_json_file(workflow_runs_filename)
            for run in workflow_runs:
                proj_commits[run['created_at']] = run['head_sha']

        # Sort the commit SHAs by workflow run date (get newest commits first)
        ordered_proj_commits = sorted(
            proj_commits.items(),
            key=lambda x: datetime.strptime(x[0], '%Y-%m-%dT%H:%M:%SZ'),
            reverse=True
        )

        # Get the Coveralls report associated with the newest commit
        # If no such report exists, a file will still be created with an empty report
        newest_commit_sha = ordered_proj_commits[0][1]
        if get_coveralls_report_for_github_commit(
            newest_commit_sha,
            f"data/{encode_coveralls_report_filename(project['id'], newest_commit_sha)}"
        ):
            reports_found += 1

    print(
        f"Found Coveralls reports for {reports_found}/{len(projects)} projects")
    print('[!] Done retrieving Coveralls code coverage info')


if __name__ == "__main__":
    projects_final_path = 'data/projects_final.csv'
    ci_workflows_final_path = 'data/ci_workflows_final.json'

    default_branches_path_prefix = 'data/default_branches'
    default_branches_path = f"{default_branches_path_prefix}.json"

    # Get default branch names
    get_default_branches_for_projects(
        projects_final_path, default_branches_path_prefix)

    # Get workflow runs (build history)
    get_workflow_runs(projects_final_path,
                      ci_workflows_final_path, default_branches_path)

    # Get Coveralls info
    get_coveralls_info(projects_final_path, ci_workflows_final_path)
