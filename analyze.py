import numpy as np
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple
from config import MEMBER_COUNT_SIZES, SUPPORTED_LANGUAGE_GROUPS, SUPPORTED_LANGUAGE_GROUPS_FILENAME_MAP, SUPPORTED_LANGUAGE_GROUPS_MAP
from coverage import load_coverage
from data_io import write_series_to_json_file
from github_api_client import convert_str_to_datetime
from plot import plot_broken_builds_boxplots, plot_code_coverage_boxplots, plot_project_member_counts_histogram
from projects import get_member_count_sizes_for_projects, load_full_projects, load_original_project_members, load_projects
from workflows import WorkflowRuns, encode_workflow_runs_path, load_workflow_runs, load_workflows


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

    avg_daily_commits_by_proj = {}
    valid_repo_id_strs = []

    # Iterate through each workflow for each project
    for project in projects:
        repo_id_str = project['id']
        project_commits = {}

        for workflow_idx_str, _ in workflows_dict[repo_id_str].items():
            # Get workflow runs
            workflow_runs_path = encode_workflow_runs_path(
                workflow_runs_prefix, repo_id_str, workflow_idx_str)
            workflow_runs = load_workflow_runs(workflow_runs_path)

            # Across all project workflows, map commit id to commit timestamp
            for run in workflow_runs:
                if not run or run is None or not isinstance(run, dict):
                    print(
                        f"WARNING: Empty run in {workflow_runs_path}, skipping...")
                elif 'head_commit' in run and isinstance(run['head_commit'], dict) and 'timestamp' in run['head_commit'] and 'id' in run['head_commit']:
                    project_commits[run['head_commit']
                                    ['timestamp']] = run['head_commit']['id']
                else:
                    print(
                        f"WARNING: Empty commit in {workflow_runs_path}, skipping...")

        # Get min / max datetime observed across all commits
        commit_datetimes = [convert_str_to_datetime(
            t) for t in project_commits.keys()]
        min_date, max_date = min(commit_datetimes), max(commit_datetimes)

        # We could be missing commits from the oldest / newest observed date, trim these
        max_valid_date = (max_date - timedelta(days=1)).replace(
            hour=23, minute=59, second=59, microsecond=999999)
        min_valid_date = (min_date + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0)

        # As long as 1 full days worth of commits were observed, compute daily averages
        num_proj_commits_by_valid_date = defaultdict(int)
        if (max_valid_date - min_valid_date + timedelta(seconds=1)).days >= 1:
            valid_repo_id_strs.append(repo_id_str)
            for commit_datetime in commit_datetimes:
                if commit_datetime >= min_valid_date and commit_datetime <= max_valid_date:
                    commit_date = str(commit_datetime.date())
                    num_proj_commits_by_valid_date[commit_date] += 1

        # Calculate project average daily commit rate (some days may be ignored)
        avg_daily_commits_by_proj[repo_id_str] = sum(
            num_proj_commits_by_valid_date.values()) / len(num_proj_commits_by_valid_date)

    num_valid_proj = len(valid_repo_id_strs)
    print('Only commits from fully observed dates will be considered')
    print(
        f"{num_valid_proj}/{len(projects)} projects have >= 1 full day of commit history")

    # Calculate average daily commit rate across all projects (some projects may be ignored)
    average_daily_commit_rate = sum(
        avg_daily_commits_by_proj.values()) / len(avg_daily_commits_by_proj)

    # Sort out frequent vs. infrequent projects by comparing against average daily commit rate
    valid_project_is_frequent = {
        repo_id: avg_daily_commits_by_proj[repo_id] >= average_daily_commit_rate
        for repo_id in valid_repo_id_strs
    }
    num_frequent = len([f for f in valid_project_is_frequent.values() if f])
    num_infrequent = len(
        [f for f in valid_project_is_frequent.values() if not f])
    print(f"{num_frequent}/{num_valid_proj} ({(num_frequent/num_valid_proj)*100:.2f}%) projects commit frequently")
    print(f"{num_infrequent}/{num_valid_proj} ({(num_infrequent/num_valid_proj)*100:.2f}%) projects commit infrequently")

    # TODO: Plot # commits vs project size, for each language
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


def analyze_broken_build_duration(projects_path: str, workflows_path: str,
                                  workflow_runs_prefix: str, broken_builds_img_prefix: str) -> None:
    """
    RQ3: How common is allowing the build to stay broken for long periods?
    To answer this RQ, ...
    """

    ConclusionsTimeline = List[Tuple[datetime, Dict[str, Any]]]
    ProjectFailureTimedeltas = Dict[str, List[timedelta]]

    def build_workflow_conclusions(workflow_runs: WorkflowRuns) -> ConclusionsTimeline:
        workflow_conclusions = {}
        for run in workflow_runs:
            if not run or run is None or not isinstance(run, dict):
                print('WARNING: Empty run, skipping...')
                continue

            depth1_fields = ['status', 'created_at',
                             'conclusion', 'head_commit']
            all_fields_exist = all([f in run for f in depth1_fields])
            all_fields_exist = all_fields_exist and isinstance(
                run['head_commit'], dict)
            all_fields_exist = all_fields_exist and 'timestamp' in run['head_commit']
            if all_fields_exist:
                if run['status'] == 'completed':
                    workflow_conclusions[convert_str_to_datetime(run['created_at'])] = {
                        'conclusion': run['conclusion'],
                        'commit_timestamp': convert_str_to_datetime(run['head_commit']['timestamp'])
                    }
            else:
                print('WARNING: Incomplete commit, skipping...')
        return sorted(workflow_conclusions.items(), key=lambda x: x[0], reverse=False)

    def get_workflow_failure_timedeltas(conclusions: ConclusionsTimeline) -> List[timedelta]:
        fail_start_conclusion, prev_conclusion = None, None
        first_success_seen = False
        failure_timedeltas = []

        # Iterate through conclusions (workflow runs) in ascending chronological order
        for _, conclusion_obj in conclusions:
            if conclusion_obj['conclusion'] == 'success':
                first_success_seen = True
                # Observing success means a failure period may now be concluded
                # NOTE: We must be sure that a full failure period has come before
                if fail_start_conclusion is not None and prev_conclusion is not None:
                    fail_start_datetime = fail_start_conclusion['commit_timestamp']
                    fail_end_datetime = prev_conclusion['commit_timestamp']

                    # Add timedelta between failure start / end to results list
                    if fail_start_datetime <= fail_end_datetime:
                        failure_timedeltas.append(
                            fail_end_datetime - fail_start_datetime)
                    else:
                        print(
                            'WARNING: Failure start timestamp > end timestamp, skipping...')

                    fail_start_conclusion = None
            else:
                # Observing failure means a failure period may now be starting
                # NOTE: We must be sure this is the first failure in its true sequence
                if fail_start_conclusion is None and first_success_seen:
                    fail_start_conclusion = conclusion_obj

            prev_conclusion = conclusion_obj
        return failure_timedeltas

    print('[!] Analyzing broken build duration')

    projects = load_projects(projects_path, False)
    workflows_dict = load_workflows(workflows_path)

    failure_timedeltas: ProjectFailureTimedeltas = defaultdict(list)

    # Iterate through each workflow for each project
    for project in projects:
        repo_id_str = project['id']
        project_failure_timedeltas = []

        for workflow_idx_str, _ in workflows_dict[repo_id_str].items():
            # Get workflow runs
            workflow_runs_path = encode_workflow_runs_path(
                workflow_runs_prefix, repo_id_str, workflow_idx_str)
            workflow_runs = load_workflow_runs(workflow_runs_path)

            # Create timeline of workflow run timestamps and their success / failure status
            ordered_workflow_conclusions = build_workflow_conclusions(
                workflow_runs)

            # Get a chronological list of broken build (run failure) timedeltas
            workflow_failure_timedeltas = get_workflow_failure_timedeltas(
                ordered_workflow_conclusions)

            # Aggregate timedeltas for this workflow with those from other workflows
            project_failure_timedeltas.extend(workflow_failure_timedeltas)

        # Add all workflows' failure timedeltas to the project-level failures dict
        failure_timedeltas[repo_id_str] = project_failure_timedeltas

    all_timedeltas = [item for sublist in failure_timedeltas.values()
                      for item in sublist]
    #average_timedelta = sum(all_timedeltas, timedelta(0)) / len(all_timedeltas)

    # The third quartile of the overall duration of broken builds is the acceptable threshold
    failure_thresh = np.quantile(all_timedeltas, 0.75)
    print(
        f"The broken build duration threshold (3rd quartile) is {failure_thresh}")

    # Determine how many projects had at least one build (run) that took longer than threshold
    projects_exceeding_thresh = 0
    for repo_id_str, deltas in failure_timedeltas.items():
        if any([delta > failure_thresh for delta in deltas]):
            projects_exceeding_thresh += 1

    exceed_ratio = f"{projects_exceeding_thresh}/{len(failure_timedeltas)}"
    exceed_perc = f"({(projects_exceeding_thresh/len(failure_timedeltas))*100:.2f}%)"
    print(f"{exceed_ratio} {exceed_perc} projects have >= 1 builds exceeding {failure_thresh}")

    # Produce boxplot for each language group, plotting # days broken per member count size
    member_count_sizes = get_member_count_sizes_for_projects(projects)
    for language_group in SUPPORTED_LANGUAGE_GROUPS:
        data_per_size = {}
        for size in MEMBER_COUNT_SIZES:
            projects_for_lang_size = [
                failure_timedeltas[p['id']]
                for p in projects
                if (
                    SUPPORTED_LANGUAGE_GROUPS_MAP[p['language']] == language_group and
                    member_count_sizes[p['id']] == size
                )
            ]
            timedeltas_hrs_for_lang_size = [
                td.seconds//3600 for proj_tds in projects_for_lang_size for td in proj_tds]
            data_per_size[size] = timedeltas_hrs_for_lang_size

        # Produce boxplot for this language group / member count size combo
        plot_broken_builds_boxplots(
            language_group,
            data_per_size,
            f"{broken_builds_img_prefix}_{SUPPORTED_LANGUAGE_GROUPS_FILENAME_MAP[language_group]}"
        )

    print('[!] Done analyzing broken build duration')
