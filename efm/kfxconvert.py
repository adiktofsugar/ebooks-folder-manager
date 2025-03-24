"""
Modified version of KFX_Input.__init__.py#convert
Library taken from https://www.mobileread.com/forums/showthread.php?t=291290
(I can't find a repo for it)
Notable changes:
- don't support streams
- no symbol_catalog_filename. there seems to be a default one, but I'm not sure how you're supposed to have this thing anyway...
"""

import logging
from typing import cast
from kfxlib import (
    JobLog,
    set_logger,
    YJ_Book,
)

logger = logging.getLogger(__name__)


def convert_to_epub(filepath: str, convert_to_epub_2=False) -> bytes:
    # set_logger puts my logger onto a thread local
    job_log = cast(JobLog, set_logger(JobLog(logger)))
    job_log.info("Converting %s" % filepath)

    # no symbol_catalog_filename because I have no idea where it is
    book = YJ_Book(filepath)
    book.decode_book(retain_yj_locals=True)

    if book.has_pdf_resource:
        job_log.warning(
            "This book contains PDF content. It can be extracted using either the From KFX user interface "
            "plugin or the KFX Input plugin CLI. See the KFX Input plugin documentation for more information."
        )

    if book.is_fixed_layout or book.is_magazine:
        job_log.warning(
            "This book has a layout that is incompatible with calibre conversion. For best results use either "
            "the From KFX user interface plugin or the KFX Input plugin CLI for conversion. See the KFX Input "
            "plugin documentation for more information."
        )

    epub_data = book.convert_to_epub(epub2_desired=convert_to_epub_2)

    # unset global logger
    set_logger()

    if job_log.errors:
        raise Exception("\n".join(job_log.errors))

    return epub_data
