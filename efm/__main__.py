import argparse
import logging
import os
import re
import sys
from pathlib import Path

import yaml
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
)

from efm.batch import BatchSummary, Duplicated, Failed, Success

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "DeDRM_tools"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "kfxlib"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "adl"))

from efm.config import Config, get_config
from efm.edit_server import start_edit_server
from efm.transaction import (
    Transaction,
    TransactionSuccess,
    TransactionError,
)
from efm.tasks import TasksFile, process_task, TaskSuccess, TaskError


logger = logging.getLogger(__name__)


def main():
    argparser = argparse.ArgumentParser(
        add_help=True,
        usage="""
      Generate site from ebook files in a directory, with optional regex filter.
      
      Usage:
        efm [options] <directory> [regex_filter]

      Examples:
        efm my-site                     # Process all books in my-site directory
        efm my-site problem.+epub       # Only process books matching the given regex

      ### Config files
      are resolved relative to each file, and must be in a file named "efm.toml", "efm.yaml", "efm.yml", or "efm.json".
      
      can have the following keys:
        - output_dir: output directory for the generated site (required if -o not specified)
        - adobe_user: email for adobe account, used to download ASCM
        - adobe_password: password for adobe account, used to download ASCM and to remove adobe DRM
        - adobe_key_files: list of keyfile paths extracted from from digital editions
            used in order to remove adobe DRM
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    argparser.add_argument(
        "-o", "--out", help="specify output directory (overrides config file)"
    )
    argparser.add_argument(
        "--loglevel", choices=["debug", "info", "error"], help="log level"
    )
    argparser.add_argument(
        "-e",
        "--edit",
        action="store_true",
        help="generate site in edit mode, and start a local server to power it",
    )
    argparser.add_argument("directory", help="directory containing ebooks to process")
    argparser.add_argument(
        "regex_filter", nargs="?", help="optional regex pattern to filter files"
    )

    args: argparse.Namespace = argparser.parse_args()
    loglevel = logging.INFO
    if args.loglevel is not None:
        match args.loglevel.lower():
            case "debug":
                loglevel = logging.DEBUG
            case "info":
                loglevel = logging.INFO
            case "error":
                loglevel = logging.ERROR
            case level:
                raise ValueError(f"Unknown log level {level}")

    # Set up console for progress bar
    console = Console()

    # Keep standard logging setup to avoid interfering with transaction logging
    logging.basicConfig(level=loglevel)

    # Validate directory argument
    directory_path = Path(args.directory).resolve()
    if not directory_path.exists():
        logger.error(f"Directory does not exist: {args.directory}")
        return 1
    if not directory_path.is_dir():
        logger.error(f"Argument must be a directory, not a file: {args.directory}")
        return 1

    # Compile regex filter if provided
    regex_filter = None
    if args.regex_filter:
        try:
            regex_filter = re.compile(args.regex_filter)
            logger.debug(f"Using regex filter: {args.regex_filter}")
        except re.error as e:
            logger.error(f"Invalid regex pattern: {args.regex_filter} - {e}")
            return 1

    config = get_config(directory_path)

    output_dirpath = get_output_dirpath(args.out, config)
    if not output_dirpath:
        logger.error(
            "No output directory specified. Use -o option or set output_dir in config file."
        )
        return 1

    edit_api_port = 12000  # choose a port that's unlikely to conflict

    tasks_filepath: Path = directory_path / "tasks.jsonl"
    tasks_summary = BatchSummary[TaskSuccess | TaskError]([Success, Failed])
    if tasks_filepath.exists():
        logger.info(f"Processing tasks file: {tasks_filepath}")
        tasks_file = TasksFile(tasks_filepath)
        while task := tasks_file.pop_task():
            result = process_task(task)
            if isinstance(result, TaskError):
                tasks_summary.add_result(
                    task.key, Failed, result=result, error=result.error_message
                )
            elif isinstance(result, TaskSuccess):
                tasks_summary.add_result(task.key, Success, result=result)
        tasks_summary.print(console=console)

    # Get all files from the directory
    logger.debug(f"Processing directory: {directory_path}")
    all_files = get_files_from_dirpath(directory_path)

    files_to_process = []
    for file_path in all_files:
        if str(file_path).endswith(".bak"):
            logger.debug(f"Skipping {file_path} because it's a backup file.")
            continue
        if file_path.name in ["efm.toml", "efm.yaml", "efm.yml", "efm.json"]:
            logger.debug(f"Skipping {file_path} because it's a config file.")
            continue
        if file_path.name == "tasks.jsonl":
            logger.debug(f"Skipping {file_path} because it's a tasks file.")
            continue
        if regex_filter:
            if regex_filter.search(file_path.name):
                files_to_process.append(file_path)
                logger.debug(f"File matches filter: {file_path.name}")
            else:
                logger.debug(f"File excluded by filter: {file_path.name}")
        else:
            files_to_process.append(file_path)

    summary = BatchSummary[TransactionSuccess | TransactionError](
        [Success, Failed, Duplicated]
    )

    # Process files with progress bar
    if files_to_process:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            file_progress = progress.add_task(
                "[green]Processing files...", total=len(files_to_process)
            )

            for original_filepath in files_to_process:
                progress.update(
                    file_progress,
                    description=f"[green]Processing {original_filepath.name}...",
                )
                logger.debug(f"Processing {original_filepath}")
                result = Transaction(
                    original_filepath, Path(output_dirpath), config
                ).perform()
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
                        original_filepath, Failed, result, error=result.error_message
                    )
                progress.update(file_progress, advance=1)

    did_fail = any([r for r in summary.results if r.has_category(Failed)])
    summary.print()

    site_dirpath = Path(output_dirpath)
    site_dirpath.mkdir(parents=True, exist_ok=True)
    db_filepath = site_dirpath / "db.yaml"

    # Create database with meta section
    db_content = {
        "meta": {"site_dirpath": site_dirpath},
        "books": [r.result.to_dict() for r in summary.results],
    }

    if args.edit:
        db_content["meta"]["edit_api_url"] = f"http://localhost:{edit_api_port}"

    # Write the database
    db_filepath.write_text(yaml.dump(db_content))

    ui_dist_dirpath = Path(__file__).parent.parent / "site-ui" / "dist"
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

    # If edit mode is enabled, start the server
    if args.edit:
        return start_edit_server(tasks_filepath, edit_api_port)

    # Return non-zero if there were any failures
    return 1 if did_fail else 0


def get_files_from_dirpath(dirpath: Path) -> list[Path]:
    all_files: list[Path] = []
    for root, dirs, files in os.walk(dirpath):
        for file in files:
            all_files.append((Path(root) / file).resolve())
    return all_files


def get_output_dirpath(arg_out: str | None, config: Config | None) -> Path | None:
    if arg_out:
        return Path(arg_out)
    if config and config.output_dir:
        return Path(config.output_dir)
    return None


if __name__ == "__main__":
    sys.exit(main())
