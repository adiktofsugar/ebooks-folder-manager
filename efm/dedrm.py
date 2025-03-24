import logging
import os
from textwrap import dedent
import time
import traceback
from typing import TypeGuard

from DeDRM_plugin import ineptepub
from DeDRM_plugin import epubtest
from DeDRM_plugin import zipfix
from DeDRM_plugin import ineptpdf
from DeDRM_plugin import erdr2pml
from DeDRM_plugin import k4mobidedrm
from DeDRM_plugin.topazextract import TopazBook

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


def decryptpdf(
    infile: str, outdir: str, key_files: list[str], passwords: list[str]
) -> str:
    filename = os.path.splitext(os.path.basename(infile))[0]

    try:
        pdf_encryption = ineptpdf.getPDFencryptionType(infile)
        if pdf_encryption is None:
            logger.debug(f"Skipping {infile}. has no drm")
            return infile

        logger.debug(f"PDF encryption type for {infile}: {pdf_encryption}")

        keys: list[tuple[str, bytearray | bytes]] | None = None
        if pdf_encryption == "EBX_HANDLER":
            # Adobe eBook / ADEPT (normal or B&N)
            keys = [(key_file, open(key_file, "rb").read()) for key_file in key_files]
        elif pdf_encryption == "Standard" or pdf_encryption == "Adobe.APS":
            keys = [
                (password, bytearray(password, "utf-8"))
                for password in [""] + passwords
            ]

        if keys is not None:
            outfile = os.path.join(outdir, filename + "_nodrm.pdf")
            for key_name, key in keys:
                try:
                    rv = ineptpdf.decryptBook(key, infile, outfile)
                    if rv == 0:
                        logger.info(f"Decrypted {infile} with {key_name}")
                        return outfile
                except ineptpdf.ADEPTInvalidPasswordError:
                    logger.debug(f"Invalid password for {infile}: '{key_name}'")
                except Exception as e:
                    raise RemoveDrmError(infile, original_error=e)
            raise RemoveDrmError(infile, message="No valid key file found")

        if pdf_encryption == "FOPN_fLock" or pdf_encryption == "FOPN_foweb":
            raise RemoveDrmError(
                infile,
                message=dedent("""
                    FileOpen encryption is unsupported.
                    Try the standalone script from the 'Tetrachroma_FileOpen_ineptpdf' folder in the Github repo.
                """),
            )
        raise RemoveDrmError(
            infile,
            message=f"Unsupported encryption type '{pdf_encryption}'",
        )
    except ineptpdf.PDFNoValidXRef as e:
        logger.debug(
            f"{infile} is invalid according to dedrm, but we ignore since it doesn't matter if it's not encrypted"
        )
        return infile


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
            logger.debug(f"Failed decrypting with key {name} - {e}")
    raise RemoveDrmError(infile, message="No valid key file found")


"""
Config options to descriptions (based on DeDRM_tools/DeDRM_plugin/config.py):
    pids (list)
        d = ManageKeysDialog(self,"Mobipocket PID",self.tempdedrmprefs['pids'], AddPIDDialog)
        aska for a Mobipocket PID, described as
            > Mobipocket PIDs are 8 or 10 characters long. Mobipocket PIDs are case-sensitive, so be sure to enter the upper and lower case letters unchanged.
        ...I don't know what this is. Mobipocket was a French software company amazon bought in 2005, and they invented
            the mobi file format. They did have an online website, so maybe it's from that?

    serials (list)
        d = ManageKeysDialog(self,"EInk Kindle Serial Number",self.tempdedrmprefs['serials'], AddSerialDialog)
        asks for an EInk Kindle serial number, described as 
            > 16 characters long and usually start with a 'B' or a '9'. Kindle Serial Numbers are case-sensitive, so be sure to enter the upper and lower case letters unchanged.
        I think this is literally the serial number of the Kindle device
    
    androidkeys (dict)
        d = ManageKeysDialog(self,"Kindle for Android Key",self.tempdedrmprefs['androidkeys'], AddAndroidDialog, 'k4a')
        asks for a "Kindle for Android backup file" that ends in 'db','ab','xml'
            then uses androidkindlekey.get_serials(fpath) (DeDRM_tools/DeDRM_plugin/androidkindlekey.py)
            > get serials from files in from android backup.ab
                backup.ab can be get using adb command:
                shell> adb backup com.amazon.kindle
                or from individual files if they're passed.
    
    kindlekeys (dict)
        d = ManageKeysDialog(self,"Kindle for Mac and PC Key",self.tempdedrmprefs['kindlekeys'], AddKindleDialog, 'k4i')
        asks for a name and finds the default key (using DeDRM_tools/DeDRM_plugin/kindlekey.py) that it finds from
            the Kindle App on your computer

The final thing, kDatabases, is probably from the DeDRM plugin
> kDatabaseFiles is a list of files created by kindlekey
But I see no reference to that variable name, so :shrug:

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
    except Exception as e:
        logger.error(
            f"Failed to decrypt {infile}: {''.join(traceback.format_exception_only(e))}"
        )
        raise RemoveDrmError(infile, "Could not decrypt", original_error=e) from e


def is_topaz_book(book) -> TypeGuard[TopazBook]:
    return book.getBookType() == "Topaz"
