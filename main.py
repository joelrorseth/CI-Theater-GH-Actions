import math
from filter_projects import filter_forked_projects, filter_projects_by_lang, get_initial_projects

MEMBER_COUNT_BINS = [
    [2, 4],
    [5, 8],
    [9, 15],
    [16, 24],
    [25, math.inf]
]
SUPPORTED_LANGUAGES = [
    'Java',
    'Javascript',
    'Typescript',
    'Ruby',
    'C',
    'C++',
    'Python'
]

DATA_FOLDER = 'data'
PROJECTS_STAGE_0_PATH = f"{DATA_FOLDER}/projects_stage_0.csv"
PROJECTS_STAGE_1_PATH = f"{DATA_FOLDER}/projects_stage_1.csv"
PROJECTS_STAGE_2_PATH = f"{DATA_FOLDER}/projects_stage_2.csv"

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

    # TODO: Sequence all experiment operations
    pass
