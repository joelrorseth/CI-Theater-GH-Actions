from data_io import read_dict_from_json_file
from plot import plot_code_coverage_boxplots, plot_value_counts_histogram
from projects import load_project_members


def analyze_project_member_count(project_membership_count_dist_img_path: str):
    print("[!] Analyzing project member counts")

    # Count the number of members associated to each project
    project_members_df = load_project_members()
    repo_member_counts = project_members_df['repo_id'].value_counts()

    print(f"Members per project mean: {repo_member_counts.mean()}")
    print(f"Members per project median: {repo_member_counts.median()}")
    print(f"Members per project std dev: {repo_member_counts.std()}")

    # Count the number of projects have each distinct membership count
    member_count_counts = repo_member_counts.value_counts()
    plot_value_counts_histogram(
        member_count_counts,
        project_membership_count_dist_img_path
    )

    """
    repos_gte1 = repo_member_counts[repo_member_counts >= 1].shape[0]
    repos_gte2 = repo_member_counts[repo_member_counts >= 2].shape[0]
    repos_gte5 = repo_member_counts[repo_member_counts >= 5].shape[0]
    repos_gte10 = repo_member_counts[repo_member_counts >= 10].shape[0]
    repos_gte25 = repo_member_counts[repo_member_counts >= 25].shape[0]

    print(f"{repos_gte1} repos have >= 1 member")
    print(f"{repos_gte2} repos have >= 2 members")
    print(f"{repos_gte5} repos have >= 5 members")
    print(f"{repos_gte10} repos have >= 10 members")
    print(f"{repos_gte25} repos have >= 25 members")
    """

    print("[!] Done analyzing project member counts")


def analyze_coverage(project_coverage_path: str, coverage_boxplot_img_path: str) -> None:
    """
    RQ2: How common is running a build in a software project with poor test coverage?
    To answer this RQ, we produce a figure containing a boxplot for each programming language,
    where each boxplot illustrates the distribution of code coverage for projects using this
    language.
    """
    coverage_by_lang = read_dict_from_json_file(project_coverage_path)
    plot_code_coverage_boxplots(coverage_by_lang, coverage_boxplot_img_path)


if __name__ == '__main__':
    project_coverage_path = 'data/project_coverage.json'

    project_membership_count_dist_img_path = 'figures/project_membership_count_dist.png'
    coverage_boxplot_img_path = 'figures/coverage_boxplot.png'

    # Produce a boxplot illustrating project test coverage by language
    analyze_coverage(project_coverage_path, coverage_boxplot_img_path)

    # Produce a histogram illustrating the distribution of project member counts
    analyze_project_member_count(project_membership_count_dist_img_path)
