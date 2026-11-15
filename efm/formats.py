"""Format-specific metadata that pymupdf doesn't report (series, EPUB version)."""

import posixpath
import zipfile
from pathlib import Path
from typing import Any

from lxml import etree

CONTAINER_NS = {"c": "urn:oasis:names:tc:opendocument:xmlns:container"}
OPF_NS = {
    "opf": "http://www.idpf.org/2007/opf",
    "dc": "http://purl.org/dc/elements/1.1/",
}


def _text(value: str | None) -> str | None:
    if value is None:
        return None
    value = " ".join(value.split())
    return value or None


def _parse_xml(data: bytes) -> etree._Element:
    # No network or entity expansion: books are untrusted input.
    parser = etree.XMLParser(resolve_entities=False, no_network=True, recover=True)
    root = etree.fromstring(data, parser)
    if root is None:
        raise ValueError("empty XML document")
    return root


# What the readers below can raise for a broken or unexpected book.
READ_ERRORS = (OSError, zipfile.BadZipFile, KeyError, ValueError, etree.LxmlError)


def read_epub_fields(book_file: Path) -> dict[str, Any]:
    with zipfile.ZipFile(book_file) as z:
        container = _parse_xml(z.read("META-INF/container.xml"))
        rootfile = container.find(".//c:rootfile", CONTAINER_NS)
        opf_path = rootfile.get("full-path") if rootfile is not None else None
        if not opf_path:
            raise ValueError("container.xml has no rootfile")
        opf_path = posixpath.normpath(opf_path)
        package = _parse_xml(z.read(opf_path))

    metadata = package.find("opf:metadata", OPF_NS)
    metas = metadata.findall("opf:meta", OPF_NS) if metadata is not None else []

    def meta(attr: str, value: str) -> etree._Element | None:
        return next((m for m in metas if m.get(attr) == value), None)

    def dc(tag: str) -> list[str]:
        if metadata is None:
            return []
        return [
            t for el in metadata.findall(f"dc:{tag}", OPF_NS) if (t := _text(el.text))
        ]

    series, series_index = None, None
    # EPUB3 collection; group-position refines it by id.
    if (collection := meta("property", "belongs-to-collection")) is not None:
        series = _text(collection.text)
        if coll_id := collection.get("id"):
            position = next(
                (
                    m
                    for m in metas
                    if m.get("property") == "group-position"
                    and m.get("refines") == f"#{coll_id}"
                ),
                None,
            )
            series_index = _text(position.text) if position is not None else None
    if series is None:
        calibre_series = meta("name", "calibre:series")
        calibre_index = meta("name", "calibre:series_index")
        series = (
            _text(calibre_series.get("content")) if calibre_series is not None else None
        )
        series_index = (
            _text(calibre_index.get("content")) if calibre_index is not None else None
        )

    titles = dc("title")
    return {
        "version": package.get("version"),
        "opf_path": opf_path,
        "title": titles[0] if titles else None,
        "creators": dc("creator"),
        "series": series,
        "series_index": series_index if series else None,
    }


def read_cbz_fields(book_file: Path) -> dict[str, Any]:
    with zipfile.ZipFile(book_file) as z:
        name = next(
            (n for n in z.namelist() if n.lower() == "comicinfo.xml"), "ComicInfo.xml"
        )
        info = _parse_xml(z.read(name))

    def field(tag: str) -> str | None:
        el = info.find(tag)
        return _text(el.text) if el is not None else None

    return {
        "series": field("Series"),
        "number": field("Number"),
        "title": field("Title"),
        "writer": field("Writer"),
    }
