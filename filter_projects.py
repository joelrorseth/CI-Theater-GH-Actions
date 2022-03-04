# Filter all GHTorrent GitHub projects, using the following stages:
#
# Pass 1: Remove projects which don't contain GitHub Actions workflow file
# Pass 2: Remove projects with few contributors
# Pass 3: Semi-automatically or manually remove projects that don't really use CI
#

import os
import json
import pandas as pd
from data_io import write_df_csv
from ghtorrent import (
    GHTORRENT_PATH,
    PROJECT_COLS,
    PROJECT_MEMBERS_COLS,
    PROJECT_MEMBERS_PATH
)
from github_api_client import get_workflows_for_repos

NUM_PARTITIONS = 10


def filter_by_member_count(output_projects_path: str):
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
        write_df_csv(projects_df, filtered_projects_path)
        print(f"Wrote to {filtered_projects_path}")

    print(f"Done filtering projects (into {NUM_PARTITIONS} partitions)")
    os.system(
        f"cat data/projects_gte5_members_split*.csv > {output_projects_path}")
    print(f"Wrote concatenated projects file to {output_projects_path}")


def filter_by_workflows(input_projects_path: str, output_projects_path: str):
    projects_df = pd.read_csv(
        input_projects_path,
        index_col=False,
        names=PROJECT_COLS
    )
    repos = [
        {
            'id': f"repo{r['repo_id']}",
            'owner': r['owner_id'],
            'name': r['name']
        }
        for r in projects_df.to_dict(orient="records")
    ]
    get_workflows_for_repos(repos, 'test_responses/repos_workflows.json')
    # TODO: Parse response to determine which have at least 1 workflow


def get_projects_with_workflows():
    eligible_project_ids = set()

    def extract_eligible_projects(query):
        if 'data' in query and query['data'] is not None:
            for repo_id_key, data_val in query['data'].items():
                if data_val is not None:
                    repo_val = query['data'][repo_id_key]
                    if 'object' in repo_val and repo_val['object'] is not None:
                        repo_obj = repo_val['object']
                        if 'entries' in repo_obj and repo_obj['entries'] is not None:
                            repo_entires = repo_obj['entries']
                            if len(repo_entires) > 0:
                                eligible_project_ids.add(
                                    repo_id_key.replace('repo', '')
                                )

    query_responses = ['test_responses/actions_query.json']
    for query_response in query_responses:
        with open(query_response) as json_file:
            query = json.load(json_file)
            extract_eligible_projects(query)

    print(
        f"There are {len(eligible_project_ids)} projects using GitHub Actions")


if __name__ == "__main__":
    projects_gte5_members_path = 'data/projects_gte5_members.csv'
    actions_projects_gte5_members_path = 'data/actions_projects_gte5_members.csv'

    # Execute filtering stages (must be done in order, due to partitioning in first pass)
    # filter_by_member_count(projects_gte5_members_path)
    # filter_by_workflows(projects_gte5_members_path,
    #                    actions_projects_gte5_members_path)
    #get_projects_with_workflows()
