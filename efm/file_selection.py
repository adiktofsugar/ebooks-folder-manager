import logging
import os
import re
import glob
from pathlib import Path

logger = logging.getLogger(__name__)


def matches_filter(filepath: Path, filter: str, use_regex_first: bool = False):
    is_negative = filter.startswith("!") or filter.startswith("-")
    if is_negative:
        filter = filter[1:]
    
    # Always try substring match first
    does_match = filter in str(filepath)
    
    # If no substring match, try other patterns
    if not does_match:
        if use_regex_first:
            # Try regex first, then glob
            try:
                regex = re.compile(filter)
                does_match = bool(regex.search(str(filepath)))
            except re.PatternError:
                # If regex fails and has glob magic, try glob
                if glob.has_magic(filter):
                    does_match = filepath.match(filter)
        else:
            if glob.has_magic(filter):
                does_match = filepath.match(filter)
            if not does_match:
                try:
                    regex = re.compile(filter)
                    does_match = bool(regex.search(str(filepath)))
                except re.PatternError:
                    pass
    
    if is_negative:
        does_match = not does_match
    return does_match


"""
get files from dirpath matching include / exclude filters
- by default, gets all files from dirpath
- if filters is set, the filepath is further filtered in order
- a filter is negative if preceded with ! or -

For example, a filters list of ["!*.js", "dogs"] would, for each file, remove if
    *.js matches, and then ensure it includes "dogs"
"""


def get_files_from_dirpath(dirpath: Path, filters: list[str] | None, use_regex_first: bool = False) -> list[Path]:
    all_files: list[Path] = []
    for root, dirs, files in os.walk(dirpath):
        for file in files:
            filepath = (Path(root) / file).resolve()
            does_match = (
                all([matches_filter(filepath, m, use_regex_first) for m in filters]) if filters else True
            )
            if does_match:
                all_files.append(filepath)
    return all_files
