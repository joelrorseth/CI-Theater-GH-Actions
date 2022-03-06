from typing import Any, Dict, Union
from requests import get, post, packages
from data_io import OutputFile, write_dict_to_json_file
import time

# Disable certificate validation warnings
packages.urllib3.disable_warnings()

RETRY_COUNT = 3

OptionalAny = Union[Any, None]


def get_from_url(url: str, auth: OptionalAny, output_filename: OutputFile = None) -> Any:
    res = get(url, auth=auth, verify=False, timeout=30)
    res_json = res.json()
    write_dict_to_json_file(res_json, output_filename)
    return res_json


def post_to_url(url: str, json: Dict[str, Any], auth: OptionalAny,
                output_filename: OutputFile = None) -> Any:
    # NOTE: GitHub API calls occassionally fail a few times in a row, attempt a few retries
    counter = 0
    while counter < RETRY_COUNT:
        try:
            res = post(url, json=json, auth=auth)
            res_json = res.json()
            write_dict_to_json_file(res_json, output_filename)
            return res_json
        except:
            print(f"Error occurred, retrying [{counter+1}/3]...")
            time.sleep(1)
            counter += 1
