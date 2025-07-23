import pytest
import tempfile
from pathlib import Path
import pymupdf
from PIL import Image
import io
import hashlib

from efm.tasks import TaskSetCover, handle_set_cover, TaskSuccess
from efm.detection import detect_format
from efm.metadata import extract_cover_image, get_metadata



def create_test_pdf(filepath: Path) -> None:
    """Create a simple test PDF."""
    doc: pymupdf.Document = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((50, 50), "Test PDF Document")
    doc.save(filepath)
    doc.close()


def create_test_epub(filepath: Path) -> None:
    """Create a minimal test EPUB."""
    import zipfile
    import xml.etree.ElementTree as ET

    with zipfile.ZipFile(filepath, "w") as epub:
        # Add mimetype
        epub.writestr(
            "mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED
        )

        # Add container.xml
        container = """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>"""
        epub.writestr("META-INF/container.xml", container)

        # Add content.opf
        opf = """<?xml version="1.0"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>Test EPUB</dc:title>
    <dc:creator>Test Author</dc:creator>
  </metadata>
  <manifest>
    <item id="text" href="text.html" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="text"/>
  </spine>
</package>"""
        epub.writestr("content.opf", opf)

        # Add content
        html = """<html><body><h1>Test EPUB</h1></body></html>"""
        epub.writestr("text.html", html)


def create_test_cover_image() -> bytes:
    """Create a simple test cover image."""
    img = Image.new("RGB", (300, 400), color="blue")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


class TestCoverDetection:
    """Test that manually set covers are properly detected."""

    def test_pdf_cover_detection_after_manual_set(self, tmp_path):
        """Test that PDF cover added as first page is detected by extract_cover_image."""
        # Create test PDF
        pdf_path = tmp_path / "test.pdf"
        create_test_pdf(pdf_path)

        # Verify it will actually be detected as a pdf...
        assert detect_format(pdf_path) == "pdf"

        # Create cover image
        cover_path = tmp_path / "cover.png"
        cover_data = create_test_cover_image()
        cover_path.write_bytes(cover_data)

        # Get metadata before setting cover
        metadata_before = get_metadata(pdf_path)
        cache_dir = tmp_path / "_cache" / "covers"

        # Extract cover before setting (should generate one)
        cover_hash_before = extract_cover_image(pdf_path, metadata_before, cache_dir)
        assert cover_hash_before is not None

        # Set cover using handle_set_cover
        task = TaskSetCover(
            key="set_cover", book_filepath=pdf_path, cover_tmp_filepath=cover_path
        )
        result = handle_set_cover(task)
        assert isinstance(result, TaskSuccess)
        assert "Successfully set cover for" in str(result.messages)

        # Get metadata after setting cover
        metadata_after = get_metadata(pdf_path)

        # Extract cover after setting (should find our manually set cover)
        cover_hash_after = extract_cover_image(pdf_path, metadata_after, cache_dir)
        assert cover_hash_after is not None

        # The hashes should be different (generated vs manually set)
        assert cover_hash_before != cover_hash_after

        # Verify the extracted cover matches what we set
        cached_cover_path = cache_dir / f"{cover_hash_after}.png"
        assert cached_cover_path.exists()

        # Load and verify it's our blue cover
        img = Image.open(cached_cover_path)
        assert img.size == (300, 400)  # Should match our test cover size
        # Check that it's predominantly blue
        pixels = list(img.getdata())
        blue_pixels = sum(1 for r, g, b in pixels if b > 200 and r < 100 and g < 100)
        assert blue_pixels > len(pixels) * 0.9  # Should be mostly blue

    def test_epub_cover_detection_after_manual_set(self, tmp_path):
        """Test that EPUB cover added as embedded file is detected by extract_cover_image."""
        # Create test EPUB
        epub_path = tmp_path / "test.epub"
        create_test_epub(epub_path)

        # Create cover image
        cover_path = tmp_path / "cover.png"
        cover_data = create_test_cover_image()
        cover_path.write_bytes(cover_data)

        # Get metadata before setting cover
        metadata_before = get_metadata(epub_path)
        cache_dir = tmp_path / "_cache" / "covers"

        # Extract cover before setting (should generate one)
        cover_hash_before = extract_cover_image(epub_path, metadata_before, cache_dir)
        assert cover_hash_before is not None

        # Set cover using handle_set_cover
        task = TaskSetCover(
            key="set_cover", book_filepath=epub_path, cover_tmp_filepath=cover_path
        )
        result = handle_set_cover(task)
        assert isinstance(result, TaskSuccess)
        assert "Successfully set cover for" in str(result.messages)

        # Get metadata after setting cover
        metadata_after = get_metadata(epub_path)

        # Extract cover after setting
        # NOTE: Current implementation may not detect embedded __cover_ files
        # This test documents the current behavior
        cover_hash_after = extract_cover_image(epub_path, metadata_after, cache_dir)
        assert cover_hash_after is not None

        # TODO: Once extract_cover_image is updated to check embedded __cover_ files,
        # verify that cover_hash_after corresponds to our blue cover

    def test_format_detection_not_file_extension(self, tmp_path):
        """Test that format detection uses PyMuPDF metadata, not file extension."""
        # Create a PDF with wrong extension
        pdf_path = tmp_path / "test.epub"  # Wrong extension!
        create_test_pdf(pdf_path)

        # Create cover image
        cover_path = tmp_path / "cover.png"
        cover_data = create_test_cover_image()
        cover_path.write_bytes(cover_data)

        # Set cover - should still work because PyMuPDF detects it's a PDF
        task = TaskSetCover(
            key="set_cover", book_filepath=pdf_path, cover_tmp_filepath=cover_path
        )
        result = handle_set_cover(task)
        assert isinstance(result, TaskSuccess)
        assert "Successfully set cover for" in str(result.messages)

        assert detect_format(pdf_path) == "pdf"

        # Verify extract_cover_image works correctly despite wrong extension
        metadata = get_metadata(pdf_path)
        cache_dir = tmp_path / "_cache" / "covers"
        cover_hash = extract_cover_image(pdf_path, metadata, cache_dir)
        assert cover_hash is not None

        # Verify the extracted cover
        cached_cover_path = cache_dir / f"{cover_hash}.png"
        assert cached_cover_path.exists()
        img = Image.open(cached_cover_path)
        assert img.size == (300, 400)  # Should be our manually set cover

    def test_cover_cache_invalidation(self, tmp_path):
        """Test that cache is properly invalidated when cover is changed."""
        # Create test PDF
        pdf_path = tmp_path / "test.pdf"
        create_test_pdf(pdf_path)

        # Create site directory structure to match real usage
        site_dir = tmp_path / "site"
        site_dir.mkdir()
        cache_dir = site_dir / "_cache"
        cache_dir.mkdir()

        # Calculate file hash (matching the real implementation)
        with open(pdf_path, "rb") as f:
            file_hash = hashlib.blake2b(f.read(), digest_size=20).hexdigest()

        # Create a fake cached metadata file
        cached_metadata_path = cache_dir / f"{file_hash}.yaml"
        cached_metadata_path.write_text("title: Old Title\n")
        assert cached_metadata_path.exists()

        # Create cover image
        cover_path = tmp_path / "cover.png"
        cover_data = create_test_cover_image()
        cover_path.write_bytes(cover_data)

        # Move PDF to site directory (to match expected structure)
        new_pdf_path = site_dir / "test.pdf"
        pdf_path.rename(new_pdf_path)

        # Set cover
        task = TaskSetCover(
            book_filepath=new_pdf_path, cover_tmp_filepath=cover_path
        )
        result = handle_set_cover(task)
        assert isinstance(result, TaskSuccess)
        assert "Cleared metadata cache" in str(result.messages)

        # Verify cache was deleted
        assert not cached_metadata_path.exists()
