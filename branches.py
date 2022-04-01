from typing import Dict
from data_io import read_dict_from_json_file, write_dict_to_json_file


def load_default_branches(default_branches_path: str) -> Dict[str, str]:
    """
    Load the JSON file containing the default branch for each project, and return this data
    in a dict.
    """
    print(f"Loading default branches from {default_branches_path}...")
    default_branches_dict = read_dict_from_json_file(default_branches_path)
    print(
        f"Loaded default branches for {len(default_branches_dict.keys())} projects")
    return default_branches_dict


def save_default_branches(default_branch_dict: Dict[str, str], output_path: str) -> None:
    write_dict_to_json_file(default_branch_dict, output_path)
    print(
        f"Wrote default branch names for {len(default_branch_dict.keys())} projects to {output_path}")
