import os

GHTORRENT_PATH = os.environ['ghtorrent_path']
PROJECT_MEMBERS_PATH = f"{GHTORRENT_PATH}project_members.csv"
PROJECT_COLS = ['repo_id', 'url', 'owner_id', 'name', 'descriptor',
                'language', 'created_at', 'forked_from', 'deleted', 'updated_at', 'dummy']
PROJECT_MEMBERS_COLS = ['repo_id', 'user_id', 'created_at']
NULL_SYMBOL = "\\N"
