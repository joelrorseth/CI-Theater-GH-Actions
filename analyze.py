import numpy as np
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple
from coverage import load_coverage
from data_io import write_series_to_json_file
from github_api_client import convert_str_to_datetime
from config import (
    MEMBER_COUNT_SIZES,
    SUPPORTED_LANGUAGE_GROUPS,
    SUPPORTED_LANGUAGE_GROUPS_FILENAME_MAP,
    SUPPORTED_LANGUAGE_GROUPS_MAP
)
from plot import (
    BoxplotterSignature,
    plot_broken_builds_boxplots,
    plot_build_duration_boxplots,
    plot_code_coverage_boxplots,
    plot_daily_commits_boxplots,
    plot_project_member_counts_histogram
)
from projects import (
    Projects,
    get_member_count_sizes_for_projects,
    load_full_projects,
    load_original_project_members,
    load_projects
)
from workflows import (
    WorkflowRuns,
    encode_workflow_runs_path,
    load_workflow_runs,
    load_workflows
)


TimedeltaList = List[timedelta]
TimedeltasByProject = Dict[str, TimedeltaList]


def flatten_list(my_list: List[List[Any]]) -> List[Any]:
    return [item for sublist in my_list for item in sublist]


def print_timedelta_stats(subject: str, timedeltas: TimedeltaList, language: str = 'All') -> None:
    timedeltas_in_secs = [td.total_seconds() for td in timedeltas]
    delta_avg = sum(timedeltas, timedelta(0)) / len(timedeltas)
    delta_quantile_50 = np.quantile(timedeltas, 0.50)
    delta_quantile_75 = np.quantile(timedeltas, 0.75)
    delta_quantile_90 = np.quantile(timedeltas, 0.90)
    delta_quantile_95 = np.quantile(timedeltas, 0.95)
    delta_quantile_99 = np.quantile(timedeltas, 0.99)
    delta_std_dev = np.std(timedeltas_in_secs)
    print(f"{subject} stats for {language} projects ({len(timedeltas)} timedeltas):")
    print(f"\tAverage: {delta_avg}")
    print(f"\tMedian: {delta_quantile_50}")
    print(f"\tMax: {max(timedeltas)}")
    print(f"\tStd Dev: {timedelta(seconds=delta_std_dev)}")
    print(f"\t0.75 Quantile: {delta_quantile_75}")
    print(f"\t0.90 Quantile: {delta_quantile_90}")
    print(f"\t0.95 Quantile: {delta_quantile_95}")
    print(f"\t0.99 Quantile: {delta_quantile_99}")
    print()


def print_timedelta_stats_for_all_langs(subject: str, unencoded_projects: Projects,
                                        timedeltas_by_proj: TimedeltasByProject) -> None:
    # Print stats about all projects in general
    print_timedelta_stats(
        subject,
        flatten_list(timedeltas_by_proj.values()),
        'All'
    )

    # Print stats for each language groups
    for language_group in SUPPORTED_LANGUAGE_GROUPS:
        lang_timedeltas = [
            timedeltas_by_proj[p['id']]
            for p in unencoded_projects
            if SUPPORTED_LANGUAGE_GROUPS_MAP[p['language']] == language_group
        ]
        lang_timedeltas = flatten_list(lang_timedeltas)
        print_timedelta_stats(subject, lang_timedeltas, language_group)


def count_projects_exceeding_thresh(timedeltas_by_proj: TimedeltasByProject,
                                    timedelta_thresh: timedelta) -> None:
    projects_exceeding_thresh = 0
    for _, deltas in timedeltas_by_proj.items():
        if any([delta > timedelta_thresh for delta in deltas]):
            projects_exceeding_thresh += 1

    exceed_ratio = f"{projects_exceeding_thresh}/{len(timedeltas_by_proj)}"
    exceed_perc = f"({(projects_exceeding_thresh/len(timedeltas_by_proj))*100:.2f}%)"
    print(f"{exceed_ratio} {exceed_perc} projects have >= 1 builds exceeding {timedelta_thresh}")


def convert_timedeltas_to_ints(timedelta_list: TimedeltaList,
                               units: str = 'hours') -> List[int]:
    denom = 1
    if units == 'hours':
        denom = 3600
    if units == 'minutes':
        denom = 60
    return [td.seconds//denom for td in timedelta_list]


def build_boxplots_by_size_for_langs(unencoded_projects: Projects,
                                     values_per_proj: Dict[str, List[int]],
                                     boxplotter: BoxplotterSignature,
                                     img_prefix: str) -> None:
    member_count_sizes = get_member_count_sizes_for_projects(
        unencoded_projects)
    for language_group in SUPPORTED_LANGUAGE_GROUPS:
        data_per_size = {}
        for size in MEMBER_COUNT_SIZES:
            projects_for_lang_size = [
                values_per_proj[p['id']]
                for p in unencoded_projects
                if (
                    SUPPORTED_LANGUAGE_GROUPS_MAP[p['language']] == language_group and
                    member_count_sizes[p['id']] == size
                )
            ]
            data_per_size[size] = flatten_list(projects_for_lang_size)

        # Produce boxplot for this language group / member count size combo
        boxplotter(language_group, data_per_size,
                   f"{img_prefix}_{SUPPORTED_LANGUAGE_GROUPS_FILENAME_MAP[language_group]}.png")


def build_timedelta_boxplots_by_size_for_langs(unencoded_projects: Projects,
                                               timedeltas_by_proj: TimedeltasByProject,
                                               boxplotter: BoxplotterSignature,
                                               img_prefix: str,
                                               units: str = 'hours') -> None:
    build_boxplots_by_size_for_langs(
        unencoded_projects,
        {repo_id: convert_timedeltas_to_ints(timedeltas, units)
         for repo_id, timedeltas in timedeltas_by_proj.items()},
        boxplotter,
        img_prefix)


def build_repo_val_boxplots_by_size_for_langs(unencoded_projects: Projects,
                                              value_per_proj: Dict[str, Any],
                                              boxplotter: BoxplotterSignature,
                                              img_prefix: str) -> None:
    build_boxplots_by_size_for_langs(
        unencoded_projects,
        {repo_id: [val] for repo_id, val in value_per_proj.items()},
        boxplotter,
        img_prefix)


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
                             workflow_runs_prefix: str, daily_commits_img_prefix: str) -> None:
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
    avg_daily_commit_rate = sum(
        avg_daily_commits_by_proj.values()) / len(avg_daily_commits_by_proj)
    print(
        f"The frequent commit threshold (avergae daily commit rate) is {avg_daily_commit_rate:.2f}")

    # Sort out frequent vs. infrequent projects by comparing against average daily commit rate
    valid_project_is_frequent = {
        repo_id: avg_daily_commits_by_proj[repo_id] >= avg_daily_commit_rate
        for repo_id in valid_repo_id_strs
    }
    num_frequent = len([f for f in valid_project_is_frequent.values() if f])
    num_infrequent = len(
        [f for f in valid_project_is_frequent.values() if not f])
    print(f"{num_frequent}/{num_valid_proj} ({(num_frequent/num_valid_proj)*100:.2f}%) projects commit frequently")
    print(f"{num_infrequent}/{num_valid_proj} ({(num_infrequent/num_valid_proj)*100:.2f}%) projects commit infrequently")

    # Produce boxplot for each language group, plotting avg # daily commits per member count size
    build_repo_val_boxplots_by_size_for_langs(
        projects,
        avg_daily_commits_by_proj,
        plot_daily_commits_boxplots,
        daily_commits_img_prefix
    )

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

    def get_workflow_failure_timedeltas(conclusions: ConclusionsTimeline) -> TimedeltaList:
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
                    if fail_start_datetime < fail_end_datetime:
                        failure_timedeltas.append(
                            fail_end_datetime - fail_start_datetime)
                    # else:
                    #    print(
                    #        'WARNING: Failure start timestamp >= end timestamp, skipping...')

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

    failure_timedeltas: TimedeltasByProject = {}

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

    # Print timedelta stats
    print_timedelta_stats_for_all_langs(
        'Broken build duration', projects, failure_timedeltas)

    # The third quartile of the overall duration of broken builds is the acceptable threshold
    all_timedeltas = flatten_list(failure_timedeltas.values())
    failure_thresh = np.quantile(all_timedeltas, 0.75)
    print(
        f"The broken build duration threshold (3rd quartile) is {failure_thresh}")

    # Determine how many projects had at least one build (run) that took longer than threshold
    count_projects_exceeding_thresh(failure_timedeltas, failure_thresh)

    # Produce boxplot for each language group, plotting # days broken per member count size
    build_timedelta_boxplots_by_size_for_langs(
        projects,
        failure_timedeltas,
        plot_broken_builds_boxplots,
        broken_builds_img_prefix,
        'hours'
    )

    print('[!] Done analyzing broken build duration')


def analyze_build_duration(projects_path: str, workflows_path: str,
                           workflow_runs_prefix: str, build_duration_img_prefix: str) -> None:
    """
    RQ4: How common are long running builds? In order to provide quick feedback, builds should
    be executed in under 10 minutes.
    To answer this RQ, ...
    """

    def build_workflow_durations(workflow_runs: WorkflowRuns) -> TimedeltaList:
        workflow_durations = []
        for run in workflow_runs:
            if not run or run is None or not isinstance(run, dict):
                print('WARNING: Empty run, skipping...')
                continue

            depth1_fields = ['status', 'created_at', 'updated_at']
            all_fields_exist = all([f in run for f in depth1_fields])
            if all_fields_exist:
                if run['status'] == 'completed':
                    run_start = convert_str_to_datetime(run['created_at'])
                    run_end = convert_str_to_datetime(run['updated_at'])
                    if run_start < run_end:
                        workflow_durations.append(run_end - run_start)
                    # else:
                    #    print('WARNING: Run start time >= end time, skipping...')
            else:
                print('WARNING: Incomplete commit, skipping...')
        return workflow_durations

    print('[!] Analyzing build duration')

    projects = load_projects(projects_path, False)
    workflows_dict = load_workflows(workflows_path)

    duration_thresh_mins = 10
    duration_thresh_timedelta = timedelta(minutes=duration_thresh_mins)
    workflow_durations_by_proj: TimedeltasByProject = {}
    print(
        f"Identifying builds that do not execute in under {duration_thresh_mins} minutes")

    # Iterate through each workflow for each project
    for project in projects:
        repo_id_str = project['id']
        project_workflow_durations = []

        for workflow_idx_str, _ in workflows_dict[repo_id_str].items():
            # Get workflow runs
            workflow_runs_path = encode_workflow_runs_path(
                workflow_runs_prefix, repo_id_str, workflow_idx_str)
            workflow_runs = load_workflow_runs(workflow_runs_path)

            # Get duration of each workflow run, aggregate across all proj workflows
            workflow_durations = build_workflow_durations(workflow_runs)
            project_workflow_durations.extend(workflow_durations)

        workflow_durations_by_proj[repo_id_str] = project_workflow_durations

    # Print timedelta stats
    print_timedelta_stats_for_all_langs(
        'Build duration', projects, workflow_durations_by_proj)

    # Determine how many projects had at least one build (run) that took longer than threshold
    count_projects_exceeding_thresh(
        workflow_durations_by_proj, duration_thresh_timedelta)

    # Produce boxplot for each language group, plotting build duration per member count size
    build_timedelta_boxplots_by_size_for_langs(
        projects,
        workflow_durations_by_proj,
        plot_build_duration_boxplots,
        build_duration_img_prefix,
        'minutes'
    )

    print('[!] Done analyzing build duration')
