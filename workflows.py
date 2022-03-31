from typing import Any, Dict, List, Union
from data_io import read_dict_from_json_file, read_dict_from_yaml_str
from run_commands import match_any_build_cmd_regex


def check_workflow_jobs_for_cmd(workflow: Union[Dict[str, Any], List[Any]]) -> bool:
    """
    Traverse the provided portion of a workflow file (ie. DFS), testing all 'run' commands
    for CI usage. Returns `True` if at least one run command matches a CI command regex, and
    `False` otherwise. This function is called recursively, such that any match will bubble-up
    and return `True`.
    """
    if type(workflow) is dict:
        for key, val in workflow.items():
            # If this is a run cmd, and it matches the regex, return True
            if key == 'run' and type(val) is str:
                if match_any_build_cmd_regex(val):
                    return True
            else:
                if check_workflow_jobs_for_cmd(val):
                    return True
    if type(workflow) is list:
        for item in workflow:
            if check_workflow_jobs_for_cmd(item):
                return True

    return False


def check_workflow_for_cmd(workflow: Dict[str, Any]) -> bool:
    """
    Traverse the 'jobs' in a workflow file, testing all 'run' commands for CI usage. Returns
    `True` if at least one run command matches a CI command regex, and `False` otherwise.
    """
    if 'jobs' in workflow and workflow['jobs'] is not None:
        return check_workflow_jobs_for_cmd(workflow['jobs'])

    return False


def get_workflows_using_ci(workflows_filename: str) -> Dict[str, Dict[str, Dict[str, str]]]:
    """
    Given the filename of a JSON file containing project YAML workflows, return the subset of
    workflows that actually use CI. This definition of 'CI' is somewhat arbitrary, and is specific
    to this study. We aim to avoid false positives (ie. returning `True` for a non-CI workflow),
    and would prefer false negatives (ie. returning `False` for a CI workflow).

    Example input workflows file (returned dict will look the same):
    ```
    {
        '123': {
            '0': { "name": "build.yml", "text": "These are my YAML contents" },
            ...
        },
        ...
    }
    ```
    """

    # Read JSON containing all workflows for all projects
    workflows_dict = read_dict_from_json_file(workflows_filename)
    ci_workflows_dict = {}

    # Iterate through each repo, and each workflow for each repo
    for i, (repo_id, workflows) in enumerate(workflows_dict.items()):
        if i % 100 == 0:
            print(
                f"Checking repo workflows for CI usage ({i}/{len(workflows_dict.keys())})...")
        for workflow_id, workflow_obj in workflows.items():
            # If workflow actually uses CI, populate the running dict
            if does_workflow_use_ci(workflow_obj):
                if repo_id not in ci_workflows_dict:
                    ci_workflows_dict[repo_id] = {}
                ci_workflows_dict[repo_id][workflow_id] = workflow_obj

    print(
        f"Only {len(ci_workflows_dict.keys())}/{len(workflows_dict.keys())} projects actually use CI")
    return ci_workflows_dict


def does_workflow_use_ci(workflow_obj: Dict[str, str]) -> bool:
    """
    Return `True` if a GitHub Actions workflow YAML defines at least one CI action, or `False`
    otherwise. This definition of 'CI' is somewhat arbitrary, and is specific to this study. We
    aim to avoid false positives (ie. returning `True` for a non-CI workflow), and would prefer
    false negatives (ie. returning `False` for a CI workflow). The workflow YAML parameter is a
    dict representation of the YAML file.
    https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions.

    Example workflow_obj:
    ```
    { "name": "build.yml", "text": "These are my YAML contents" }
    ```
    """

    def uses_valid_yaml_filename():
        return workflow_obj['name'].endswith('.yml') or workflow_obj['name'].endswith('.yaml')

    def uses_on_push(workflow_yaml):
        # NOTE: Will not use, since this filter will be applied when fetching build data
        # Require that workflow runs 'on push'
        if 'on' in workflow_yaml and workflow_yaml['on'] is not None:
            on_dict_has_push = type(
                workflow_yaml['on']) is dict and 'push' in workflow_yaml['on']
            on_list_has_push = type(
                workflow_yaml['on']) is list and 'push' in workflow_yaml['on']
            if on_dict_has_push or on_list_has_push:
                return True

    if uses_valid_yaml_filename():
        workflow_text = workflow_obj['text']
        workflow_text = workflow_text.replace('\t', ' ')
        workflow_yaml = read_dict_from_yaml_str(workflow_text)

        # If workflow actually uses CI, populate the running dict
        if workflow_yaml is not None:
            return check_workflow_for_cmd(workflow_yaml)

    return False