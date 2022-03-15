import json
import yaml
import pandas as pd
from typing import Any, Dict, List, Optional

OutputFile = Optional[str]


def write_dict_to_json_file(res_json: Any, output_filename: OutputFile = None) -> None:
    if output_filename is not None:
        with open(output_filename, 'w') as f:
            json.dump(res_json, f)


def read_dict_from_json_file(json_file_path: str) -> Dict:
    with open(json_file_path) as infile:
        return json.load(infile)


def write_str_to_yaml_file(res_yaml: str, output_filename: OutputFile = None) -> None:
    if output_filename is not None:
        with open(output_filename, 'w') as outfile:
            yaml.dump(res_yaml, outfile)


def read_dict_from_yaml_str(yaml_str: str) -> Optional[Dict[str, Any]]:
    try:
        yaml_dict = yaml.load(yaml_str, Loader=yaml.BaseLoader)
        if type(yaml_dict) is dict:
            return yaml_dict
    except yaml.scanner.ScannerError as e:
        print("ERROR: YAML parsing raised ScannerError.")
    except yaml.parser.ParserError as e:
        print("ERROR: YAML parsing raised ParserError.")


def write_df_to_csv_file(df, output_filename: OutputFile = None,
                         header: Optional[bool] = False,
                         write_index_col: Optional[bool] = False) -> None:
    if output_filename is not None:
        df.to_csv(output_filename, header=header, index=write_index_col)


def read_df_from_csv_file(csv_file_path: str, column_names: Optional[List[str]] = None,
                          expect_index_col: Optional[bool] = False) -> pd.DataFrame:
    return pd.read_csv(
        csv_file_path,
        index_col=expect_index_col,
        names=column_names
    )
