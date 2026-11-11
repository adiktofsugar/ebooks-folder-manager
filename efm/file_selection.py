import glob
import logging
import os
import re
from pathlib import Path

logger = logging.getLogger(__name__)


def matches_filter(path: Path, filter: str, use_regex_first: bool = False):
    is_negative = filter.startswith("!") or filter.startswith("-")
    if is_negative:
        filter = filter[1:]

    # Always try substring match first
    does_match = filter in str(path)

    # If no substring match, try other patterns
    if not does_match:
        if use_regex_first:
            # Try regex first, then glob
            try:
                regex = re.compile(filter)
                does_match = bool(regex.search(str(path)))
            except re.PatternError:
                # If regex fails and has glob magic, try glob
                if glob.has_magic(filter):
                    does_match = path.match(filter)
        else:
            if glob.has_magic(filter):
                does_match = path.match(filter)
            if not does_match:
                try:
                    regex = re.compile(filter)
                    does_match = bool(regex.search(str(path)))
                except re.PatternError:
                    pass

    if is_negative:
        does_match = not does_match
    return does_match


"""
get files from dir matching include / exclude filters
- by default, gets all files from dir
- if filters is set, the file paths are further filtered in order
- a filter is negative if preceded with ! or -

For example, a filters list of ["!*.js", "dogs"] would, for each file, remove if
    *.js matches, and then ensure it includes "dogs"
"""


def get_files_from_dir(
    dir: Path, filters: list[str] | None, use_regex_first: bool = False
) -> list[Path]:
    files: list[Path] = []
    for dirpath, _dirnames, filenames in os.walk(dir):
        for filename in filenames:
            # absolute(), not resolve(): a symlink stays under dir instead of jumping to its target
            file = (Path(dirpath) / filename).absolute()
            does_match = (
                all([matches_filter(file, m, use_regex_first) for m in filters])
                if filters
                else True
            )
            if does_match:
                files.append(file)
    return files
