from coverage import load_coverage
from data_io import write_series_to_json_file
from github_api_client import convert_str_to_datetime
from plot import plot_code_coverage_boxplots, plot_project_member_counts_histogram
from projects import load_full_projects, load_original_project_members, load_projects
from workflows import encode_workflow_runs_path, load_workflow_runs, load_workflows


def analyze_project_member_count(projects_path: str,
                                 project_membership_count_dist_img_path: str,
                                 project_membership_count_dist_path: str):
    print("[!] Analyzing project member counts")

    # Get the intersection of original project members' projects and specified projects
    project_members_df = load_original_project_members()
    projects_df = load_full_projects(projects_path)
    project_members_df = project_members_df[
        project_members_df.repo_id.isin(projects_df.repo_id)
    ]

    # Count the number of members associated to each project
    repo_member_counts = project_members_df['repo_id'].value_counts()
    print(f"Members per project mean: {repo_member_counts.mean()}")
    print(f"Members per project median: {repo_member_counts.median()}")
    print(f"Members per project std dev: {repo_member_counts.std()}")

    # Count the number of projects having each distinct membership count
    member_count_counts = repo_member_counts.value_counts()
    write_series_to_json_file(
        member_count_counts, project_membership_count_dist_path)
    plot_project_member_counts_histogram(
        member_count_counts,
        project_membership_count_dist_img_path
    )

    print("[!] Done analyzing project member counts")


def analyze_commit_frequency(projects_path: str, workflows_path: str,
                             workflow_runs_prefix: str) -> None:
    """
    RQ1: How common is running CI in the master branch but with infrequent commits?
    To answer this RQ, ...
    """
    print('[!] Analyzing project commit frequency')

    projects = load_projects(projects_path, False)
    workflows_dict = load_workflows(workflows_path)
    num_proj_multiple_workflows = 0

    # Iterate through each workflow for each project
    for i, project in enumerate(projects):
        repo_id_str = project['id']
        project_workflows = workflows_dict[project['id']]

        if len(project_workflows) > 1:
            num_proj_multiple_workflows += 1
        if len(project_workflows) == 0:
            print(f"ERROR: There are no workflows for project {repo_id_str}")

        # TODO
        # for workflow_idx_str, _ in workflows_dict[project['id']].items():
        #     # Get workflow runs
        #     workflow_runs_path = encode_workflow_runs_path(
        #         workflow_runs_prefix, repo_id_str, workflow_idx_str)
        #     workflow_runs = load_workflow_runs(workflow_runs_path)
        #     [convert_str_to_datetime(r['created_at']) for r in workflow_runs]

    print(
        f"There are {num_proj_multiple_workflows} projects with multiple workflows")
    print("[!] Done analyzing project commit frequency")


def analyze_coverage(coverage_path: str, coverage_boxplot_img_path: str) -> None:
    """
    RQ2: How common is running a build in a software project with poor test coverage?
    To answer this RQ, we produce a figure containing a boxplot for each programming language,
    where each boxplot illustrates the distribution of code coverage for projects using this
    language.
    """
    print('[!] Analyzing project code coverage by language')
    coverage_by_lang = load_coverage(coverage_path)
    plot_code_coverage_boxplots(coverage_by_lang, coverage_boxplot_img_path)
    print('[!] Done analyzing project code coverage')
