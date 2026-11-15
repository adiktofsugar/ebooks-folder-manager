"""Small but real EPUB/CBZ files, for metadata that the sample books don't have."""

import io
import zipfile
from pathlib import Path

from PIL import Image

CONTAINER_XML = """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>"""

CHAPTER_XHTML = """<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"><head><title>c</title></head><body><p>Hello.</p></body></html>"""


def make_epub(
    file: Path,
    *,
    version: str = "2.0",
    title: str = "A Title",
    author: str = "An Author",
    extra_meta: str = "",
) -> Path:
    opf = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="{version}" unique-identifier="id">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="id">urn:uuid:1</dc:identifier>
    <dc:title>{title}</dc:title>
    <dc:creator>{author}</dc:creator>
    <dc:language>en</dc:language>
    {extra_meta}
  </metadata>
  <manifest><item id="c" href="c.xhtml" media-type="application/xhtml+xml"/></manifest>
  <spine><itemref idref="c"/></spine>
</package>"""
    with zipfile.ZipFile(file, "w") as z:
        z.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml", CONTAINER_XML)
        z.writestr("OEBPS/content.opf", opf)
        z.writestr("OEBPS/c.xhtml", CHAPTER_XHTML)
    return file


def make_cbz(file: Path, comic_info: str | None) -> Path:
    png = io.BytesIO()
    Image.new("RGB", (8, 8), "white").save(png, "PNG")
    with zipfile.ZipFile(file, "w") as z:
        z.writestr("001.png", png.getvalue())
        if comic_info is not None:
            z.writestr("ComicInfo.xml", comic_info)
    return file
