import math
from filter_projects import get_initial_projects

MEMBER_COUNT_BINS = [
    [2, 4],
    [5, 8],
    [9, 15],
    [16, 24],
    [25, math.inf]
]

DATA_FOLDER = 'data'
PROJECTS_STAGE_0_PATH = f"{DATA_FOLDER}/projects_stage_0.csv"

if __name__ == '__main__':
    print('CI Theater (GitHub Actions edition)')
    print(
        f"NOTE: Please delete any stale data in ./{DATA_FOLDER}/ before running")
    print('Starting the experiment...')
    print()

    print('[!] Beginning filtering phase:')
    get_initial_projects(PROJECTS_STAGE_0_PATH)

    # TODO: Sequence all experiment operations
    pass
