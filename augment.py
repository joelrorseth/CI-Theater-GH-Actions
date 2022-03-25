# Augment the final project selection with additional required data.
# This script must be run after filter_projects.py has established a final list of projects.
#
# - Get the default branch name of every GitHub project
# - Get workflow run data for all push builds on the default branch of all projects
#

import os
from data_io import read_dict_from_json_file
from github_api_client import get_default_branch_for_repos_partitioned, get_runs_for_workflow
from projects import encode_repo_and_workflow_key, load_projects, load_projects_partitioned

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
    num_projects_missing_stuff = 0
    for project in projects:
        if project['id'] not in workflows_dict:
            print(
                f"ERROR: Missing workflows for project with ID {project['id']}")
            num_projects_missing_stuff += 1
        elif project['id'] not in default_branches_dict:
            print(
                f"ERROR: Missing default branch for project with ID {project['id']}")
            num_projects_missing_stuff += 1

    if num_projects_missing_stuff > 0:
        print(
            f"ERROR: {num_projects_missing_stuff} projects are missing data, aborting!")
        return

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
