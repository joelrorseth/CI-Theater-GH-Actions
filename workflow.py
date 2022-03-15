from typing import Dict
from data_io import read_dict_from_json_file, read_dict_from_yaml_str


def get_workflows_using_ci(workflows_filename: str) -> Dict[str, Dict[str, Dict[str, str]]]:
    """
    Given the filename pf a JSON file containing project YAML workflows, return the subset of
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
    for repo_id, workflows in workflows_dict.items():
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
    dict representation of the YAML file. For more info about the workflow YAML schema, see the
    [documentation on Github](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions).

    Example workflow_obj:
    ```
    { "name": "build.yml", "text": "These are my YAML contents" }
    ```
    """

    def uses_valid_yaml_filename():
        return workflow_obj['name'].endswith('.yml') or workflow_obj['name'].endswith('.yaml')

    def uses_on_push(workflow_yaml):
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
            return uses_on_push(workflow_yaml)

    return False
