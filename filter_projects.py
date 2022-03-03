# Filter all GHTorrent GitHub projects, using the following stages:
#
# Pass 1: Remove projects which don't contain GitHub Actions workflow file
# Pass 2: Remove projects with few contributors
# Pass 3: Semi-automatically or manually remove projects that don't really use CI
#

import os
import pandas as pd

GHTORRENT_PATH = os.environ['ghtorrent_path']
project_members_path = f"{GHTORRENT_PATH}project_members.csv"


# Load project_members table
project_members_df = pd.read_csv(
        project_members_path,
        names=['repo_id', 'user_id', 'created_at']
)
print(f"There are {project_members_df['repo_id'].nunique()} unique repos")
print(f"There are {project_members_df.shape[0]} member records")

# Remove any potential duplicate memberships
project_members_df.drop_duplicates(subset=['repo_id','user_id'], inplace=True)
print(f"There are {project_members_df.shape[0]} unique member records")

repo_member_counts = project_members_df['repo_id'].value_counts()
print(f"Repo member count mean: {repo_member_counts.mean()}")
print(f"Repo member count median: {repo_member_counts.median()}")
print(f"Repo member count std: {repo_member_counts.std()}")

repos_gte1 = repo_member_counts[repo_member_counts>=1].shape[0]
repos_gte2 = repo_member_counts[repo_member_counts>=2].shape[0]
repos_gte5 = repo_member_counts[repo_member_counts>=5].shape[0]
repos_gte10 = repo_member_counts[repo_member_counts>=10].shape[0]
repos_gte25 = repo_member_counts[repo_member_counts>=25].shape[0]

print(f"{repos_gte1} repos have >= 1 member")
print(f"{repos_gte2} repos have >= 2 members")
print(f"{repos_gte5} repos have >= 5 members")
print(f"{repos_gte10} repos have >= 10 members")
print(f"{repos_gte25} repos have >= 25 members")

