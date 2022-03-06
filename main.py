from coveralls_api_client import get_coveralls_report
from github_api_client import get_user, get_workflow, get_workflow_files_for_repos, get_workflow_runs, get_workflows_for_repos, run_search

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

    # Get workflows present in a collection of repos
    # all_repos = [
    #     {'id': 'repo1', 'owner': 'facebook', 'name': 'watchman'},
    #     {'id': 'repo2', 'owner': 'facebook', 'name': 'SPARTA'},
    #     {'id': 'repo3', 'owner': 'facebook', 'name': 'react'},
    #     {'id': 'repo4', 'owner': 'facebook', 'name': 'react-native'},
    # ]
    # get_workflows_for_repos(all_repos, 'test_responses/repos_workflows.json')
    
    # Get a specific workflow YAML file
    pass
