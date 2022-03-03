from coveralls_api_client import get_coveralls_report
from github_api_client import get_user, get_workflow, get_workflow_runs, run_search

if __name__ == "__main__":
    # Find GitHub projects with GitHub Actions .yml file
    # run_search('search_page_1.json)

    # Get Github Actions CI-enabled repos

    # Get workflow object
    #get_workflow("Rookfighter", "threadpool-cpp", "cmake.yml", "test_wklfw.json")

    # Get all runs of a given workflow
    #get_workflow_runs("Rookfighter", "threadpool-cpp", "cmake.yml", "workflow_runs.json")

    # Get coveralls report
    #get_coveralls_report('voltrb', 'volt', 'coveralls.json')
    pass
