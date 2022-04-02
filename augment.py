# Augment the final project selection with additional required data.
# This script must be run after filter_projects.py has established a final list of projects.
#
# - Get the default branch name of every GitHub project
# - Get workflow run data for all push builds on the default branch of all projects
#

import os
from datetime import datetime, timedelta
from typing import Any, Dict, List
from branches import load_default_branches
from coveralls_api_client import get_latest_coveralls_report_in_date_range
from data_io import read_dict_from_json_file, write_dict_to_json_file
from projects import load_projects, load_projects_and_partition
from workflows import encode_workflow_runs_path, load_workflows
from config import (
    MAX_GITHUB_RESULTS_PER_PAGE,
    NUM_PAGES,
    NUM_PARTITIONS_DEFAULT_BRANCH,
    NUM_WORKFLOW_RUNS
)
from github_api_client import (
    GITHUB_DATE_FORMAT,
    get_default_branch_for_repos_partitioned,
    get_runs_for_workflow
)


def encode_coveralls_report_path(project_coverage_prefix: str, repo_id: str) -> str:
    """
    Encode a path for the Coveralls report corresponding to a given project. Produces a
    filename of the form `coveralls_report_repo123.json`, which indicates that the file contains
    the Coveralls report for repo 123.
    """
    return f"{project_coverage_prefix}_repo{repo_id}.json"


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


def load_projects_workflows_branches(projects_path: str, workflows_path: str, default_branches_path: str):
    """
    Load the projects, along with workflow and default branch data. Verify all augmented data,
    before returning the project, workflow, and default branch dictionaries as a tuple.
    """
    projects = load_projects(projects_path, False)
    workflows_dict = load_workflows(workflows_path)
    default_branches_dict = load_default_branches(default_branches_path)

    # Verify that workflows and default branches exist for all projects
    verify_projects_have_augmented_data(
        projects, {'workflows': workflows_dict, 'default branch': default_branches_dict})

    return projects, workflows_dict, default_branches_dict


def get_default_branches_for_projects(projects_path: str, default_branches_path_prefix: str) -> None:
    print(f"[!] Retrieving the default branch name for each project")

    default_branches_output_path = f"{default_branches_path_prefix}.json"
    if os.path.isfile(default_branches_output_path):
        print(
            f"[!] {default_branches_output_path} already exists, skipping...")
        return

    partitioned_projects = load_projects_and_partition(
        projects_path, NUM_PARTITIONS_DEFAULT_BRANCH)
    get_default_branch_for_repos_partitioned(
        partitioned_projects, NUM_PARTITIONS_DEFAULT_BRANCH, default_branches_path_prefix)
    print(
        f"[!] Wrote default branch names file to {default_branches_output_path}")
    print(f"[!] Done retrieving default branch names")


def get_workflow_runs(projects_path: str, workflows_path: str, default_branches_path: str,
                      workflow_runs_prefix: str) -> None:
    print(
        f"[!] Retrieving the {NUM_WORKFLOW_RUNS} most recent runs for each project workflow")

    projects, workflows_dict, default_branches_dict = load_projects_workflows_branches(
        projects_path, workflows_path, default_branches_path)

    # Get workflow runs for all workflows in all projects
    # NOTE: This will take a while, and may likely require restarting due to GitHub API rate limits
    for i, project in enumerate(projects):
        print(f"Getting workflow runs for project {i+1}/{len(projects)}")
        for workflow_idx_str, workflow in workflows_dict[project['id']].items():
            # Get workflow runs for this workflow if we haven't already
            runs_output_path = encode_workflow_runs_path(
                workflow_runs_prefix, project['id'], workflow_idx_str)
            if not os.path.isfile(runs_output_path):
                get_runs_for_workflow(
                    project['owner'],
                    project['name'],
                    default_branches_dict[project['id']],
                    workflow['name'],
                    runs_output_path,
                    NUM_PAGES,
                    MAX_GITHUB_RESULTS_PER_PAGE
                )

    print('[!] Done retrieving workflow runs (no summarized file was written)')


def get_coveralls_info(projects_path: str, workflows_path: str, default_branches_path: str,
                       workflow_runs_prefix: str, project_coverage_prefix: str,
                       project_coverage_path: str) -> None:
    print('[!] Retrieving Coveralls code coverage info for each project')
    reports_found, reports_found_by_lang = 0, {}

    projects, workflows_dict, default_branches_dict = load_projects_workflows_branches(
        projects_path, workflows_path, default_branches_path)

    # Get Coveralls report for each project
    for i, project in enumerate(projects):
        print(
            f"Getting Coveralls report for project {i+1}/{len(projects)} (# found = {reports_found})")

        # Get SHAs (identifiers) for the head commits of every workflow run
        proj_commits = {}
        for workflow_idx_str, _ in workflows_dict[project['id']].items():
            workflow_runs_path = encode_workflow_runs_path(
                workflow_runs_prefix, project['id'], workflow_idx_str)
            if not os.path.isfile(workflow_runs_path):
                print(
                    f"ERROR: Workflow runs file does not exist at {workflow_runs_path}, aborting!")
                exit()

            workflow_runs = read_dict_from_json_file(workflow_runs_path)
            for run in workflow_runs:
                proj_commits[run['created_at']] = run['head_sha']

        # Sort the commit SHAs by workflow run date (get newest commits first)
        ordered_proj_commits = sorted(
            proj_commits.items(),
            key=lambda x: datetime.strptime(x[0], GITHUB_DATE_FORMAT),
            reverse=True
        )

        coveralls_report_filename = encode_coveralls_report_path(
            project_coverage_prefix, project['id'])
        report = {}

        if len(ordered_proj_commits) == 0:
            # No workflow runs existed
            # TODO: Does this project really use CI? We should probably filter these cases out
            write_dict_to_json_file(report, coveralls_report_filename)
        elif not os.path.isfile(coveralls_report_filename):
            # Get the latest Coveralls report created within 7 days before the latest build run
            max_report_date = datetime.strptime(
                ordered_proj_commits[0][0], GITHUB_DATE_FORMAT)
            min_report_date = max_report_date - timedelta(days=7)

            report = get_latest_coveralls_report_in_date_range(
                project['owner'],
                project['name'],
                default_branches_dict[project['id']],
                min_report_date,
                max_report_date,
                output_filename=coveralls_report_filename
            )
        else:
            # Report has already been retrieved, read it from disk
            report = read_dict_from_json_file(coveralls_report_filename)

        # Aggregate coverage by programming language
        if report:
            reports_found += 1
            if project['language'] not in reports_found_by_lang:
                reports_found_by_lang[project['language']] = []
            reports_found_by_lang[project['language']].append(
                report['covered_percent'])

    print(
        f"Found Coveralls reports for {reports_found}/{len(projects)} projects")

    # Write project coverage to JSON file (will omit projects lacking Coveralls report)
    write_dict_to_json_file(reports_found_by_lang, project_coverage_path)
    for lang, coverages in reports_found_by_lang.items():
        print(f"Found {len(coverages)} coverage reports for {lang} projects")

    print('[!] Done retrieving Coveralls code coverage info')
