from typing import Any, Dict, Union
from requests import get, post, packages
from data_io import OutputFile, write_res_json

# Disable certificate validation warnings
packages.urllib3.disable_warnings()

OptionalAny = Union[Any, None]


def get_from_url(url: str, auth: OptionalAny, output_filename: OutputFile = None) -> Any:
    res = get(url, auth=auth, verify=False, timeout=30)
    res_json = res.json()
    write_res_json(res_json, output_filename)
    return res_json


def post_to_url(url: str, json: Dict[str, Any], auth: OptionalAny,
                output_filename: OutputFile = None) -> Any:
    res = post(url, json=json, auth=auth)
    res_json = res.json()
    write_res_json(res_json, output_filename)
    return res_json
