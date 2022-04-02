from typing import Dict, List
from data_io import OutputFile, read_dict_from_json_file, write_dict_to_json_file

LangCoverageDict = Dict[str, List[float]]


def load_coverage(coverage_path: str) -> LangCoverageDict:
    print(f"Loading coverage stats from {coverage_path}...")
    coverage_dict = read_dict_from_json_file(coverage_path)
    print(
        f"Loaded coverage stats for {len(coverage_dict.keys())} language groups")
    return coverage_dict


def save_coverage(coverage_dict: LangCoverageDict, output_path: OutputFile) -> None:
    write_dict_to_json_file(coverage_dict, output_path)
    print(
        f"Wrote coverage stats for {len(coverage_dict.keys())} language groups to {output_path}")
