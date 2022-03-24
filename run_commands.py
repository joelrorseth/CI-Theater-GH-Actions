import re
from typing import List

JS_BUILD_REGEX = ".*(^|\s|\/)(npm\s+(install|ci|test|build)|npm\s+run\s+(build|test|ci))($|\s)"
GRADLE_BUILD_REGEX = ".*(^|\s|\/)gradlew?((?=\s).*\s)(build|test)($|\s)"
MAVEN_BUILD_REGEX = ".*(^|\s|\/)mvn((?=\s).*\s)(install|package|compile|test|verify)($|\s)"
MAKE_BUILD_REGEX = ".*(^|\s|\/)c?make($|\s)"
JAVAC_BUILD_REGEX = ".*(^|\s|\/)javac($|\s)"
RUBY_BUILD_REGEX = ".*(^|\s|\/)rake($|\s)|.*(^|\s|\/)bundle((?=\s).*\s)(install|exec)($|\s)"
PYTHON_BUILD_REGEX = ".*(^|\s|\/)(python(2|3)?|pip\s+install|pytest)($|\s)"
ALL_BUILD_REGEX = [
    JS_BUILD_REGEX,
    GRADLE_BUILD_REGEX,
    MAVEN_BUILD_REGEX,
    MAKE_BUILD_REGEX,
    JAVAC_BUILD_REGEX,
    RUBY_BUILD_REGEX,
    PYTHON_BUILD_REGEX
]


def match_cmd_regex(cmd_regex: str, test_cmd: str) -> bool:
    """Return `True` if the given command matches the given regex, and `False` otherwise."""
    return re.search(cmd_regex, test_cmd) is not None


def match_any_cmd_regex(all_regex: List[str], test_cmd: str) -> bool:
    """Return `True` if the given command matches any of the given regex, and `False` otherwise."""
    return any(match_cmd_regex(r, test_cmd) for r in all_regex)


def match_any_build_cmd_regex(test_cmd: str) -> bool:
    """Return `True` if the given command matches any of the build regex, and `False` otherwise."""
    return match_any_cmd_regex(ALL_BUILD_REGEX, test_cmd)
