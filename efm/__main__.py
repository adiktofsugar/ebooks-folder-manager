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
from efm.transaction import Transaction, TransactionResult, TransactionSuccess, TransactionError


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

    results: list[TransactionResult] = []

    for original_filepath in all_files:
        if str(original_filepath).endswith(".bak"):
            logger.debug(f"Skipping {original_filepath} because it's a backup file.")
            continue
        if original_filepath.name in ["efm.toml", "efm.yaml", "efm.yml", "efm.json"]:
            logger.debug(f"Skipping {original_filepath} because it's a config file.")
            continue

        logger.debug(f"Processing {original_filepath}")
        result = Transaction(original_filepath, Path(args.out)).perform()
        # Check for duplicates only for successful results
        if isinstance(result, TransactionSuccess):
            if result.filename not in [r.filename for r in results if isinstance(r, TransactionSuccess)]:
                results.append(result)
        else:
            # Always include error results
            results.append(result)

    # Count successes and failures
    successes = [r for r in results if isinstance(r, TransactionSuccess)]
    failures = [r for r in results if isinstance(r, TransactionError)]
    
    # Show summary
    print(f"\nProcessed {len(results)} files:")
    print(f"  ✓ {len(successes)} successful")
    if failures:
        print(f"  ✗ {len(failures)} failed")
        if loglevel == logging.DEBUG:
            print("\nFailed files:")
            for error_result in failures:
                print(f"  - {error_result.messages[0] if error_result.messages else 'Unknown file'}")
    site_dirpath = Path(args.out)
    db_filepath = site_dirpath / "db.yaml"
    # Include both successful and failed results in the database
    db_filepath.write_text(yaml.dump([result.to_dict() for result in results]))

    ui_dist_dirpath = Path(__file__).parent.parent / "ui" / "dist"
    if not ui_dist_dirpath.exists():
        logger.error(
            f"UI distribution directory {ui_dist_dirpath} does not exist. Can not generate site."
        )
        return 1
    for root, dirs, files in os.walk(ui_dist_dirpath):
        for file in files:
            src_file = Path(root) / file
            dest_file = site_dirpath / src_file.relative_to(ui_dist_dirpath)
            if not dest_file.exists():
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                dest_file.write_bytes(src_file.read_bytes())
    # Return non-zero if there were any failures
    return 1 if failures else 0


def get_files_from_dirpath(dirpath: Path) -> list[Path]:
    all_files: list[Path] = []
    for root, dirs, files in os.walk(dirpath):
        for file in files:
            all_files.append(Path(root) / file)
    return all_files


if __name__ == "__main__":
    sys.exit(main())
