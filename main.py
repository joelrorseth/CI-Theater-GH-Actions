from github_api_client import get_all_workflow_runs, get_runs_for_workflow

if __name__ == "__main__":
    # Find GitHub projects with GitHub Actions .yml file
    # run_search('search_page_1.json)

    # Get Github Actions CI-enabled repos

    # Get workflow object
    #get_workflow("Rookfighter", "threadpool-cpp", "cmake.yml", "test_wklfw.json")

    # Get all runs of a given workflow
    #get_runs_for_workflow("Rookfighter", "threadpool-cpp", "cmake.yml", "workflow_runs.json")

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
    # get_runs_for_workflow('facebook', 'mcrouter', 'main', 'build.yml', 'test_responses/mcrouter_build_workflow_runs.json')
    # get_all_workflow_runs('facebook', 'mcrouter', 'main', 'test_responses/mcrouter_all_workflow_runs.json')
    #get_runs_for_workflow('facebook', 'watchman', 'main', 'getdeps_mac.yml', 'test_responses/watchman_build_workflow_runs.json')

    pass
