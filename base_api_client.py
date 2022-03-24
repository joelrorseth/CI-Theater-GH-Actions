from typing import Any, Dict, Optional
from requests import get, post, packages
from data_io import OutputFile, write_dict_to_json_file
import time

# Disable certificate validation warnings
packages.urllib3.disable_warnings()

RETRY_COUNT = 10

OptionalAny = Optional[Any]
OptionalParams = Optional[Dict[str, str]]


def get_from_url(url: str, output_filename: OutputFile = None,
                 auth: OptionalAny = None, params: OptionalParams = None) -> Any:
    res = get(url, auth=auth, params=params, verify=False, timeout=30)
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
            if res_json is None or not('data' in res_json) or res_json['data'] is None:
                raise ValueError()
            write_dict_to_json_file(res_json, output_filename)
            return res_json
        except:
            print(f"Error occurred, retrying [{counter+1}/{RETRY_COUNT}]...")
            time.sleep(3)
            counter += 1
    print(f"ERROR: Exhausted all {RETRY_COUNT} retries")
