import json
from typing import Any, Union

OutputFile = Union[str, None]


def write_res_json(res_json: Any, output_filename: OutputFile = None) -> None:
    if output_filename is not None:
        with open(output_filename, 'w') as f:
            json.dump(res_json, f)


def write_df_csv(df, output_filename: OutputFile = None):
    if output_filename is not None:
        df.to_csv(output_filename)
