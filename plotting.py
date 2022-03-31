import matplotlib.pyplot as plt
from typing import Any, Dict, List
from data_io import OutputFile


def build_boxplots(data: Dict[str, List[Any]], title: str, xlabel: str, ylabel: str,
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


def build_code_coverage_boxplots(coverage: Dict[str, List[Any]], output_filename: OutputFile) -> None:
    """
    Build a figure containing multiple boxplots, one for the code coverage of each different
    programming language. Each boxplot corresponds to an entry in the specified `coverage` dict,
    where each key is a programming language, and the associated list of values are the coverage
    values (for projects using that language). Example `coverage` dict:
    ```
    {'Java': [85,100,35], 'Ruby': [10,15,80,90,72]}
    ```
    """
    build_boxplots(coverage, 'Code Coverage', 'Languages',
                   'Distribution', output_filename)
