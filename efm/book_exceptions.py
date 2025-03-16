# Base exception class for all Book-related errors
class BookError(Exception):
    """Base exception class for all Book-related errors."""

    def __init__(self, book, message=None):
        from efm.book import Book

        self.book = book
        self.file_path = book.file if book else "Unknown file"
        self.message = message or f"Error with book: {self.file_path}"
        super().__init__(self.message)


# Specific exception types
class GetMetadataError(BookError):
    """Error related to book metadata operations."""

    def __init__(self, book, message=None, original_error=None):
        self.original_error = original_error
        message = message or f"Error reading metadata from {book.file}"
        if original_error:
            message += f": {original_error}"
        super().__init__(book, message)


class RemoveDrmError(BookError):
    """Error related to DRM operations."""

    def __init__(self, book, message=None):
        message = message or f"Error removing DRM from {book.file}"
        super().__init__(book, message)


class UnsupportedFormatError(BookError):
    """Error related to unsupported file formats."""

    def __init__(self, book, format_type=None, message=None):
        self.format_type = format_type
        message = (
            message or f"Unsupported format {format_type or 'unknown'} for {book.file}"
        )
        super().__init__(book, message)


class DetectEncryptionError(RemoveDrmError):
    """Error related to encryption/decryption operations."""

    def __init__(self, book, message=None):
        message = message or f"Cannot remove DRM from {book.file} because of an error"
        super().__init__(book, message)


class MissingDrmKeyFileError(RemoveDrmError):
    """Error when a required key file is missing."""

    def __init__(self, book, key_type=None, message=None):
        self.key_type = key_type
        message = (
            message
            or f"Cannot remove DRM from {book.file} because no {key_type or ''} key file was provided"
        )
        super().__init__(book, message)


class UnsupportedEncryptionError(RemoveDrmError):
    """Error when the encryption type is not supported."""

    def __init__(self, book, encryption_type=None, message=None):
        self.encryption_type = encryption_type
        message = (
            message
            or f"Cannot remove DRM from {book.file} because it's encrypted with {encryption_type or 'unsupported encryption'}"
        )
        super().__init__(book, message)
