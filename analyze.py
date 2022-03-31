from data_io import read_dict_from_json_file
from plot import plot_code_coverage_boxplots


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

    coverage_boxplot_img_path = 'data/coverage_boxplot.png'

    # Produce a boxplot illustrating project test coverage by language
    analyze_coverage(project_coverage_path, coverage_boxplot_img_path)
