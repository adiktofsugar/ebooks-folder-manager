import argparse
import glob
import logging
import os
import sys
import textwrap
from efm.exceptions import BookError, DeDrmError
from efm.transaction import Transaction

logger = logging.getLogger(__name__)


def main():
    argparser = argparse.ArgumentParser(
        add_help=True,
        usage="""
      Run efm on file / folder / glob. 
      If a file, it will perform all actions you specify.
      If a folder, it will walk that folder recursively run on all files that do not end in ".bak".
      If a glob, it will run on all files that match the glob. Folders that match the glob will be ignored.

      Actions are (specified below) are resolved in the following order:
      - set on command line
      - set in config file
      - default to "print"

      Config files are resolved relative to each file, and must be in a file named "efm.toml", "efm.yaml", "efm.yml", or "efm.json".
      Config files can have the following keys:
      - actions: a list of actions to perform
      - adobe_key_file: path to Adobe key file

    """,
        epilog=textwrap.dedent("""
      <action>  is one of:
        - drm           remove DRM from files
        - rename        rename files based on metadata
        - print         print metadata to console
        - pdf           reformat a PDF via k2pdfopt
        - download      download an ACSM file
        - none          get the metadata, but print nothing (useful for testing to see if we don't throw any errors)
    """),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    argparser.add_argument(
        "-a",
        "--action",
        action="append",
        choices=["drm", "rename", "print", "pdf", "download", "none"],
        help="action to perform - see below for description",
    )
    argparser.add_argument("--dry", action="store_true", help="dry run")
    argparser.add_argument(
        "--watch", action="store_true", help="watch folder for changes"
    )
    argparser.add_argument(
        "--loglevel", choices=["debug", "info", "error"], help="log level"
    )
    argparser.add_argument("spec", nargs="+", help="file, folder, or glob to process")

    args = argparser.parse_args()
    loglevel = logging.ERROR
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
    else:
        loglevel = logging.INFO

    if args.dry and loglevel < logging.INFO:
        loglevel = logging.INFO

    logging.basicConfig(level=loglevel)

    files = args.spec
    all_files: list[str] = []

    for original_filepath in files:
        logger.debug(f"Processing {original_filepath}")
        if os.path.isdir(original_filepath):
            logger.debug(f"{original_filepath} is directory")
            all_files.extend(get_files_from_dirpath(original_filepath))
        elif os.path.isfile(original_filepath):
            logger.debug(f"{original_filepath} is file")
            all_files.append(original_filepath)
        else:
            expanded = glob.glob(original_filepath)
            logger.debug(f"{original_filepath} is glob, expanded to {expanded}")
            all_files.extend(expanded)

    has_error = False
    for original_filepath in all_files:
        if original_filepath.endswith(".bak"):
            logger.info(f"Skipping {original_filepath} because it's a backup file.")
            continue
        if (
            os.path.basename(original_filepath) == "efm.toml"
            or os.path.basename(original_filepath) == "efm.yaml"
            or os.path.basename(original_filepath) == "efm.yml"
            or os.path.basename(original_filepath) == "efm.json"
        ):
            logger.info(f"Skipping {original_filepath} because it's a config file.")
            continue

        logger.debug(f"Processing {original_filepath}")
        try:
            Transaction(original_filepath, args.action, args.dry).perform()
        except Exception as e:
            if isinstance(e, BookError) or isinstance(e, DeDrmError):
                logger.error(str(e))
                has_error = True
            else:
                raise

    if has_error:
        logger.error("Errors occurred during processing. Exiting with status 1.")
        return 1
    return 0


def get_files_from_dirpath(dirpath: str) -> list[str]:
    all_files: list[str] = []
    for root, dirs, files in os.walk(dirpath):
        for file in files:
            all_files.append(os.path.join(root, file))
    return all_files


if __name__ == "__main__":
    sys.exit(main())
