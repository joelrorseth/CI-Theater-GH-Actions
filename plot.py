import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from typing import Any, Dict, List
from data_io import OutputFile


def plot_boxplots(data: Dict[str, List[Any]], title: str, xlabel: str, ylabel: str,
                  output_filename: OutputFile) -> None:
    """
    Build a figure containing multiple boxplots. Each boxplot corresponds to an entry in the
    specified `data` dict, meaning each value and key specify a boxplot and corresponding label.
    Example `data` dict:
    ```
    {'Category A': [85,100,35], 'Category B': [10,15,80,90,72]}
    ```
    """

    fig, ax = plt.subplots()
    ax.boxplot(data.values())
    ax.set_title(title)
    ax.set_xticklabels(data.keys())
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)

    # plt.show()
    if output_filename is not None:
        plt.savefig(output_filename)
        print(f"Wrote boxplot to {output_filename}")
        plt.clf()


def plot_code_coverage_boxplots(coverage: Dict[str, List[Any]], output_filename: OutputFile) -> None:
    """
    Build a figure containing multiple boxplots, one for the code coverage of each different
    programming language. Each boxplot corresponds to an entry in the specified `coverage` dict,
    where each key is a programming language, and the associated list of values are the coverage
    values (for projects using that language). Example `coverage` dict:
    ```
    {'Java': [85,100,35], 'Ruby': [10,15,80,90,72]}
    ```
    """
    plot_boxplots(coverage, 'Code Coverage', 'Languages',
                  'Distribution', output_filename)


def plot_broken_builds_boxplots(language: str, data: Dict[str, List[Any]],
                                output_filename: OutputFile) -> None:
    """
    Build a figure containing multiple boxplots, one for each member count size category. Each
    boxplot corresponds to an entry in the specified `data` dict, where each key is a member
    count size category, and the associated list of values are the # hours broken (for various
    workflow runs across projects in that size category). Example `data` dict:
    ```
    {'Very Small': [12,14,2], 'Small': [10,15,8,9,7], ...}
    ```
    """
    plot_boxplots(data, f"{language} Projects", 'Project Member Count Size',
                  '# Hours Broken', output_filename)


def plot_project_member_counts_histogram(value_counts: pd.Series, output_filename: OutputFile) -> None:
    """
    Build a histogram to visualize a pandas value_counts() series.
    """
    ax = value_counts.hist(bins=np.linspace(0, len(value_counts), 101))
    ax.set_title('Distribution of Project Member Counts')
    ax.set_xlabel('# Project Members')
    ax.set_ylabel('Frequency')

    # plt.show()
    if output_filename is not None:
        plt.savefig(output_filename)
        plt.clf()
