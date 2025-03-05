import argparse
import logging
import os
import textwrap
import time
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from efm.book import Book


def main():
    argparser = argparse.ArgumentParser(
        add_help=True,
        usage="""
      Run efm on folder. This will walk that folder recursively and perform all actions you specify.
      If no actions are specified, will use any efm.(yaml|yml|json|jsonc) files in the folder.
    """,
        epilog=textwrap.dedent("""
      <action>  is one of:
        - drm           remove DRM from files (backs up original as .bak)
        - rename        rename files based on metadata
        - print         print metadata to console
        - pdf           reformat a PDF via k2pdfopt (backs up original as .bak)
        - none          do nothing (useful for testing to see if we don't throw any errors)
    """),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    argparser.add_argument("folder", help="folder to process")
    argparser.add_argument(
        "action",
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
    argparser.add_argument("--adobekey", help="path to Adobe key file")
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

    for root, dirs, files in os.walk(args.folder):
        for file in files:
            if file.endswith(".bak"):
                continue
            process_book(
                Book(
                    os.path.join(root, file), adobe_key_file=args.adobekey, dry=args.dry
                ),
                args.action,
            )

    if args.watch:
        event_handler = OnBookChangeAdd(adobe_key_file=args.adobekey, dry=args.dry)
        observer = Observer()
        observer.schedule(event_handler, path=args.folder, recursive=True)
        observer.start()
        try:
            while True:
                time.sleep(1)
        finally:
            observer.stop()
            observer.join()


class OnBookChangeAdd(FileSystemEventHandler):
    def __init__(self, adobe_key_file=str | None, dry=bool | None):
        self.adobe_key_file = adobe_key_file
        self.dry = dry

    def on_created(self, event):
        if event.is_file:
            book = Book(event.src_path)
            process_book(book, args.action)

    def on_modified(self, event):
        return super().on_modified(event)


def process_book(book: Book, actions: list[str]):
    # Note: this order has significance
    if "drm" in actions:
        book.remove_drm()
    if "rename" in actions:
        book.rename()
    if "print" in actions:
        book.print_metadata()
    if "pdf" in actions:
        book.reformat_pdf()
    if "none" in actions:
        book.get_metadata()
    book.save()


if __name__ == "__main__":
    main()
