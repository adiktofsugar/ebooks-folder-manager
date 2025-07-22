#!/usr/bin/env python
"""Test that messages in db.yaml are properly isolated to their respective books."""

import tempfile
import shutil
from pathlib import Path
import yaml


def test_db_yaml_message_isolation():
    """Test that each book in db.yaml only contains messages related to itself."""
    # Create a sample db.yaml with the problematic structure
    test_db = [
        {
            "originalFilename": "book1.epub",
            "messages": [
                "Processing book1.epub",
                "Skipping book1.epub because metadata has already been processed"
            ]
        },
        {
            "originalFilename": "book2.pdf", 
            "messages": [
                "Processing book2.pdf",
                "Skipping book2.pdf because metadata has already been processed"
            ]
        },
        {
            "originalFilename": "book3.mobi",
            "messages": [
                "Processing book3.mobi",
                "Skipping book3.mobi because metadata has already been processed"
            ]
        }
    ]
    
    # Validate that messages are properly isolated
    for book_entry in test_db:
        filename = book_entry["originalFilename"]
        messages = book_entry.get("messages", [])
        
        # Check each message belongs to this book
        for message in messages:
            # Skip empty messages
            if not message:
                continue
                
            # Message should mention this book's filename
            if "Processing" in message or "Skipping" in message:
                assert filename in message, \
                    f"Book '{filename}' has message that doesn't mention it: '{message}'"
        
        # Ensure no messages from other books
        other_filenames = [b["originalFilename"] for b in test_db if b["originalFilename"] != filename]
        for other_filename in other_filenames:
            for message in messages:
                assert other_filename not in message, \
                    f"Book '{filename}' has message from another book '{other_filename}': '{message}'"


def test_detect_shared_messages():
    """Test that detects when messages are incorrectly shared across books."""
    # This represents the buggy behavior where all books have the same messages
    buggy_db = [
        {
            "originalFilename": "book1.epub",
            "messages": [
                "Processing book1.epub", 
                "Processing book2.pdf",
                "Processing book3.mobi",
                "Skipping book1.epub because metadata has already been processed",
                "Skipping book2.pdf because metadata has already been processed",
                "Skipping book3.mobi because metadata has already been processed"
            ]
        },
        {
            "originalFilename": "book2.pdf",
            "messages": [
                "Processing book1.epub",
                "Processing book2.pdf", 
                "Processing book3.mobi",
                "Skipping book1.epub because metadata has already been processed",
                "Skipping book2.pdf because metadata has already been processed",
                "Skipping book3.mobi because metadata has already been processed"
            ]
        },
        {
            "originalFilename": "book3.mobi",
            "messages": [
                "Processing book1.epub",
                "Processing book2.pdf",
                "Processing book3.mobi",
                "Skipping book1.epub because metadata has already been processed", 
                "Skipping book2.pdf because metadata has already been processed",
                "Skipping book3.mobi because metadata has already been processed"
            ]
        }
    ]
    
    # This should fail validation
    errors_found = []
    
    for book_entry in buggy_db:
        filename = book_entry["originalFilename"]
        messages = book_entry.get("messages", [])
        
        # Check for messages from other books
        other_filenames = [b["originalFilename"] for b in buggy_db if b["originalFilename"] != filename]
        for other_filename in other_filenames:
            for message in messages:
                if other_filename in message:
                    errors_found.append(
                        f"Book '{filename}' has message from another book '{other_filename}': '{message}'"
                    )
    
    # We expect to find errors in the buggy db
    assert len(errors_found) > 0, "Failed to detect shared messages bug"
    
    # Verify we found the expected number of cross-contamination errors
    # Each book has 4 messages from other books (2 Processing + 2 Skipping)
    # 3 books × 4 wrong messages = 12 errors
    assert len(errors_found) == 12, f"Expected 12 errors, found {len(errors_found)}"


def check_db_yaml_for_shared_messages(db_path: str) -> list[str]:
    """
    Utility function to check an actual db.yaml file for shared messages.
    Returns a list of error messages if issues are found.
    """
    with open(db_path) as f:
        db = yaml.safe_load(f)
    
    errors: list[str] = []
    
    # Get all unique filenames
    all_filenames = [entry.get("originalFilename", "") for entry in db]
    
    for book_entry in db:
        filename = book_entry.get("originalFilename", "")
        messages = book_entry.get("messages", [])
        
        # Check for messages from other books
        other_filenames = [f for f in all_filenames if f != filename and f]
        
        for other_filename in other_filenames:
            for message in messages:
                if other_filename in message:
                    errors.append(
                        f"Book '{filename}' has message from another book '{other_filename}': '{message}'"
                    )
    
    return errors


if __name__ == "__main__":
    # Can be run directly to check a real db.yaml file
    import sys
    if len(sys.argv) > 1:
        db_path = Path(sys.argv[1])
        if db_path.exists():
            errors = check_db_yaml_for_shared_messages(db_path)
            if errors:
                print(f"Found {len(errors)} message isolation issues:")
                for error in errors[:10]:  # Show first 10 errors
                    print(f"  - {error}")
                if len(errors) > 10:
                    print(f"  ... and {len(errors) - 10} more")
            else:
                print("No message isolation issues found!")
        else:
            print(f"File not found: {db_path}")