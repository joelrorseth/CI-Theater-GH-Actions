# Augment the final project selection with additional required data.
# This script must be run after filter_projects.py has established a final list of projects.
#
# - Get the default branch name of every GitHub project
# - Get workflow run data for all push builds on the default branch of all projects
#

from github_api_client import get_default_branch_for_repos_partitioned
from projects import load_projects_partitioned

NUM_PARTITIONS_DEFAULT_BRANCH = 60


def get_default_branches_for_projects(projects_path: str, default_branches_path_prefix: str):
    partitioned_projects = load_projects_partitioned(
        projects_path, NUM_PARTITIONS_DEFAULT_BRANCH)
    get_default_branch_for_repos_partitioned(
        partitioned_projects, NUM_PARTITIONS_DEFAULT_BRANCH, default_branches_path_prefix)


if __name__ == "__main__":
    final_projects_path = 'data/final_projects.csv'
    default_branches_path_prefix = 'data/default_branches'

    # Get default branch names
    get_default_branches_for_projects(
        final_projects_path, default_branches_path_prefix)
