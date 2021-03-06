import math

DATA_FOLDER = 'data'
RESULTS_FOLDER = 'results'
NUM_MEMBER_PARTITIONS = 10
NUM_WORKFLOW_PARTITIONS = 1500
NUM_YAML_PARTITIONS = 100
NUM_PARTITIONS_DEFAULT_BRANCH = 60
NUM_WORKFLOW_RUNS = 500
NUM_REQUIRED_WORKFLOW_RUNS = 100
MAX_GITHUB_RESULTS_PER_PAGE = 100
NUM_PAGES = NUM_WORKFLOW_RUNS / MAX_GITHUB_RESULTS_PER_PAGE

MEMBER_COUNT_SIZES = [
    'Very Small', 'Small', 'Medium', 'Large', 'Very Large'
]
MEMBER_COUNT_SIZES_MAP = {
    'Very Small': [2, 2],
    'Small': [3, 4],
    'Medium': [5, 9],
    'Large': [10, 19],
    'Very Large': [20, math.inf]
}
SUPPORTED_LANGUAGES = [
    'Java',
    'JavaScript',
    'TypeScript',
    'Ruby',
    'C',
    'C++',
    'Python'
]
SUPPORTED_LANGUAGE_GROUPS = [
    'Java',
    'JS / TS',
    'Ruby',
    'C / C++',
    'Python'
]
SUPPORTED_LANGUAGE_GROUPS_MAP = {
    'Java': 'Java',
    'JavaScript': 'JS / TS',
    'TypeScript': 'JS / TS',
    'Ruby': 'Ruby',
    'C': 'C / C++',
    'C++': 'C / C++',
    'Python': 'Python'
}
SUPPORTED_LANGUAGE_GROUPS_FILENAME_MAP = {
    'Java': 'java',
    'JS / TS': 'js_ts',
    'Ruby': 'ruby',
    'C / C++': 'c_cpp',
    'Python': 'python'
}
