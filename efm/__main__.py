import argparse
import glob
import logging
import os
import shutil
import sys
import tempfile
import textwrap
from efm.action import (
    BaseAction,
    DeDrmAction,
    PrintAction,
    ReformatPdfAction,
    RenameAction,
)
from efm.book import Book
from efm.exceptions import BookError, DeDrmError
from efm.config import get_closest_config


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
        - none          get the metadata, but print nothing (useful for testing to see if we don't throw any errors)
    """),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    argparser.add_argument("spec", nargs="+", help="file, folder, or glob to process")
    argparser.add_argument(
        "-a",
        "--action",
        metavar="action",
        nargs="*",
        choices=["drm", "rename", "print", "pdf", "none"],
        help="action to perform - see below for description",
    )
    argparser.add_argument("--dry", action="store_true", help="dry run")
    argparser.add_argument(
        "--watch", action="store_true", help="watch folder for changes"
    )
    argparser.add_argument(
        "--loglevel", choices=["debug", "info", "error"], help="log level"
    )
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
        loglevel = logging.ERROR

    if args.dry and loglevel < logging.INFO:
        loglevel = logging.INFO

    logging.basicConfig(level=loglevel)

    files = args.spec
    all_files: list[str] = []

    for original_filepath in files:
        logging.debug(f"Processing {original_filepath}")
        if os.path.isdir(original_filepath):
            logging.debug(f"{original_filepath} is directory")
            all_files.extend(get_files_from_dirpath(original_filepath))
        elif os.path.isfile(original_filepath):
            logging.debug(f"{original_filepath} is file")
            all_files.append(original_filepath)
        else:
            expanded = glob.glob(original_filepath)
            logging.debug(f"{original_filepath} is glob, expanded to {expanded}")
            all_files.extend(expanded)

    has_error = False
    for original_filepath in all_files:
        if original_filepath.endswith(".bak"):
            logging.info(f"Skipping {original_filepath} because it's a backup file.")
            continue
        if (
            os.path.basename(original_filepath) == "efm.toml"
            or os.path.basename(original_filepath) == "efm.yaml"
            or os.path.basename(original_filepath) == "efm.yml"
            or os.path.basename(original_filepath) == "efm.json"
        ):
            logging.info(f"Skipping {original_filepath} because it's a config file.")
            continue

        logging.debug(f"Processing {original_filepath} - getting config")
        config = get_closest_config(os.path.dirname(original_filepath))
        try:
            temp_dirpath = tempfile.mkdtemp(prefix=original_filepath)
            action_ids = (
                args.action
                if args.action is not None
                else config.actions
                if config.actions is not None
                else ["print"]
            )
            filename, ext = os.path.splitext(original_filepath)
            current_filepath = original_filepath
            # order matters. drm has to come first for any metadata to work
            for action_id in ["drm", "pdf", "rename", "print"]:
                if action_id in action_ids:
                    action = get_action_from_str(
                        action_id, current_filepath, temp_dirpath, args.dry
                    )
                    after_filepath = action.perform()
                    if after_filepath != current_filepath:
                        old_filepath = os.path.join(
                            temp_dirpath, f"before_{action_id}{ext}"
                        )
                        if current_filepath == original_filepath:
                            # don't delete the original file
                            shutil.copy(current_filepath, old_filepath)
                        else:
                            shutil.move(current_filepath, old_filepath)

                        current_filepath = os.path.join(
                            temp_dirpath, f"{filename}{ext}"
                        )
                        shutil.move(after_filepath, current_filepath)

            if current_filepath != original_filepath:
                logging.info(
                    f"{original_filepath} changed. Backup files are in {temp_dirpath}"
                )
                shutil.copy(current_filepath, original_filepath)

        except Exception as e:
            if isinstance(e, BookError) or isinstance(e, DeDrmError):
                logging.error(str(e))
                has_error = True
            else:
                raise

    if has_error:
        logging.error("Errors occurred during processing. Exiting with status 1.")
        return 1
    return 0


def get_files_from_dirpath(dirpath: str) -> list[str]:
    all_files: list[str] = []
    for root, dirs, files in os.walk(dirpath):
        for file in files:
            all_files.append(os.path.join(root, file))
    return all_files


def get_action_from_str(
    action: str, filepath: str, temp_dirpath: str, dry: bool
) -> BaseAction:
    match action:
        case "drm":
            return DeDrmAction(filepath, temp_dirpath, dry)
        case "rename":
            return RenameAction(filepath, temp_dirpath, dry)
        case "print":
            return PrintAction(filepath, temp_dirpath, dry)
        case "pdf":
            return ReformatPdfAction(filepath, temp_dirpath, dry)
        case _:
            raise ValueError(f"Unknown action {action}")


if __name__ == "__main__":
    sys.exit(main())
