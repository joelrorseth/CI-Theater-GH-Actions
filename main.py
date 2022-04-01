import math
from filter_projects import (
    filter_by_workflow_files,
    filter_forked_projects,
    filter_projects_by_lang,
    get_initial_projects
)

MEMBER_COUNT_BINS = [
    [2, 4],
    [5, 8],
    [9, 15],
    [16, 24],
    [25, math.inf]
]
SUPPORTED_LANGUAGES = [
    'Java',
    'JavaScript',
    'TypeScript',
    'Ruby',
    'C',
    'C++',
    'Python'
]

DATA_FOLDER = 'data'
PROJECTS_STAGE_0_PATH = f"{DATA_FOLDER}/projects_stage_0.csv"
PROJECTS_STAGE_1_PATH = f"{DATA_FOLDER}/projects_stage_1.csv"
PROJECTS_STAGE_2_PATH = f"{DATA_FOLDER}/projects_stage_2.csv"
PROJECTS_STAGE_3_PATH = f"{DATA_FOLDER}/projects_stage_3.csv"
WORKFLOWS_STAGE_3_PREFIX = f"{DATA_FOLDER}/workflows_stage_3"

if __name__ == '__main__':
    print('CI Theater (GitHub Actions edition)')
    print(
        f"NOTE: Please delete any stale data in ./{DATA_FOLDER}/ before running")
    print('Starting the experiment...')
    print()

    print('[!] Beginning filtering phase:')
    get_initial_projects(PROJECTS_STAGE_0_PATH)
    filter_forked_projects(PROJECTS_STAGE_0_PATH, PROJECTS_STAGE_1_PATH)
    filter_projects_by_lang(SUPPORTED_LANGUAGES,
                            PROJECTS_STAGE_1_PATH, PROJECTS_STAGE_2_PATH)
    filter_by_workflow_files(PROJECTS_STAGE_2_PATH,
                             PROJECTS_STAGE_3_PATH, WORKFLOWS_STAGE_3_PREFIX)

    # TODO: Sequence all experiment operations
    pass
