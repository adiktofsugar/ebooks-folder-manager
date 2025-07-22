"""File type detection utilities."""

import logging
from pathlib import Path
import pymupdf

logger = logging.getLogger(__name__)




def detect_format(filepath: Path) -> str | None:
    """Detect the format of an ebook file.
    
    Returns:
        'pdf', 'epub', or None if unknown
    """
    # Try PyMuPDF first as it can detect many formats accurately
    try:
        doc = pymupdf.open(filepath)
        if doc.metadata:
            format = doc.metadata.get("format")
            doc.close()
            if format:
                # Check if it's a PDF (could be "PDF 1.7", etc.)
                if format.lower().startswith("pdf"):
                    return "pdf"
        doc.close()
    except:
        pass
    
    # Try EPUB detection using ebooklib (content-based)
    try:
        import ebooklib.epub as epub
        book = epub.read_epub(filepath)  # pyright: ignore[reportUnknownMemberType]
        return "epub"
    except:
        pass
    
    # Fall back to extension only for known formats
    ext = filepath.suffix.lower()
    if ext == ".pdf":
        return "pdf"
    elif ext == ".epub":
        # Double-check with content-based detection already done above
        return None  # If it wasn't detected as EPUB above, it's not a valid EPUB
    
    return None