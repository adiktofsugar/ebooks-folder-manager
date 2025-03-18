import os
from unittest.mock import patch
import pytest
import tempfile
import shutil

from efm.book import Book, BookMetadata
from efm.exceptions import (
    DetectEncryptionError,
    UnsupportedEncryptionError,
)


@pytest.fixture
def sample_paths():
    """Fixture providing paths to sample books"""
    sample_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "sample-books"
    )
    return {
        "sample_dir": sample_dir,
        "basic_epub": os.path.join(sample_dir, "1Q84.epub"),
        "basic_pdf": os.path.join(sample_dir, "Emotions.pdf"),
        "series_epub": os.path.join(sample_dir, "InterestingTimes.epub"),
        "weird_title_epub": os.path.join(sample_dir, "WorldUnbound.epub"),
    }


@pytest.fixture
def temp_dir():
    """Fixture providing a temporary directory for test files"""
    dir_path = tempfile.mkdtemp()
    yield dir_path
    # Cleanup after test
    shutil.rmtree(dir_path)


def test_init(sample_paths):
    """Test Book initialization"""
    book = Book(sample_paths["epub_file"])
    assert book.file == sample_paths["epub_file"]
    assert book.dry is False
    assert book.metadata is None
    assert book.new_file is None
    assert book.tmp_file is None


def test_get_metadata_epub(sample_paths):
    """Test getting metadata from an EPUB file"""
    book = Book(sample_paths["epub_file"])
    metadata = book.get_metadata()

    # Verify metadata is retrieved and has the expected structure
    assert isinstance(metadata, BookMetadata)
    assert metadata.format is not None
    assert metadata.title is not None

    # Format should be EPUB for this file
    assert "EPUB" in metadata.format.upper()


def test_get_metadata_pdf(sample_paths):
    """Test getting metadata from a PDF file"""
    book = Book(sample_paths["pdf_file"])
    metadata = book.get_metadata()

    # Verify metadata is retrieved and has the expected structure
    assert isinstance(metadata, BookMetadata)
    assert metadata.format is not None

    # Format should be PDF for this file
    assert "PDF" in metadata.format.upper()

    # Check is_k2pdfopt_version attribute for PDF files
    assert metadata.is_k2pdfopt_version is False


def test_get_tmp_file(sample_paths):
    """Test creating a temporary file"""
    book = Book(sample_paths["epub_file"])
    tmp_file = book.get_tmp_file()

    # Verify tmp_file is created and exists
    assert tmp_file is not None
    assert os.path.exists(tmp_file)

    # Verify tmp_file has the same extension as the original file
    _, orig_ext = os.path.splitext(sample_paths["epub_file"])
    _, tmp_ext = os.path.splitext(tmp_file)
    assert orig_ext == tmp_ext


def test_print_metadata(sample_paths, capsys):
    """Test printing metadata using pytest's capsys fixture to capture stdout"""
    book = Book(sample_paths["epub_file"])
    book.print_metadata()

    # Capture the printed output
    captured = capsys.readouterr()

    # Verify output contains expected information
    assert "Metadata for" in captured.out
    assert "Format:" in captured.out
    assert "Title:" in captured.out


def test_rename(sample_paths, temp_dir):
    """Test renaming a book based on metadata"""
    # Copy a sample file to the temp directory for testing
    test_file = os.path.join(temp_dir, "test.epub")
    shutil.copy(sample_paths["epub_file"], test_file)

    book = Book(test_file)
    book.rename()

    # Verify new_file is set and has the expected format
    assert book.new_file is not None

    # New filename should be in the format "Author - Title.ext"
    metadata = book.get_metadata()
    expected_name = f"{metadata.author} - {metadata.title}.epub"
    expected_path = os.path.join(temp_dir, expected_name)

    assert book.new_file == expected_path


@pytest.mark.parametrize(
    "encryption_type,expected_exception",
    [
        ("Unencrypted", None),
        ("Error", DetectEncryptionError),
        ("Readium LCP", UnsupportedEncryptionError),
        ("Apple", UnsupportedEncryptionError),
        ("Kobo", UnsupportedEncryptionError),
        ("B&N", UnsupportedEncryptionError),
    ],
)
def test_remove_drm(sample_paths, encryption_type, expected_exception):
    """Test removing DRM with different encryption types"""
    with patch("efm.book.encryption", return_value=encryption_type):
        book = Book(sample_paths["epub_file"])

        if expected_exception:
            with pytest.raises(expected_exception):
                book.remove_drm()
        else:
            # Should not raise an exception for unencrypted files
            book.remove_drm()
            # No tmp_file should be created for unencrypted files
            assert book.tmp_file is None


def test_process_print_action(sample_paths):
    """Test processing a book with the 'print' action"""
    with patch.object(Book, "print_metadata") as mock_print:
        book = Book(sample_paths["epub_file"])
        book.process(["print"])

        # Verify print_metadata was called
        mock_print.assert_called_once()


def test_process_multiple_actions(sample_paths):
    """Test processing a book with multiple actions"""
    with (
        patch.object(Book, "print_metadata") as mock_print,
        patch.object(Book, "rename") as mock_rename,
        patch.object(Book, "save") as mock_save,
    ):
        book = Book(sample_paths["epub_file"])
        book.process(["print", "rename"])

        # Verify all expected methods were called
        mock_print.assert_called_once()
        mock_rename.assert_called_once()
        mock_save.assert_called_once()


def test_save_with_rename(sample_paths, temp_dir):
    """Test saving a book after renaming"""
    # Copy a sample file to the temp directory for testing
    test_file = os.path.join(temp_dir, "test_save.epub")
    shutil.copy(sample_paths["epub_file"], test_file)

    book = Book(test_file, dry=True)  # Use dry mode to avoid actual file operations

    # Set up a new file name
    new_file = os.path.join(temp_dir, "New Name.epub")
    book.new_file = new_file

    with patch("logging.info") as mock_log:
        book.save()

        # Verify logging occurred with the expected message
        mock_log.assert_called_with(f"Would rename {test_file} to {new_file}")

        # In dry mode, the file should not actually be renamed
        assert os.path.exists(test_file)
        assert not os.path.exists(new_file)


def test_save_with_tmp_file(sample_paths, temp_dir):
    """Test saving a book after creating a temporary file"""
    # Copy a sample file to the temp directory for testing
    test_file = os.path.join(temp_dir, "test_tmp.epub")
    shutil.copy(sample_paths["epub_file"], test_file)

    book = Book(test_file, dry=True)  # Use dry mode to avoid actual file operations

    # Force creation of a tmp_file
    tmp_file = book.get_tmp_file()

    with patch("logging.info") as mock_log:
        book.save()

        # Verify logging occurred with the expected message
        mock_log.assert_called_with(f"Would save {test_file} with changes")
