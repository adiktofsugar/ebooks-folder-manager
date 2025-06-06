import argparse
import glob
import logging
import os
import sys
import traceback
from pathlib import Path

import yaml

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "DeDRM_tools"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "kfxlib"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "adl"))

from efm.exceptions import BookError
from efm.transaction import Transaction


logger = logging.getLogger(__name__)


def main():
    argparser = argparse.ArgumentParser(
        add_help=True,
        usage="""
      Generate site from ebook files, specified by file, folder, or glob.

      ### Config files
      are resolved relative to each file, and must be in a file named "efm.toml", "efm.yaml", "efm.yml", or "efm.json".
      
      can have the following keys:
        - adobe_key_file: path to Adobe key file
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    argparser.add_argument(
        "-o", "--out", help="specify output directory", default="site"
    )
    argparser.add_argument(
        "--loglevel", choices=["debug", "info", "error"], help="log level"
    )
    argparser.add_argument("spec", nargs="+", help="file, folder, or glob to process")

    args = argparser.parse_args()
    loglevel = logging.INFO
    if args.loglevel:
        match args.loglevel.lower():
            case "debug":
                loglevel = logging.DEBUG
            case "info":
                loglevel = logging.INFO
            case "error":
                loglevel = logging.ERROR
            case _:
                raise ValueError(f"Unknown log level {args.loglevel}")

    logging.basicConfig(level=loglevel)

    files = args.spec
    all_files: list[Path] = []

    for original_filepath in files:
        logger.debug(f"Processing {original_filepath}")
        p = Path(original_filepath)
        if p.is_dir():
            logger.debug(f"{original_filepath} is directory")
            all_files.extend(get_files_from_dirpath(p))
        elif p.is_file():
            logger.debug(f"{original_filepath} is file")
            all_files.append(p)
        else:
            expanded = [Path(f) for f in glob.glob(original_filepath)]
            logger.debug(f"{original_filepath} is glob, expanded to {expanded}")
            all_files.extend(expanded)

    errors = list[tuple[Path, BookError]]()
    metadata_filepaths: set[Path] = set()

    for original_filepath in all_files:
        if str(original_filepath).endswith(".bak"):
            logger.info(f"Skipping {original_filepath} because it's a backup file.")
            continue
        if original_filepath.name in ["efm.toml", "efm.yaml", "efm.yml", "efm.json"]:
            logger.info(f"Skipping {original_filepath} because it's a config file.")
            continue

        logger.debug(f"Processing {original_filepath}")
        try:
            metadata_filepaths.add(
                Transaction(original_filepath, Path(args.out)).perform()
            )
        except Exception as e:
            if isinstance(e, BookError):
                errors.append((original_filepath, e))
            else:
                raise

    if len(errors) > 0:
        logger.error("Errors occurred during processing:")
        for filepath, error in errors:
            logger.error(
                f"> {filepath}:{os.linesep}{''.join([f'  | {line}' for line in traceback.format_exception_only(error)])}"
            )
        return 1
    site_dirpath = Path(args.out)
    metadata_summary_filepath = site_dirpath / "metadata" / "summary.yaml"
    metadata_summary_filepath.write_text(
        yaml.dump(
            dict(
                files=[str(f.relative_to(site_dirpath)) for f in metadata_filepaths],
            )
        )
    )
    return 0


def get_files_from_dirpath(dirpath: Path) -> list[Path]:
    all_files: list[Path] = []
    for root, dirs, files in os.walk(dirpath):
        for file in files:
            all_files.append(Path(root) / file)
    return all_files


if __name__ == "__main__":
    sys.exit(main())
