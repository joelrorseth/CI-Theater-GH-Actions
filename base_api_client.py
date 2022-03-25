import time
from json import JSONDecodeError
from typing import Any, Dict, Optional
from requests import get, post, packages
from data_io import OutputFile, write_dict_to_json_file

# Disable certificate validation warnings
packages.urllib3.disable_warnings()

RETRY_COUNT = 10

OptionalAny = Optional[Any]
OptionalParams = Optional[Dict[str, str]]


def get_from_url(url: str, output_filename: OutputFile = None,
                 auth: OptionalAny = None, params: OptionalParams = None,
                 allow_json_decode_error: bool = False) -> Dict[Any, Any]:
    """
    Execute a GET request to a given URL. The response body will be deserialized from JSON into
    a dict, which is written to an output file (if provided), then returned. If the response may
    not be in JSON format (perhaps it is HTML, which means parsing will throw JSONDecodeError),
    set `allow_json_decode_error=True` to return an empty dict, otherwise JSONDecodeError will
    be raised. 
    """
    res = get(url, auth=auth, params=params, verify=False, timeout=30)
    try:
        res_json = res.json()
    except JSONDecodeError as e:
        if allow_json_decode_error:
            res_json = {}
        else:
            raise e

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
