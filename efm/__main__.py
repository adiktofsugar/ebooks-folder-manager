import argparse
import logging
import os
import textwrap

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

    books: list[Book] = []
    for root, dirs, files in os.walk(args.folder):
        for file in files:
            if file.endswith(".bak"):
                continue
            books.append(
                Book(
                    os.path.join(root, file), adobe_key_file=args.adobekey, dry=args.dry
                )
            )

    for book in books:
        if "drm" in args.action:
            book.remove_drm()
        if "rename" in args.action:
            book.rename()
        if "print" in args.action:
            book.print_metadata()
        if "pdf" in args.action:
            book.reformat_pdf()
        if "none" in args.action:
            book.get_metadata()
        book.save()


if __name__ == "__main__":
    main()
