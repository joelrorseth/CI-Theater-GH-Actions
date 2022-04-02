from coverage import load_coverage
from data_io import write_series_to_json_file
from plot import plot_code_coverage_boxplots, plot_project_member_counts_histogram
from projects import load_full_projects, load_original_project_members


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


def analyze_coverage(coverage_path: str, coverage_boxplot_img_path: str) -> None:
    """
    RQ2: How common is running a build in a software project with poor test coverage?
    To answer this RQ, we produce a figure containing a boxplot for each programming language,
    where each boxplot illustrates the distribution of code coverage for projects using this
    language.
    """
    coverage_by_lang = load_coverage(coverage_path)
    plot_code_coverage_boxplots(coverage_by_lang, coverage_boxplot_img_path)
