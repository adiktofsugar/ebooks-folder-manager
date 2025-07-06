"""High-level tests for the efm transaction module using ramdisk."""

import pytest
import tempfile
import shutil
from pathlib import Path
import yaml
import uuid

from efm.transaction import Transaction, TransactionSuccess, TransactionError
from conftest import sanitize_string, sanitize_transaction


@pytest.fixture(scope="session")
def ramdisk_root(tmp_path_factory):
    """Create a session-scoped ramdisk directory."""
    # On Linux, /tmp is often a tmpfs (ramdisk)
    # pytest's tmp_path_factory already uses the system temp directory
    return tmp_path_factory.mktemp("efm_test_ramdisk")


@pytest.fixture
def test_env(ramdisk_root):
    """Set up test environment on ramdisk."""
    # Create test directories
    test_dir = ramdisk_root / f"test_{uuid.uuid4().hex[:8]}"
    test_dir.mkdir(exist_ok=True)
    
    sample_books_dir = test_dir / "sample-books"
    sample_books_dir.mkdir()
    
    site_dir = test_dir / "site"
    site_dir.mkdir()
    
    yield {
        "root": test_dir,
        "sample_books": sample_books_dir,
        "site": site_dir,
    }
    
    # Cleanup
    shutil.rmtree(test_dir)


def test_interesting_times_epub(test_env):
    """Test processing InterestingTimes.epub specifically."""
    # Copy the specific book we want to test
    source_book = Path("sample-books/InterestingTimes.epub")
    if not source_book.exists():
        pytest.skip("InterestingTimes.epub not found in sample-books")
    
    test_book = test_env["sample_books"] / "InterestingTimes.epub"
    shutil.copy(source_book, test_book)
    
    # Run transaction
    transaction = Transaction(test_book, test_env["site"])
    result = transaction.perform()
    
    # Expectations for InterestingTimes.epub
    assert isinstance(result, TransactionSuccess)
    assert result.metadata is not None
    assert result.metadata.title == "Interesting Times"
    assert result.metadata.author == "Terry Pratchett"
    assert result.metadata.format == "EPUB"
    
    # Check output filename
    assert result.filename == Path("books/Terry Pratchett-Interesting Times.epub")
    
    # Check the file exists
    output_file = test_env["site"] / result.filename
    assert output_file.exists()
    
    # Check cache exists
    cache_file = test_env["site"] / "_cache" / f"{result.hash}.yaml"
    assert cache_file.exists()


def test_emotions_pdf(test_env):
    """Test processing Emotions.pdf specifically."""
    # Copy the specific book we want to test
    source_book = Path("sample-books/Emotions.pdf")
    if not source_book.exists():
        pytest.skip("Emotions.pdf not found in sample-books")
    
    test_book = test_env["sample_books"] / "Emotions.pdf"
    shutil.copy(source_book, test_book)
    
    # Run transaction
    transaction = Transaction(test_book, test_env["site"])
    result = transaction.perform()
    
    # PDF processing might succeed or fail depending on metadata
    assert isinstance(result, (TransactionSuccess, TransactionError))
    
    if isinstance(result, TransactionSuccess):
        assert result.metadata is not None
        assert result.metadata.format in ["PDF", "PDF document"]
        # PDF might not have title/author metadata
        if result.metadata.title and result.metadata.author:
            assert result.metadata.author in str(result.filename)


def test_corrupted_epub(test_env):
    """Test processing a corrupted EPUB file."""
    # Create a file that claims to be EPUB but isn't valid
    bad_epub = test_env["sample_books"] / "corrupted.epub"
    bad_epub.write_text("This is not a valid EPUB file!")
    
    # Run transaction
    transaction = Transaction(bad_epub, test_env["site"])
    result = transaction.perform()
    
    # Should fail
    assert isinstance(result, TransactionError)
    assert "corrupted.epub" in str(result.original_filename)
    assert result.error_message is not None
    assert "metadata" in result.error_message.lower() or "open" in result.error_message.lower()
    assert len(result.messages) >= 2  # Should have error messages
    
    # Error should still be cached
    cache_files = list((test_env["site"] / "_cache").glob("*.yaml"))
    assert len(cache_files) == 1
    
    # Load cache and verify it's an error
    cache_data = yaml.safe_load(cache_files[0].read_text())
    assert cache_data["error"] is True


def test_duplicate_processing(test_env):
    """Test processing the same file twice uses cache."""
    # Copy InterestingTimes.epub
    source_book = Path("sample-books/InterestingTimes.epub")
    if not source_book.exists():
        pytest.skip("InterestingTimes.epub not found in sample-books")
    
    test_book = test_env["sample_books"] / "test.epub"
    shutil.copy(source_book, test_book)
    
    # First transaction
    transaction1 = Transaction(test_book, test_env["site"])
    result1 = transaction1.perform()
    
    assert isinstance(result1, TransactionSuccess)
    initial_messages_count = len(result1.messages)
    
    # Second transaction - should use cache
    transaction2 = Transaction(test_book, test_env["site"])
    result2 = transaction2.perform()
    
    assert isinstance(result2, TransactionSuccess)
    assert result2.hash == result1.hash
    assert result2.filename == result1.filename
    
    # Should have a skip message
    assert any("Skipping" in msg and "already been processed" in msg for msg in result2.messages)


def test_duplicate_content_different_names(test_env):
    """Test processing identical content with different filenames."""
    # Copy InterestingTimes.epub
    source_book = Path("sample-books/InterestingTimes.epub")
    if not source_book.exists():
        pytest.skip("InterestingTimes.epub not found in sample-books")
    
    book1 = test_env["sample_books"] / "book1.epub"
    book2 = test_env["sample_books"] / "book2.epub"
    shutil.copy(source_book, book1)
    shutil.copy(source_book, book2)
    
    # Process both
    transaction1 = Transaction(book1, test_env["site"])
    result1 = transaction1.perform()
    
    transaction2 = Transaction(book2, test_env["site"])
    result2 = transaction2.perform()
    
    # Both should succeed with same hash
    assert isinstance(result1, TransactionSuccess)
    assert isinstance(result2, TransactionSuccess)
    assert result1.hash == result2.hash
    
    # But different original filenames
    assert str(result1.original_filename) == str(book1)
    assert str(result2.original_filename) == str(book2)
    
    # Same output filename (since same content)
    assert result1.filename == result2.filename


def test_text_file_processing(test_env):
    """Test processing a plain text file."""
    # Create a text file
    text_file = test_env["sample_books"] / "readme.txt"
    text_file.write_text("This is a plain text file.\nIt has multiple lines.")
    
    # Run transaction
    transaction = Transaction(text_file, test_env["site"])
    result = transaction.perform()
    
    # Should succeed
    assert isinstance(result, TransactionSuccess)
    assert result.metadata is not None
    assert result.metadata.format == "Text"
    
    # Text files typically don't have author/title
    assert result.metadata.author == ""
    assert result.metadata.title == ""
    
    # Output filename should be based on original name
    assert "readme.txt" in str(result.filename)


def test_transaction_messages_capture(test_env):
    """Test that log messages are properly captured during transaction."""
    # Copy a known book
    source_book = Path("sample-books/InterestingTimes.epub")
    if not source_book.exists():
        pytest.skip("InterestingTimes.epub not found in sample-books")
    
    test_book = test_env["sample_books"] / "test_messages.epub"
    shutil.copy(source_book, test_book)
    
    # Run transaction with debug logging
    import logging
    old_level = logging.getLogger().level
    logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        transaction = Transaction(test_book, test_env["site"])
        result = transaction.perform()
        
        assert isinstance(result, TransactionSuccess)
        # Should have debug messages
        assert len(result.messages) > 0
        
        # Check for expected message patterns
        debug_messages = [msg for msg in result.messages if "DEBUG" in msg]
        assert len(debug_messages) > 0
        
        # Should have processing messages
        assert any("Processing" in msg for msg in result.messages)
        
    finally:
        logging.getLogger().setLevel(old_level)