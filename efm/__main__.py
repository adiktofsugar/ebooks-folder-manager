import argparse
import glob
import logging
import os
import sys
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

import yaml

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "DeDRM_tools"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "kfxlib"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "adl"))

from efm.transaction import (
    Transaction,
    TransactionResult,
    TransactionSuccess,
    TransactionError,
)
from efm.tasks import TasksFile, Task, process_task, TaskResult, TaskSuccess, TaskError


logger = logging.getLogger(__name__)


def main():
    argparser = argparse.ArgumentParser(
        add_help=True,
        usage="""
      Generate site from ebook files, specified by file, folder, or glob.
      
      Usage:
        efm [options] <file/folder/glob>...  # Process ebooks
        efm -e <directory>                    # Start edit server

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
    argparser.add_argument(
        "-e", "--edit", action="store_true", help="start a local server with add_task endpoint"
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

    logging.basicConfig(level=loglevel)

    # If edit mode is enabled, start the server
    if args.edit:
        if not args.spec:
            print("Error: You must specify at least one directory when using -e/--edit mode")
            return 1
        
        # Use the first specified directory for tasks.jsonl
        task_directory = Path(args.spec[0]).resolve()
        if not task_directory.is_dir():
            task_directory = task_directory.parent
            
        site_dirpath = Path(args.out)
        return start_edit_server(task_directory, site_dirpath)

    # Normal processing mode requires spec arguments
    if not args.spec:
        argparser.print_help()
        return 1

    files = args.spec
    all_files: list[Path] = []

    # Process tasks.jsonl file if it exists in any of the specified directories
    directories_to_check = set()
    for spec in args.spec:
        p = Path(spec).resolve()
        if p.is_dir():
            directories_to_check.add(p)
        elif p.is_file():
            directories_to_check.add(p.parent)

    task_results: list[TaskResult] = []
    for directory in directories_to_check:
        tasks_filepath = directory / "tasks.jsonl"
        if tasks_filepath.exists():
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
                result = process_task(task, directory)
                task_results.append(result)
                
                # Log result
                if isinstance(result, TaskSuccess):
                    logger.info(f"Task '{result.description}' completed successfully")
                    if result.messages:
                        for msg in result.messages:
                            logger.info(f"  - {msg}")
                else:
                    logger.error(f"Task '{result.description}' failed: {result.error_message}")
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

        logger.debug(f"Processing {original_filepath}")
        result = Transaction(original_filepath, Path(args.out)).perform()
        results.append(result)

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
            if loglevel == logging.DEBUG:
                print("\nFailed tasks:")
                for error_result in task_failures:
                    print(f"  - {error_result.description}: {error_result.error_message}")
    
    # Show summary
    print(f"\nProcessed {len(all_files)} files:")
    print(f"  ✓ {len(successes)} successful")
    if duplicate_count > 0:
        print(f"  ≡ {duplicate_count} duplicates")
    if failures:
        print(f"  ✗ {len(failures)} failed")
        if loglevel == logging.DEBUG:
            print("\nFailed files:")
            for error_result in failures:
                print(
                    f"  - {error_result.original_filepath}: {error_result.error_message}"
                )
    site_dirpath = Path(args.out)
    site_dirpath.mkdir(parents=True, exist_ok=True)
    db_filepath = site_dirpath / "db.yaml"
    
    # Create database with meta section
    db_content = {
        "meta": {},
        "books": [result.to_dict() for result in deduplicated_results]
    }
    
    # Check if edit_api_url file exists (written by server)
    edit_api_file = site_dirpath / ".edit_api_url"
    if edit_api_file.exists():
        edit_api_url = edit_api_file.read_text().strip()
        if edit_api_url:
            db_content["meta"]["edit_api"] = edit_api_url
    
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
    # Return non-zero if there were any failures
    return 1 if failures else 0


def get_files_from_dirpath(dirpath: Path) -> list[Path]:
    all_files: list[Path] = []
    for root, dirs, files in os.walk(dirpath):
        for file in files:
            all_files.append((Path(root) / file).resolve())
    return all_files


def start_edit_server(task_directory: Path, site_dirpath: Path, port: int = 8080):
    """Start HTTP server for edit mode with add_task endpoint."""
    
    # Write the API URL to a file so it can be included in db.yaml
    site_dirpath.mkdir(parents=True, exist_ok=True)
    edit_api_file = site_dirpath / ".edit_api_url"
    edit_api_url = f"http://localhost:{port}"
    edit_api_file.write_text(edit_api_url)
    
    class TaskRequestHandler(BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path == "/add_task":
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                
                try:
                    # Parse JSON data
                    data = json.loads(post_data.decode('utf-8'))
                    
                    # Validate required fields
                    if 'description' not in data:
                        self.send_error(400, "Missing required field: description")
                        return
                    
                    # Create task
                    task = Task(
                        description=data['description'],
                        parameters=data.get('parameters', '')
                    )
                    
                    # Add task to tasks.jsonl
                    tasks_filepath = task_directory / "tasks.jsonl"
                    tasks_file = TasksFile(tasks_filepath)
                    tasks_file.add_task(task)
                    
                    # Send success response
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    response = {
                        'status': 'success',
                        'message': f'Task added: {task.description}',
                        'task': task.to_dict()
                    }
                    self.wfile.write(json.dumps(response).encode('utf-8'))
                    
                except json.JSONDecodeError:
                    self.send_error(400, "Invalid JSON")
                except Exception as e:
                    self.send_error(500, f"Server error: {str(e)}")
            else:
                self.send_error(404, "Not found")
        
        def do_GET(self):
            if self.path == "/info":
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                response = {
                    'directory': str(task_directory),
                    'site_directory': str(site_dirpath)
                }
                self.wfile.write(json.dumps(response).encode('utf-8'))
            else:
                self.send_error(404, "Not found")
        
        def log_message(self, format, *args):
            # Override to customize logging
            logger.info(f"{self.address_string()} - {format % args}")
    
    # Create and start server
    server_address = ('', port)
    httpd = HTTPServer(server_address, TaskRequestHandler)
    
    print(f"\nStarting EFM API server on port {port}")
    print(f"Task directory: {task_directory}")
    print(f"Tasks will be saved to: {task_directory / 'tasks.jsonl'}")
    print("\nAPI endpoints:")
    print(f"  GET  http://localhost:{port}/info      - Get server info")
    print(f"  POST http://localhost:{port}/add_task  - Add a new task")
    print("\nPress Ctrl+C to stop the server\n")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.shutdown()
        # Clean up the API URL file
        if edit_api_file.exists():
            edit_api_file.unlink()
        return 0


if __name__ == "__main__":
    sys.exit(main())
