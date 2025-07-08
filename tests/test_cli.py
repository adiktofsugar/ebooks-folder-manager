"""High-level tests for the efm CLI using ramdisk and snapshots."""

import pytest
import shutil
from pathlib import Path
import yaml
import sys
import uuid

from efm.__main__ import main
from efm.transaction import TransactionError, TransactionResult, TransactionSuccess
from conftest import sanitize_transaction


@pytest.fixture(scope="session")
def ramdisk_root(tmp_path_factory):
    """Create a session-scoped ramdisk directory."""
    return tmp_path_factory.mktemp("efm_cli_test_ramdisk")


@pytest.fixture
def test_env(ramdisk_root):
    """Set up test environment on ramdisk."""
    # Create test directories
    test_dir = ramdisk_root / f"test_{uuid.uuid4().hex[:8]}"
    test_dir.mkdir(exist_ok=True)
    
    sample_books_dir = test_dir / "books"
    sample_books_dir.mkdir()
    
    site_dir = test_dir / "site"
    
    yield {
        "root": test_dir,
        "books": sample_books_dir,
        "site": site_dir,
    }
    
    # Cleanup
    shutil.rmtree(test_dir)


def sanitize_db_for_snapshot(db_data, test_env=None):
    """Sanitize database data for consistent snapshots.
    
    Args:
        db_data: The database data to sanitize
        test_env: The test environment dictionary with keys: root, books, site
    """
    sanitized_data = []
    
    for entry in db_data:
        # Create a TransactionResult from the dict and sanitize it
        result = TransactionResult.from_dict(entry)
        sanitized_entry = sanitize_transaction(result, test_env)
        sanitized_data.append(sanitized_entry)
    
    return sanitized_data


def test_cli_single_file(test_env, monkeypatch, snapshot):
    """Test CLI with a single file."""
    # Copy a known book
    source_book = Path("sample-books/InterestingTimes.epub")
    if not source_book.exists():
        pytest.skip("InterestingTimes.epub not found in sample-books")
    
    test_book = test_env["books"] / "test.epub"
    shutil.copy(source_book, test_book)
    
    # Mock sys.argv
    monkeypatch.setattr(sys, "argv", ["efm", str(test_book), "-o", str(test_env["site"])])
    
    # Run main
    exit_code = main()
    assert exit_code == 0
    
    # Load database
    db_file = test_env["site"] / "db.yaml"
    assert db_file.exists()
    db_data = yaml.safe_load(db_file.read_text())
    
    # Sanitize and snapshot
    sanitized_db = sanitize_db_for_snapshot(db_data, test_env)
    snapshot.assert_match(yaml.dump(sanitized_db, sort_keys=True), "db.yaml")
    
    # Verify messages are included
    assert len(db_data) == 1
    assert "messages" in db_data[0]
    assert isinstance(db_data[0]["messages"], list)


def test_cli_multiple_files_with_duplicates(test_env, monkeypatch, snapshot):
    """Test CLI with multiple files including duplicates."""
    # Copy a book multiple times
    source_book = Path("sample-books/InterestingTimes.epub")
    if not source_book.exists():
        pytest.skip("InterestingTimes.epub not found in sample-books")
    
    book1 = test_env["books"] / "book1.epub"
    book2 = test_env["books"] / "book2.epub"
    book3 = test_env["books"] / "different.epub"
    
    shutil.copy(source_book, book1)
    shutil.copy(source_book, book2)
    
    # Create a different book (corrupted)
    book3.write_text("Not a real EPUB")
    
    # Mock sys.argv with debug logging to get more messages
    monkeypatch.setattr(sys, "argv", [
        "efm", str(book1), str(book2), str(book3), 
        "-o", str(test_env["site"]),
        "--loglevel", "debug"
    ])
    
    # Run main
    exit_code = main()
    assert exit_code == 0
    
    # Load database
    db_file = test_env["site"] / "db.yaml"
    db_data = yaml.safe_load(db_file.read_text())
    
    # Debug: print the database entries BEFORE sanitization
    print(f"\nDatabase contains {len(db_data)} entries (BEFORE sanitization)")
    for i, entry in enumerate(db_data):
        error_val = entry.get("error", None)
        print(f"  Entry {i}: error={error_val} - {entry.get('original_filepath', 'unknown')}")
    
    # Verify we have both success and error entries BEFORE sanitization
    # Note: duplicates are removed from the database, so we only see unique successes
    successes = [d for d in db_data if not d.get("error", False)]
    errors = [d for d in db_data if d.get("error", False)]
    print(f"\nBEFORE sanitization - Successes: {len(successes)}, Errors: {len(errors)}")
    
    # Sanitize and snapshot
    sanitized_db = sanitize_db_for_snapshot(db_data, test_env)
    snapshot.assert_match(yaml.dump(sanitized_db, sort_keys=True), "db.yaml")
    
    # Check AFTER sanitization
    print(f"\nDatabase contains {len(db_data)} entries (AFTER sanitization)")
    for i, entry in enumerate(db_data):
        error_val = entry.get("error", None)
        print(f"  Entry {i}: error={error_val} - {entry.get('original_filepath', 'unknown')}")
    
    # Re-check successes and errors
    successes = [d for d in db_data if not d.get("error", False)]
    errors = [d for d in db_data if d.get("error", False)]
    print(f"\nSuccesses: {len(successes)}")
    print(f"Errors: {len(errors)}")
    for s in successes:
        print(f"  Success: error={s.get('error')}, path={s.get('original_filepath')}")
    assert len(successes) == 1  # Only one unique success (duplicates removed)
    assert len(errors) == 1
    
    # Verify error has messages
    assert len(errors[0]["messages"]) > 0
    assert any("ERROR" in msg for msg in errors[0]["messages"])


def test_cli_text_file_processing(test_env, monkeypatch, snapshot):
    """Test CLI processing various file types."""
    # Create different file types
    (test_env["books"] / "readme.txt").write_text("This is a text file")
    (test_env["books"] / "document.pdf").write_bytes(b"%PDF-1.4 fake pdf content")
    
    # Mock sys.argv
    monkeypatch.setattr(sys, "argv", [
        "efm", str(test_env["books"]), "-o", str(test_env["site"])
    ])
    
    # Run main
    exit_code = main()
    assert exit_code == 0
    
    # Load database
    db_file = test_env["site"] / "db.yaml"
    db_data = yaml.safe_load(db_file.read_text())
    
    # Sanitize and snapshot
    sanitized_db = sanitize_db_for_snapshot(db_data, test_env)
    snapshot.assert_match(yaml.dump(sanitized_db, sort_keys=True), "db.yaml")
    
    # Verify different formats were processed
    formats = {entry["metadata"]["format"] for entry in db_data if "metadata" in entry}
    assert "Text" in formats


def test_cli_with_cached_results(test_env, monkeypatch, snapshot):
    """Test CLI with already cached results."""
    # Copy a book
    source_book = Path("sample-books/InterestingTimes.epub")
    test_book = test_env["books"] / "cached.epub"
    shutil.copy(source_book, test_book)
    
    # First run - process the book
    monkeypatch.setattr(sys, "argv", [
        "efm", str(test_book), "-o", str(test_env["site"]), "--loglevel", "debug"
    ])
    exit_code1 = main()
    assert exit_code1 == 0
    
    # Second run - should use cache
    monkeypatch.setattr(sys, "argv", [
        "efm", str(test_book), "-o", str(test_env["site"]), "--loglevel", "debug"
    ])
    exit_code2 = main()
    assert exit_code2 == 0
    
    # Load database from second run
    db_file = test_env["site"] / "db.yaml"
    db_data = yaml.safe_load(db_file.read_text())
    

    # Sanitize and snapshot
    sanitized_db = sanitize_db_for_snapshot(db_data, test_env)
    snapshot.assert_match(yaml.dump(sanitized_db, sort_keys=True), "db.yaml")

    # Verify cache message is in the logs
    assert len(db_data) == 1
    datum = db_data[0]
    messages = datum["messages"]
    assert any("DEBUG - Skipping" in item for item in messages)



def test_cli_error_with_debug_messages(test_env, monkeypatch, snapshot):
    """Test debug messages with various file types."""
    # Copy real books
    source_epub = Path("sample-books/InterestingTimes.epub")
    source_pdf = Path("sample-books/Emotions.pdf")
    
    if not source_epub.exists():
        pytest.skip("InterestingTimes.epub not found in sample-books")
    if not source_pdf.exists():
        pytest.skip("Emotions.pdf not found in sample-books")
    
    # Set up test files
    test_epub = test_env["books"] / "test.epub"
    test_pdf = test_env["books"] / "test.pdf"
    corrupted_epub = test_env["books"] / "corrupted.epub"
    
    shutil.copy(source_epub, test_epub)
    shutil.copy(source_pdf, test_pdf)
    corrupted_epub.write_bytes(b"PK\x03\x04corrupted data here")
    
    # Run with debug logging
    monkeypatch.setattr(sys, "argv", [
        "efm", str(test_env["books"]), "-o", str(test_env["site"]), "--loglevel", "debug"
    ])
    
    exit_code = main()
    # Should have some failures
    assert exit_code == 1
    
    # Load database
    db_file = test_env["site"] / "db.yaml"
    db_data = yaml.safe_load(db_file.read_text())
    
    # Sanitize and snapshot
    sanitized_db = sanitize_db_for_snapshot(db_data, test_env)
    snapshot.assert_match(yaml.dump(sanitized_db, sort_keys=True), "db.yaml")
    
    db_results = [TransactionResult.from_dict(d) for d in db_data]
    db_results_by_name:dict[str,TransactionResult] = {}
    for db_result in db_results:
        db_results_by_name[str(db_result.original_filepath)] = db_result


    # Verify EPUB processing
    epub_result = db_results_by_name[str(test_epub)]
    assert isinstance(epub_result, TransactionSuccess)
    assert len(epub_result.messages) > 0
    # Should have DEBUG messages about processing
    epub_levels = [msg.split(" - ")[2] for msg in epub_result.messages if len(msg.split(" - ")) >= 3]
    assert "DEBUG" in epub_levels
    
    # Verify PDF processing
    pdf_result = db_results_by_name[str(test_pdf)]
    assert isinstance(pdf_result, TransactionSuccess)
    pdf_levels = [msg.split(" - ")[2] for msg in pdf_result.messages if len(msg.split(" - ")) >= 3]
    assert len(pdf_levels) > 0
    
    # Verify error case
    error_result = db_results_by_name[str(corrupted_epub)]
    assert isinstance(error_result, TransactionError)
    assert len(error_result.messages) >= 2
    error_levels = [msg.split(" - ")[2] for msg in error_result.messages if len(msg.split(" - ")) >= 3]
    assert "ERROR" in error_levels


def test_cli_interesting_times_epub(test_env, monkeypatch, snapshot):
    """Test processing InterestingTimes.epub specifically via CLI."""
    source_book = Path("sample-books/InterestingTimes.epub")
    if not source_book.exists():
        pytest.skip("InterestingTimes.epub not found in sample-books")
    
    test_book = test_env["books"] / "InterestingTimes.epub"
    shutil.copy(source_book, test_book)
    
    monkeypatch.setattr(sys, "argv", ["efm", str(test_book), "-o", str(test_env["site"])])
    exit_code = main()
    assert exit_code == 0
    
    db_file = test_env["site"] / "db.yaml"
    db_data = yaml.safe_load(db_file.read_text())
    
    assert len(db_data) == 1
    result = TransactionResult.from_dict(db_data[0])
    
    assert isinstance(result, TransactionSuccess)
    assert result.metadata is not None
    assert result.metadata.title == "Interesting Times"
    assert result.metadata.author == "Terry Pratchett"
    assert result.metadata.format == "EPUB"
    assert result.filename == Path("books/Terry Pratchett-Interesting Times.epub")
    
    output_file = test_env["site"] / result.filename
    assert output_file.exists()
    
    cache_file = test_env["site"] / "_cache" / f"{result.hash}.yaml"
    assert cache_file.exists()


def test_cli_emotions_pdf(test_env, monkeypatch, snapshot):
    """Test processing Emotions.pdf specifically via CLI."""
    source_book = Path("sample-books/Emotions.pdf")
    if not source_book.exists():
        pytest.skip("Emotions.pdf not found in sample-books")
    
    test_book = test_env["books"] / "Emotions.pdf"
    shutil.copy(source_book, test_book)
    
    monkeypatch.setattr(sys, "argv", ["efm", str(test_book), "-o", str(test_env["site"])])
    exit_code = main()
    
    assert exit_code in (0, 1)
    
    db_file = test_env["site"] / "db.yaml"
    db_data = yaml.safe_load(db_file.read_text())
    
    assert len(db_data) == 1
    result = TransactionResult.from_dict(db_data[0])
    
    assert isinstance(result, (TransactionSuccess, TransactionError))
    
    if isinstance(result, TransactionSuccess):
        assert result.metadata is not None
        assert result.metadata.format in ["PDF", "PDF document"]
        if result.metadata.title and result.metadata.author:
            assert result.metadata.author in str(result.filename)


def test_cli_corrupted_epub_handling(test_env, monkeypatch, snapshot):
    """Test CLI handling of a corrupted EPUB file."""
    bad_epub = test_env["books"] / "corrupted.epub"
    bad_epub.write_text("This is not a valid EPUB file!")
    
    monkeypatch.setattr(sys, "argv", ["efm", str(bad_epub), "-o", str(test_env["site"])])
    exit_code = main()
    
    assert exit_code == 1
    
    db_file = test_env["site"] / "db.yaml"
    db_data = yaml.safe_load(db_file.read_text())
    
    assert len(db_data) == 1
    result = TransactionResult.from_dict(db_data[0])
    
    assert isinstance(result, TransactionError)
    assert "corrupted.epub" in str(result.original_filepath)
    assert result.error_message is not None
    assert "metadata" in result.error_message.lower() or "open" in result.error_message.lower()
    assert len(result.messages) >= 2
    
    cache_files = list((test_env["site"] / "_cache").glob("*.yaml"))
    assert len(cache_files) == 1
    
    cache_data = yaml.safe_load(cache_files[0].read_text())
    assert cache_data["error"] is True


def test_cli_duplicate_book_processing(test_env, monkeypatch, snapshot):
    """Test CLI processing the same file twice uses cache."""
    source_book = Path("sample-books/InterestingTimes.epub")
    if not source_book.exists():
        pytest.skip("InterestingTimes.epub not found in sample-books")
    
    test_book = test_env["books"] / "test.epub"
    shutil.copy(source_book, test_book)
    
    monkeypatch.setattr(sys, "argv", ["efm", str(test_book), "-o", str(test_env["site"]), "--loglevel", "debug"])
    exit_code1 = main()
    assert exit_code1 == 0
    
    db_file = test_env["site"] / "db.yaml"
    db_data1 = yaml.safe_load(db_file.read_text())
    result1 = TransactionResult.from_dict(db_data1[0])
    assert isinstance(result1, TransactionSuccess)
    
    monkeypatch.setattr(sys, "argv", ["efm", str(test_book), "-o", str(test_env["site"]), "--loglevel", "debug"])
    exit_code2 = main()
    assert exit_code2 == 0
    
    db_data2 = yaml.safe_load(db_file.read_text())
    result2 = TransactionResult.from_dict(db_data2[0])
    
    assert isinstance(result2, TransactionSuccess)
    assert result2.hash == result1.hash
    assert result2.filename == result1.filename
    
    assert any("Skipping" in msg and "already been processed" in msg for msg in result2.messages)


def test_cli_duplicate_content_different_filenames(test_env, monkeypatch, snapshot):
    """Test CLI processing identical content with different filenames."""
    source_book = Path("sample-books/InterestingTimes.epub")
    if not source_book.exists():
        pytest.skip("InterestingTimes.epub not found in sample-books")
    
    book1 = test_env["books"] / "book1.epub"
    book2 = test_env["books"] / "book2.epub"
    shutil.copy(source_book, book1)
    shutil.copy(source_book, book2)
    
    monkeypatch.setattr(sys, "argv", ["efm", str(book1), str(book2), "-o", str(test_env["site"])])
    exit_code = main()
    assert exit_code == 0
    
    db_file = test_env["site"] / "db.yaml"
    db_data = yaml.safe_load(db_file.read_text())
    
    assert len(db_data) == 1
    result = TransactionResult.from_dict(db_data[0])
    
    assert isinstance(result, TransactionSuccess)
    assert str(result.original_filepath) in (str(book1), str(book2))
    
    cache_files = list((test_env["site"] / "_cache").glob("*.yaml"))
    assert len(cache_files) == 1


def test_cli_plain_text_file(test_env, monkeypatch, snapshot):
    """Test CLI processing a plain text file."""
    text_file = test_env["books"] / "readme.txt"
    text_file.write_text("This is a plain text file.\nIt has multiple lines.")
    
    monkeypatch.setattr(sys, "argv", ["efm", str(text_file), "-o", str(test_env["site"])])
    exit_code = main()
    assert exit_code == 0
    
    db_file = test_env["site"] / "db.yaml"
    db_data = yaml.safe_load(db_file.read_text())
    
    assert len(db_data) == 1
    result = TransactionResult.from_dict(db_data[0])
    
    assert isinstance(result, TransactionSuccess)
    assert result.metadata is not None
    assert result.metadata.format == "Text"
    
    assert result.metadata.author == ""
    assert result.metadata.title == ""
    
    assert "readme.txt" in str(result.filename)


def test_cli_debug_message_capture(test_env, monkeypatch, snapshot):
    """Test that CLI properly captures debug messages during processing."""
    source_book = Path("sample-books/InterestingTimes.epub")
    if not source_book.exists():
        pytest.skip("InterestingTimes.epub not found in sample-books")
    
    test_book = test_env["books"] / "test_messages.epub"
    shutil.copy(source_book, test_book)
    
    monkeypatch.setattr(sys, "argv", [
        "efm", str(test_book), "-o", str(test_env["site"]), "--loglevel", "debug"
    ])
    exit_code = main()
    assert exit_code == 0
    
    db_file = test_env["site"] / "db.yaml"
    db_data = yaml.safe_load(db_file.read_text())
    
    assert len(db_data) == 1
    result = TransactionResult.from_dict(db_data[0])
    
    assert isinstance(result, TransactionSuccess)
    assert len(result.messages) > 0
    
    debug_messages = [msg for msg in result.messages if "DEBUG" in msg]
    assert len(debug_messages) > 0
    
    assert any("Processing" in msg for msg in result.messages)