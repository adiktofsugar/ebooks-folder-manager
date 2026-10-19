import argparse
import logging
from pathlib import Path

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)

from efm.batch import BatchSummary, Duplicated, Failed, Success
from efm.config import Config, get_config
from efm.database import Db, DbMeta
from efm.file_selection import get_files_from_dirpath
from efm.transaction import (
    Transaction,
    TransactionError,
    TransactionSuccess,
)

logger = logging.getLogger(__name__)


def add_parser(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]"):
    parser = subparsers.add_parser(
        "process",
        help="process a directory of ebooks into an output library",
        description="Process ebook files in a directory into an output library (books + db.yaml).",
        epilog="""
examples:
  efm process my-books                  # Process all books in my-books
  efm process my-books 'problem.+epub'  # Only process books matching the given regex

config files:
  Looked up in <directory> and its parents, named "efm.toml", "efm.yaml",
  "efm.yml", or "efm.json". Child values override parent values.

  keys:
    - output_dir: output directory for the processed library (required if -o not specified)
    - adobe_user: email for adobe account, used to download ACSM
    - adobe_password: password for adobe account, used to download ACSM and to remove adobe DRM
    - adobe_key_files: list of keyfile paths extracted from digital editions,
        used in order to remove adobe DRM
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-o", "--out", help="specify output directory (overrides config file)"
    )
    parser.add_argument("directory", help="directory containing ebooks to process")
    parser.add_argument(
        "filters",
        nargs="*",
        help="optional pattern(s) to filter files. can be glob (without **), regex, or substring",
    )
    parser.set_defaults(run=run)


def run(args: argparse.Namespace, console: Console) -> int:
    directory_path = Path(args.directory).resolve()
    if not directory_path.exists():
        logger.error(f"Directory does not exist: {args.directory}")
        return 1
    if not directory_path.is_dir():
        logger.error(f"Argument must be a directory, not a file: {args.directory}")
        return 1

    config = get_config(directory_path)
    logger.info(f"Using config ${config}" if config else "No config found")

    output_dirpath = get_output_dirpath(args.out, config)
    if not output_dirpath:
        logger.error(
            "No output directory specified. Use -o option or set output_dir in config file."
        )
        return 1
    logger.info(f"Writing to {output_dirpath}")

    # Get all files from the directory
    all_filters: list[str] = [
        "!*.bak",
        "!efm.toml",
        "!efm.yaml",
        "!efm.yml",
        "!efm.json",
        *args.filters,
    ]
    logger.debug(f"Getting files from: {directory_path} matching {all_filters}")
    filepaths = get_files_from_dirpath(directory_path, all_filters)

    summary = BatchSummary[TransactionSuccess | TransactionError](
        [Success, Failed, Duplicated]
    )

    # Process files with progress bar
    if filepaths:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            file_progress = progress.add_task(
                "[green]Processing files...", total=len(filepaths)
            )

            for filepath in filepaths:
                progress.update(
                    file_progress,
                    description=f"[green]Processing {filepath.name}...",
                )
                logger.debug(f"Processing {filepath}")
                result = Transaction(filepath, Path(output_dirpath), config).perform()
                if isinstance(result, TransactionSuccess):
                    is_duplicate = result.hash in [
                        r.name for r in summary.results if r.has_category(Success)
                    ]
                    if is_duplicate:
                        summary.add_result(result.hash, Duplicated, result)
                    else:
                        summary.add_result(result.hash, Success, result)
                elif isinstance(result, TransactionError):
                    summary.add_result(
                        str(filepath),
                        Failed,
                        result,
                        error=result.error_message,
                    )
                progress.update(file_progress, advance=1)

    did_fail = any(r.has_category(Failed) for r in summary.results)
    summary.print()

    site_dirpath = Path(output_dirpath)
    site_dirpath.mkdir(parents=True, exist_ok=True)
    db_meta = DbMeta(site_dirpath=site_dirpath)
    db = Db(
        meta=db_meta,
        books=[r.result for r in summary.results if not r.has_category(Duplicated)],
    )
    db.save(site_dirpath / "db.yaml")

    # Return non-zero if there were any failures
    return 1 if did_fail else 0


def get_output_dirpath(arg_out: str | None, config: Config | None) -> Path | None:
    if arg_out:
        return Path(arg_out)
    if config and config.output_dir:
        return Path(config.output_dir)
    return None
