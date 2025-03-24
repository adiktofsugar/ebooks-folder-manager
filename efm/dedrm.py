import logging
import os
import time
from typing import TypeGuard

from DeDRM_tools.DeDRM_plugin import ineptepub
from DeDRM_tools.DeDRM_plugin import epubtest
from DeDRM_tools.DeDRM_plugin import zipfix
from DeDRM_tools.DeDRM_plugin import ineptpdf
from DeDRM_tools.DeDRM_plugin import erdr2pml
from DeDRM_tools.DeDRM_plugin import k4mobidedrm
from DeDRM_tools.DeDRM_plugin.topazextract import TopazBook

from efm.exceptions import (
    RemoveDrmError,
    UnsupportedEncryptionError,
    ZipFixError,
)

logger = logging.getLogger(__name__)


def decryptepub(infile: str, outdir: str, key_files: list[str]) -> str:
    # first fix the epub to make sure we do not get errors
    filename = os.path.splitext(os.path.basename(infile))[0]
    bpath = os.path.dirname(infile)
    zippath = os.path.join(bpath, filename + "_temp.zip")
    rv = zipfix.repairBook(infile, zippath)
    if rv != 0:
        raise ZipFixError(infile)
    outfile = os.path.join(outdir, filename + "_nodrm.epub")
    try:
        if ineptepub.adeptBook(zippath):
            for key_file in key_files:
                userkey = open(key_file, "rb").read()
                try:
                    rv = ineptepub.decryptBook(userkey, zippath, outfile)
                    if rv == 0:
                        logger.info(f"Decrypted {infile} with key file {key_file}")
                        return outfile
                except Exception as e:
                    raise RemoveDrmError(infile, original_error=e)
            raise RemoveDrmError(infile, message="No valid key file found")
        else:
            encryption = epubtest.encryption(zippath)
            if encryption == "Unencrypted":
                logger.info("{0} is not DRMed.".format(filename))
                return infile
            raise UnsupportedEncryptionError(infile, encryption)
    finally:
        os.remove(zippath)


def decryptpdf(infile: str, outdir: str, key_files: list[str]) -> str:
    filename = os.path.splitext(os.path.basename(infile))[0]
    outfile = os.path.join(outdir, filename + "_nodrm.pdf")
    for key_file in key_files:
        userkey = open(key_file, "rb").read()
        try:
            rv = ineptpdf.decryptBook(userkey, infile, outfile)
            if rv == 0:
                logger.info(f"Decrypted {infile} with {key_file}")
                return outfile
        except Exception as e:
            raise RemoveDrmError(infile, original_error=e)
    raise RemoveDrmError(infile, message="No valid key file found")


def decryptpdb(infile: str, outdir: str, social_drm_file: str) -> str:
    outname = os.path.splitext(os.path.basename(infile))[0] + ".pmlz"
    outpath = os.path.join(outdir, outname)
    rv = 1
    keydata = open(social_drm_file, "r").read()
    keydata = keydata.rstrip(os.linesep)
    ar = keydata.split(",")
    for i in ar:
        try:
            name, cc8 = i.split(":")
        except ValueError as e:
            raise RemoveDrmError(
                infile, "Error parsing user supplied social drm data.", original_error=e
            )
        try:
            rv = erdr2pml.decryptBook(
                infile, outpath, True, erdr2pml.getuser_key(name, cc8)
            )
            if rv == 0:
                logger.info(f"Decrypted {infile} with key {name}")
                return outpath
        except Exception as e:
            logger.debug(f"Failed decryptinh with key {name} - {e}")
    raise RemoveDrmError(infile, message="No valid key file found")


"""
This takes a bunch of config options I'm not totally sure we really need. In the end, it seems to only
really need the "pids", which it extracts from the various other sources.

The way it gets the keys _seems_ to be in efm/DeDRM_tools/DeDRM_plugin/config.py

This will _probably_ be a big part of the "setup" process...or some way of defining a keystore. I'm not sure
I really want this part to just be config file entries. Maybe it'll point to a keystore or something.

Much of this seems to be kindlekey.py
"""


def decryptk4mobi(
    infile: str,
    outdir: str,
    kindle_pids: list[str],
    kindle_serials: list[str],
    kindle_db_files: list[str],
    kindle_android_files: list[str],
) -> str:
    starttime = time.time()

    kindle_dbs, errors = k4mobidedrm.collectKDatabases(kindle_db_files)
    if len(errors) > 0:
        message = "Error collecting database files:"
        for dbfile, e in errors:
            message += f"{dbfile}: {e}"
        raise RemoveDrmError(infile, message)

    try:
        book = k4mobidedrm.GetDecryptedBook(
            infile,
            kindle_dbs,
            kindle_android_files,
            kindle_serials,
            kindle_pids,
            starttime,
        )
    except Exception as e:
        raise RemoveDrmError(infile, "Could not decrypt", original_error=e)

    logger.info(f"Decrypted {infile}")
    outfilename = k4mobidedrm.inferReasonableName(infile, book.getBookTitle())
    outfilename = outfilename + "_nodrm"
    outfile = os.path.join(outdir, outfilename + book.getBookExtension())

    book.getFile(outfile)

    if is_topaz_book(book):
        logger.error(
            "Topaz SVG books are not supported since they apparently output two files"
        )
        # zipname = os.path.join(outdir, outfilename + "_SVG.zip")
        # book.getSVGZip(zipname)
        # logger.info(
        #     "Saved SVG ZIP Archive for {1:s} after {0:.1f} seconds".format(
        #         time.time() - starttime, outfilename
        #     )
        # )

    # remove internal temporary directory of Topaz pieces
    book.cleanup()
    return outfile


def is_topaz_book(book) -> TypeGuard[TopazBook]:
    return book.getBookType() == "Topaz"
