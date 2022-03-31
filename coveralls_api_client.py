import os
from typing import Any, Dict
from base_api_client import get_from_url
from data_io import OutputFile

COVERALLS_BASE_URL = os.environ['coveralls_base_url']


def get_from_coveralls(slug: str, output_filename: OutputFile = None):
    # Coveralls returns HTML for 404 results, so allow JSON decoding error (returns empty dict)
    return get_from_url(
        f"{COVERALLS_BASE_URL}{slug}",
        output_filename,
        allow_json_decode_error=True
    )


def get_coveralls_report_for_github_repo(owner: str, repo: str, page: int = 1,
                                         output_filename: OutputFile = None) -> Dict[str, Any]:
    """
    Get Coveralls code coverage reports for a given GitHub repo. A dict is returned,
    which contains a list of builds in reverse chronological order (ie. newest first). If no
    record of this repo exists in Coveralls, an empty dict is returned. A maximum of 10 builds
    is returned, so use the `page` parameter to page through results chronologically.
    ```
    {
        "page": 1,
        "pages": 41,
        "total": 408,
        "builds": [
            {
                "created_at": "2018-01-30T20:05:10Z",
                "url": null,
                "commit_message": "Release 2.0.0",
                "branch": "main",
                "committer_name": "Bob Smith",
                "committer_email": "bobsmith@gmail.com",
                "commit_sha": "da6fed7e00bb55a127041c1364e145ccccc11111",
                "repo_name": "bobsmith/myproject",
                "badge_url": "https://s3.amazonaws.com/assets.coveralls.io/badges/coveralls_100.svg",
                "coverage_change": 100.0,
                "covered_percent": 100.0
            },
            ...
        ]
    }
    ```
    """
    return get_from_coveralls(
        f"/github/{owner}/{repo}.json?page={page}",
        output_filename
    )


def get_coveralls_report_for_github_commit(github_commit_sha: str,
                                           output_filename: OutputFile = None) -> Dict[str, Any]:
    """
    Get the Coveralls code coverage report for a given GitHub commit SHA. A dict is returned,
    which will be empty if no such report exists. Example return value:
    ```
    {
        "created_at": "2018-01-30T20:05:10Z",
        "url": null,
        "commit_message": "Release 2.0.0",
        "branch": "main",
        "committer_name": "Bob Smith",
        "committer_email": "bobsmith@gmail.com",
        "commit_sha": "da6fed7e00bb55a127041c1364e145ccccc11111",
        "repo_name": "bobsmith/myproject",
        "badge_url": "https://s3.amazonaws.com/assets.coveralls.io/badges/coveralls_100.svg",
        "coverage_change": 100.0,
        "covered_percent": 100.0
    }
    ```
    """
    return get_from_coveralls(
        f"/builds/{github_commit_sha}.json",
        output_filename
    )
