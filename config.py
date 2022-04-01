import math

DATA_FOLDER = 'data'
NUM_MEMBER_PARTITIONS = 10
NUM_WORKFLOW_PARTITIONS = 1500
NUM_YAML_PARTITIONS = 100

# Number of workflow runs to fetch (ie. build history window)
NUM_PARTITIONS_DEFAULT_BRANCH = 60
# Github can retrieve a max of 100 results per page
NUM_WORKFLOW_RUNS = 500

MAX_GITHUB_RESULTS_PER_PAGE = 100
NUM_PAGES = NUM_WORKFLOW_RUNS / MAX_GITHUB_RESULTS_PER_PAGE

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
