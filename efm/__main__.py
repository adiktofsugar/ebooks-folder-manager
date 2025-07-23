import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "DeDRM_tools"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "kfxlib"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "adl"))

import argparse
import logging
from pathlib import Path
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
)

from efm.database import Db, DbMeta
from efm.batch import BatchSummary, Duplicated, Failed, Success
from efm.file_selection import get_files_from_dirpath

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
        efm [options] <directory> [filter][,filter...]

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
        "filters",
        nargs="*",
        help="optional pattern(s) to filter files. can be glob (without **), regex, or substring",
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

    # Set up console for progress bar and logging
    console = Console()

    # Configure rich logging handler with custom format for narrow screens
    from rich.text import Text
    from datetime import datetime
    from typing import override

    class NarrowScreenRichHandler(RichHandler):
        @override
        def render_message(self, record, message):
            """Render message with timestamp/level on first line, message on second."""
            # Format time
            time_format = "[%X]"
            log_time = datetime.fromtimestamp(record.created).strftime(time_format)

            level_text = Text(
                record.levelname, style=f"logging.level.{record.levelname.lower()}"
            )
            time_text = Text(log_time, style="log.time")
            first_line = Text.assemble(level_text, " ", time_text)
            return Text.assemble(first_line, "\n", message)

    rich_handler = NarrowScreenRichHandler(
        console=console,
        rich_tracebacks=True,
        show_time=False,  # We handle time ourselves
        show_level=False,
        show_path=False,
        markup=True,
    )

    logging.basicConfig(level=loglevel, handlers=[rich_handler])

    # Validate directory argument
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
    all_filters: list[str] = [
        "!*.bak",
        "!efm.toml",
        "!efm.yaml",
        "!efm.yml",
        "!efm.json",
        "!tasks.jsonl",
    ]
    if args.filters:
        for f in args.filters:
            all_filters.append(f)
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

    did_fail = any([r for r in summary.results if r.has_category(Failed)])
    summary.print()

    site_dirpath = Path(output_dirpath)
    site_dirpath.mkdir(parents=True, exist_ok=True)
    db_meta = DbMeta(
        site_dirpath=site_dirpath,
        edit_api_url=f"http://localhost:{edit_api_port}" if args.edit else None,
    )
    db = Db(
        meta=db_meta,
        books=[r.result for r in summary.results if not r.has_category(Duplicated)],
    )
    db.save(site_dirpath / "db.yaml")

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


def get_output_dirpath(arg_out: str | None, config: Config | None) -> Path | None:
    if arg_out:
        return Path(arg_out)
    if config and config.output_dir:
        return Path(config.output_dir)
    return None


if __name__ == "__main__":
    sys.exit(main())
