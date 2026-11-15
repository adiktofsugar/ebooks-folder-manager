import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "DeDRM_tools"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "kfxlib"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "adl"))

import argparse
import logging
from datetime import datetime
from typing import override

from rich.console import Console
from rich.logging import RichHandler
from rich.text import Text

from efm.commands import acsm, find, ls, rename, setup


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


LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "error": logging.ERROR,
}


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="efm", description="Ebooks Folder Manager")
    parser.add_argument(
        "--loglevel", choices=list(LOG_LEVELS), default="info", help="log level"
    )
    parser.add_argument(
        "--store",
        help="metadata store directory (default: $EFM_STORE, else $XDG_DATA_HOME/efm/store)",
    )
    parser.add_argument(
        "--no-stat-cache",
        action="store_true",
        help="always hash files instead of trusting unchanged size/mtime/ctime",
    )
    subparsers = parser.add_subparsers(title="commands", metavar="<command>")
    ls.add_parser(subparsers)
    find.add_parser(subparsers)
    acsm.add_parser(subparsers)
    rename.add_parser(subparsers)
    setup.add_parser(subparsers)
    return parser


def main() -> int:
    parser = create_parser()
    args = parser.parse_args()
    if not hasattr(args, "run"):
        parser.print_help()
        return 1

    # Set up console for progress bar and logging
    # stderr, so logs and progress never mix into stdout output like `ls -f json`
    console = Console(stderr=True)
    rich_handler = NarrowScreenRichHandler(
        console=console,
        rich_tracebacks=True,
        show_time=False,  # We handle time ourselves
        show_level=False,
        show_path=False,
        markup=True,
    )
    logging.basicConfig(
        level=LOG_LEVELS[args.loglevel], format="%(message)s", handlers=[rich_handler]
    )

    return args.run(args, console)


if __name__ == "__main__":
    sys.exit(main())
