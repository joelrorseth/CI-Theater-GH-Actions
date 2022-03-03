import os
from base_api_client import OptionalStr, get_from_url

COVERALLS_BASE_URL = os.environ['coveralls_base_url']


def get_from_coveralls(slug: str, output_filename: OptionalStr = None):
    return get_from_url(f"{COVERALLS_BASE_URL}{slug}", None, output_filename)


def get_coveralls_report(owner: str, repo: str, output_filename: OptionalStr = None):
    return get_from_coveralls(
        f"/{owner}/{repo}.json?page=1",
        output_filename
    )
