# Filter all GHTorrent GitHub projects, using the following stages:
#
# Pass 1: Remove projects which don't contain GitHub Actions workflow file
# Pass 2: Remove projects with few contributors
# Pass 3: Semi-automatically or manually remove projects that don't really use CI
#

import os
import pandas as pd
from data_io import write_df_csv


NUM_PARTITIONS = 10
GHTORRENT_PATH = os.environ['ghtorrent_path']
project_members_path = f"{GHTORRENT_PATH}project_members.csv"


# Load project_members table
print('Loading project-member associations...')
project_members_df = pd.read_csv(
    project_members_path,
    index_col=False,
    names=['repo_id', 'user_id', 'created_at']
)
print(f"Loaded {project_members_df.shape[0]} project-member associations")

# Remove any potential duplicate memberships
project_members_df.drop_duplicates(subset=['repo_id', 'user_id'], inplace=True)
print(f"There are {project_members_df.shape[0]} unique project-member associations")
print(f"There are {project_members_df['repo_id'].nunique()} unique projects associated to members")
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
            names=['repo_id', 'url', 'owner_id', 'name', 'descriptor', 'language', 'created_at', 'forked_from', 'deleted', 'updated_at', 'dummy']
    )
    print(f"Loaded {projects_df.shape[0]} projects")
    #print(projects_df)

    projects_df = projects_df[projects_df.repo_id.isin(repos_gte5)]
    print(f"Removed projects with < 5 members, there are now {projects_df.shape[0]} projects")

    filtered_projects_path = f"data/projects_gte5_members_split{i}.csv"
    write_df_csv(projects_df, filtered_projects_path)
    print(f"Wrote to {filtered_projects_path}")


print(f"Done filtering projects (into {NUM_PARTITIONS} partitions)")
os.system('cat data/projects_gte5_members_split*.csv > data/projects_gte5_members.csv')
print("Wrote concatenated projects file to data/projects_gte5_members.csv")

