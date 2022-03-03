import json
from typing import Any, Dict, Union
from requests import get, post, packages

# Disable certificate validation warnings
packages.urllib3.disable_warnings()

OptionalStr = Union[str, None]
OptionalAny = Union[Any, None]


def get_from_url(url: str, auth: OptionalAny, output_filename: OptionalStr = None) -> Any:
    res = get(url, auth=auth, verify=False, timeout=30)
    res_json = res.json()
    write_res_json(res_json, output_filename)
    return res_json


def post_to_url(url: str, json: Dict[str, Any], auth: OptionalAny,
                output_filename: OptionalStr = None) -> Any:
    res = post(url, json=json, auth=auth)
    res_json = res.json()
    write_res_json(res_json, output_filename)
    return res_json


def write_res_json(res_json: Any, output_filename: OptionalStr = None) -> None:
    if output_filename is not None:
        with open(output_filename, 'w') as f:
            json.dump(res_json, f)