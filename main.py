from augment import get_coveralls_info, get_default_branches_for_projects, get_workflow_runs
from config import DATA_FOLDER, RESULTS_FOLDER, SUPPORTED_LANGUAGES
from filter_projects import (
    filter_by_default_branch_existence,
    filter_by_using_ci,
    filter_by_workflow_files,
    filter_by_workflow_run_history,
    filter_forked_projects,
    filter_projects_by_lang,
    get_initial_projects
)
from analyze import (
    analyze_broken_build_duration,
    analyze_commit_frequency,
    analyze_coverage,
    analyze_project_member_count
)

# These filenamess / paths are declared in order of creation
PROJECTS_STAGE_0_PATH = f"{DATA_FOLDER}/projects_stage_0.csv"
PROJECTS_STAGE_1_PATH = f"{DATA_FOLDER}/projects_stage_1.csv"
PROJECTS_STAGE_2_PATH = f"{DATA_FOLDER}/projects_stage_2.csv"
PROJECTS_STAGE_3_PATH = f"{DATA_FOLDER}/projects_stage_3.csv"
WORKFLOWS_STAGE_3_PREFIX = f"{DATA_FOLDER}/workflows_stage_3"
WORKFLOWS_STAGE_3_PATH = f"{WORKFLOWS_STAGE_3_PREFIX}.json"
PROJECTS_STAGE_4_PATH = f"{DATA_FOLDER}/projects_stage_4.csv"
WORKFLOWS_STAGE_4_PATH = f"{DATA_FOLDER}/workflows_stage_4.json"
WORKFLOW_YAML_STAGE_4_PREFIX = f"{DATA_FOLDER}/workflow_yaml_stage_3"
DEFAULT_BRANCHES_PREFIX = f"{DATA_FOLDER}/default_branches"
DEFAULT_BRANCHES_PATH = f"{DEFAULT_BRANCHES_PREFIX}.json"
PROJECTS_STAGE_5_PATH = f"{DATA_FOLDER}/projects_stage_5.csv"
WORKFLOW_RUNS_PREFIX = f"{DATA_FOLDER}/workflow_runs"
PROJECTS_STAGE_6_PATH = f"{DATA_FOLDER}/projects_stage_6.csv"
WORKFLOWS_STAGE_6_PATH = f"{DATA_FOLDER}/workflows_stage_6.json"
PROJECT_COVERAGE_PREFIX = f"{DATA_FOLDER}/project_coverage"
LANGUAGE_COVERAGE_PATH = f"{DATA_FOLDER}/language_coverage.json"

ORIGINAL_PROJECTS_MEMBER_DIST_IMG_PATH = f"{RESULTS_FOLDER}/original_projects_member_dist.png"
ORIGINAL_PROJECTS_MEMBER_DIST_JSON_PATH = f"{RESULTS_FOLDER}/original_projects_member_dist.json"
FINAL_PROJECTS_MEMBER_DIST_IMG_PATH = f"{RESULTS_FOLDER}/final_projects_member_dist.png"
FINAL_PROJECTS_MEMBER_DIST_JSON_PATH = f"{RESULTS_FOLDER}/final_projects_member_dist.json"
PROJECT_COVERAGE_BY_LANG_IMG_PATH = f"{RESULTS_FOLDER}/project_coverage_by_language.png"


if __name__ == '__main__':
    print('CI Theater (GitHub Actions edition)')
    print(
        f"NOTE: Please delete any stale data in ./{DATA_FOLDER}/ before running")
    print('Starting the experiment...')
    print()

    print('[!] Beginning filtering phase')
    get_initial_projects(PROJECTS_STAGE_0_PATH)
    filter_forked_projects(PROJECTS_STAGE_0_PATH, PROJECTS_STAGE_1_PATH)
    filter_projects_by_lang(SUPPORTED_LANGUAGES,
                            PROJECTS_STAGE_1_PATH, PROJECTS_STAGE_2_PATH)
    filter_by_workflow_files(PROJECTS_STAGE_2_PATH,
                             PROJECTS_STAGE_3_PATH, WORKFLOWS_STAGE_3_PREFIX)
    filter_by_using_ci(PROJECTS_STAGE_3_PATH, PROJECTS_STAGE_4_PATH,
                       WORKFLOWS_STAGE_3_PATH, WORKFLOWS_STAGE_4_PATH,
                       WORKFLOW_YAML_STAGE_4_PREFIX)

    print('[!] Beginning augmentation phase')
    get_default_branches_for_projects(
        PROJECTS_STAGE_4_PATH, DEFAULT_BRANCHES_PREFIX)
    filter_by_default_branch_existence(
        PROJECTS_STAGE_4_PATH, PROJECTS_STAGE_5_PATH, DEFAULT_BRANCHES_PATH)
    get_workflow_runs(PROJECTS_STAGE_5_PATH, WORKFLOWS_STAGE_4_PATH,
                      DEFAULT_BRANCHES_PATH, WORKFLOW_RUNS_PREFIX)
    filter_by_workflow_run_history(PROJECTS_STAGE_5_PATH, PROJECTS_STAGE_6_PATH,
                                   WORKFLOWS_STAGE_4_PATH, WORKFLOWS_STAGE_6_PATH,
                                   WORKFLOW_RUNS_PREFIX)
    get_coveralls_info(PROJECTS_STAGE_6_PATH, WORKFLOWS_STAGE_6_PATH, DEFAULT_BRANCHES_PATH,
                       WORKFLOW_RUNS_PREFIX, PROJECT_COVERAGE_PREFIX, LANGUAGE_COVERAGE_PATH)

    print('[!] Beginning analysis phase')
    analyze_project_member_count(
        PROJECTS_STAGE_0_PATH,
        ORIGINAL_PROJECTS_MEMBER_DIST_IMG_PATH,
        ORIGINAL_PROJECTS_MEMBER_DIST_JSON_PATH
    )
    analyze_project_member_count(
        PROJECTS_STAGE_6_PATH,
        FINAL_PROJECTS_MEMBER_DIST_IMG_PATH,
        FINAL_PROJECTS_MEMBER_DIST_JSON_PATH
    )
    analyze_coverage(LANGUAGE_COVERAGE_PATH, PROJECT_COVERAGE_BY_LANG_IMG_PATH)
    analyze_commit_frequency(PROJECTS_STAGE_6_PATH,
                             WORKFLOWS_STAGE_6_PATH, WORKFLOW_RUNS_PREFIX)
    analyze_broken_build_duration(PROJECTS_STAGE_6_PATH,
                                  WORKFLOWS_STAGE_6_PATH, WORKFLOW_RUNS_PREFIX)

    print('Done')
