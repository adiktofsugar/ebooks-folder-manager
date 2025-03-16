import argparse
import glob
import logging
import os
import textwrap
from efm.book import Book
from efm.book_exceptions import BookError
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
        - drm           remove DRM from files (backs up original as .bak)
        - rename        rename files based on metadata
        - print         print metadata to console
        - pdf           reformat a PDF via k2pdfopt (backs up original as .bak)
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

    for file in files:
        logging.debug(f"Processing {file}")
        if os.path.isdir(file):
            logging.debug(f"{file} is directory")
            all_files.extend(get_files_from_dirpath(file))
        elif os.path.isfile(file):
            logging.debug(f"{file} is file")
            all_files.append(file)
        else:
            expanded = glob.glob(file)
            logging.debug(f"{file} is glob, expanded to {expanded}")
            all_files.extend(expanded)

    for file in all_files:
        if file.endswith(".bak"):
            logging.debug(f"Skipping {file} because it's a backup file.")
            continue
        logging.debug(f"Processing {file} - getting config")
        config = get_closest_config(os.path.dirname(file))
        actions = (
            args.action
            if args.action is not None
            else config.actions
            if config is not None
            else ["print"]
        )
        try:
            Book(file, dry=args.dry).process(actions)
        except BookError as e:
            # Log the error but continue processing other files
            logging.error(str(e))


def get_files_from_dirpath(dirpath: str) -> list[str]:
    all_files: list[str] = []
    for root, dirs, files in os.walk(dirpath):
        for file in files:
            all_files.append(os.path.join(root, file))
    return all_files


if __name__ == "__main__":
    main()
