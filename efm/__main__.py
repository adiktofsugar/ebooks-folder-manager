import argparse
import glob
import logging
import os
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

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "DeDRM_tools"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "kfxlib"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "adl"))

from efm.edit_server import start_edit_server
from efm.transaction import (
    Transaction,
    TransactionResult,
    TransactionSuccess,
    TransactionError,
)
from efm.tasks import TasksFile, process_task, TaskResult, TaskSuccess, TaskError


logger = logging.getLogger(__name__)


def main():
    argparser = argparse.ArgumentParser(
        add_help=True,
        usage="""
      Generate site from ebook files, specified by file, folder, or glob.
      
      Usage:
        efm [options] <file/folder/glob>...

      ### Config files
      are resolved relative to each file, and must be in a file named "efm.toml", "efm.yaml", "efm.yml", or "efm.json".
      
      can have the following keys:
        - adobe_user: email for adobe account, used to download ASCM
        - adobe_password: password for adobe account, used to download ASCM and to remove adobe DRM
        - adobe_key_files: list of keyfile paths extracted from from digital editions
            used in order to remove adobe DRM
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    argparser.add_argument(
        "-o", "--out", help="specify output directory", default="site"
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
    argparser.add_argument("spec", nargs="*", help="file, folder, or glob to process")

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

    # Set up console for progress bar
    console = Console()

    # Keep standard logging setup to avoid interfering with transaction logging
    logging.basicConfig(level=loglevel)

    if not args.spec:
        logger.info("Nothing to do, as no source files specified")
        return 0

    tasks_filepaths: list[Path] = []
    for spec in args.spec:
        p = Path(spec).resolve()
        if p.is_dir():
            tasks_filepaths.append(p / "tasks.jsonl")

    # Fail early if incompatible with edit mode
    if args.edit and len(tasks_filepaths) == 0:
        logger.critical(
            "No task filepath candidates. There must be at least one source directory specified to write the tasks to."
        )
        return 1

    edit_api_port = 8000
    files: list[str] = args.spec
    all_files: list[Path] = []

    task_results: list[TaskResult] = []
    for tasks_filepath in tasks_filepaths:
        if not tasks_filepath.exists():
            continue
        logger.info(f"Found tasks file: {tasks_filepath}")
        tasks_file = TasksFile(tasks_filepath)

        # Get initial task count
        initial_count = tasks_file.get_task_count()
        if initial_count > 0:
            logger.info(f"Processing {initial_count} pending tasks")

        # Process all tasks by popping from the top
        while True:
            task = tasks_file.pop_task()
            if task is None:
                break

            # Process the task
            result = process_task(task)
            task_results.append(result)

            # Log result
            if isinstance(result, TaskSuccess):
                logger.info(f"Task '{result.key}' completed successfully")
                if result.messages:
                    for msg in result.messages:
                        logger.info(f"  - {msg}")
            elif isinstance(result, TaskError):
                logger.error(f"Task '{result.key}' failed: {result.error_message}")
                if result.messages:
                    for msg in result.messages:
                        logger.info(f"  - {msg}")

    for original_filepath in files:
        logger.debug(f"Processing {original_filepath}")
        p = Path(original_filepath).resolve()  # Convert to absolute path
        if p.is_dir():
            logger.debug(f"{original_filepath} is directory")
            all_files.extend(get_files_from_dirpath(p))
        elif p.is_file():
            logger.debug(f"{original_filepath} is file")
            all_files.append(p)
        else:
            expanded = [Path(f).resolve() for f in glob.glob(original_filepath)]
            logger.debug(f"{original_filepath} is glob, expanded to {expanded}")
            all_files.extend(expanded)

    results: list[TransactionResult] = []

    # Filter out files to skip
    files_to_process = []
    for original_filepath in all_files:
        if str(original_filepath).endswith(".bak"):
            logger.debug(f"Skipping {original_filepath} because it's a backup file.")
            continue
        if original_filepath.name in ["efm.toml", "efm.yaml", "efm.yml", "efm.json"]:
            logger.debug(f"Skipping {original_filepath} because it's a config file.")
            continue
        if original_filepath.name == "tasks.jsonl":
            logger.debug(f"Skipping {original_filepath} because it's a tasks file.")
            continue
        files_to_process.append(original_filepath)

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
                result = Transaction(original_filepath, Path(args.out)).perform()
                results.append(result)
                progress.update(file_progress, advance=1)

    # Count successes and failures
    successes = [r for r in results if isinstance(r, TransactionSuccess)]
    failures = [r for r in results if isinstance(r, TransactionError)]

    # Deduplicate successful results by hash
    seen_hashes = {}
    deduplicated_results: list[TransactionResult] = []
    duplicate_count = 0

    for result in results:
        if isinstance(result, TransactionSuccess):
            if result.hash in seen_hashes:
                duplicate_count += 1
                logger.debug(
                    f"Skipping duplicate: {result.original_filepath} has same content as {seen_hashes[result.hash]}"
                )
            else:
                seen_hashes[result.hash] = result.original_filepath
                deduplicated_results.append(result)
        else:
            # Always include error results
            deduplicated_results.append(result)

    # Show summary of tasks if any were processed
    if task_results:
        task_successes = [r for r in task_results if isinstance(r, TaskSuccess)]
        task_failures = [r for r in task_results if isinstance(r, TaskError)]
        print(f"\nProcessed {len(task_results)} tasks:")
        print(f"  ✓ {len(task_successes)} successful")
        if task_failures:
            print(f"  ✗ {len(task_failures)} failed")
            print("\nFailed tasks:")
            for error_result in task_failures:
                print(f"  - {error_result.key}: {error_result.error_message}")

    # Show summary
    print(f"\nProcessed {len(all_files)} files:")
    print(f"  ✓ {len(successes)} successful")
    if duplicate_count > 0:
        print(f"  ≡ {duplicate_count} duplicates")
    if failures:
        print(f"  ✗ {len(failures)} failed")
        print("\nFailed files:")
        for error_result in failures:
            print(f"  - {error_result.original_filepath}: {error_result.error_message}")
    site_dirpath = Path(args.out)
    site_dirpath.mkdir(parents=True, exist_ok=True)
    db_filepath = site_dirpath / "db.yaml"

    # Create database with meta section
    db_content = {
        "meta": {"site_dirpath": site_dirpath},
        "books": [result.to_dict() for result in deduplicated_results],
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
        # the task filepath we send to this function is the one we want it to write to
        # choose the smallest one, since we have to reduce it somehow
        tasks_filepath = tasks_filepaths[0]
        for f in tasks_filepaths:
            if len(f.as_uri()) < len(tasks_filepath.as_uri()):
                tasks_filepath = f
        return start_edit_server(tasks_filepath, edit_api_port)

    # Return non-zero if there were any failures
    return 1 if failures else 0


def get_files_from_dirpath(dirpath: Path) -> list[Path]:
    all_files: list[Path] = []
    for root, dirs, files in os.walk(dirpath):
        for file in files:
            all_files.append((Path(root) / file).resolve())
    return all_files


if __name__ == "__main__":
    sys.exit(main())
