import os

from efm.exceptions import UnsupportedFormatError

"""
I have one of 2 choices here, I think:
1. figure out a way to run DeDRM from here (fake the calibre class, make certain assumptions true, etc.)
2. copy basically the whole thing in here

Theoretically, #1 will allow for easier upgrades, but I don't think it'll let me make the flow I want.
...even with the adobekey it's kind of impossible.

#2 is basically just a copy paste with some minor changes, so if I'm careful with how I copy it, it
# could mostly be a 1 to 1 copy, and then I can make some changes in how certain things are called...
"""


def decrypt(path_to_ebook: str) -> str:
    booktype = os.path.splitext(path_to_ebook)[1].lower()[1:]
    if booktype in [
        "prc",
        "mobi",
        "pobi",
        "azw",
        "azw1",
        "azw3",
        "azw4",
        "tpz",
        "kfx-zip",
    ]:
        # Kindle/Mobipocket
        return decrypt_kindle(path_to_ebook)
    elif booktype == "pdb":
        # eReader
        return decrypt_ereader(path_to_ebook)
    elif booktype == "pdf":
        # Adobe PDF (hopefully) or LCP PDF
        return decrypt_pdf(path_to_ebook)
        pass
    elif booktype == "epub":
        # Adobe Adept, PassHash (B&N) or LCP ePub
        return decrypt_epub(path_to_ebook)
    raise UnsupportedFormatError(
        path_to_ebook, format_type=booktype, message="Unknown book type"
    )


def decrypt_kindle(path_to_ebook: str) -> str:
    # Kindle/Mobipocket
    pass


def decrypt_ereader(path_to_ebook: str) -> str:
    # eReader
    pass


def decrypt_pdf(path_to_ebook: str) -> str:
    # Adobe PDF (hopefully) or LCP PDF
    pass


def decrypt_epub(path_to_ebook: str) -> str:
    # Adobe Adept, PassHash (B&N) or LCP ePub
    pass
