from pathlib import Path


class BookError(Exception):
    """Base exception class for all Book-related errors."""

    def __init__(self, book_file: Path, message=None):
        super().__init__(
            f"Error with book: {book_file}{f' - {message}' if message else ''}"
        )


class GetMetadataError(BookError):
    """Error related to book metadata operations."""

    def __init__(self, book_file: Path, message=None, original_error=None):
        super().__init__(
            book_file,
            f"Couldn't get metadata{f' - {message}' if message else ''}{f' - {original_error}' if original_error else ''}",
        )


class RemoveDrmError(BookError):
    """Error related to DRM operations."""

    def __init__(self, book_file: Path, message=None, original_error=None):
        super().__init__(
            book_file,
            f"Couldn't remove DRM{f' - {message}' if message else ''}{f' - {original_error}' if original_error else ''}",
        )


class ZipFixError(RemoveDrmError):
    """Error related to fixing a zip file."""

    def __init__(self, book_file: Path):
        super().__init__(
            book_file,
            "Couldn't fix zip file",
        )


class DetectEncryptionError(RemoveDrmError):
    """Error related to encryption/decryption operations."""

    def __init__(self, book_file: Path, message=None):
        super().__init__(
            book_file,
            f"Couldn't detect DRM type{f' - {message}' if message else ''}",
        )


class MissingDrmKeyFileError(RemoveDrmError):
    """Error when a required key file is missing."""

    def __init__(self, book_file: Path, encryption_type: str, message=None):
        super().__init__(
            book_file,
            f"Missing required key for {encryption_type}, add to your config file{f' - {message}' if message else ''}",
        )


class UnsupportedEncryptionError(RemoveDrmError):
    """Error when the encryption type is not supported."""

    def __init__(self, book_file: Path, encryption_type: str, message=None):
        super().__init__(
            book_file,
            f"{encryption_type} encryption is not supported{f' - {message}' if message else ''}",
        )


class UnsupportedSchemaError(Exception):
    """A stored record's schema_version is unknown to this efm (likely written by a newer one)."""

    def __init__(self, version: int, known: list[int]):
        super().__init__(
            f"Unsupported schema_version {version} (known: {', '.join(map(str, known))})"
        )
        self.version: int = version


class InvalidStoreEntryError(Exception):
    """A store file exists but can't be read as its model."""

    def __init__(self, file: Path, original_error: Exception):
        super().__init__(f"Invalid store file {file} - {original_error}")


class ContentError(Exception):
    """A book's stored content is missing, or doesn't reassemble to its hash."""


class TemplateError(Exception):
    """A rename template that can't be parsed or evaluated."""


class MissingValueError(TemplateError):
    """A template placeholder needs metadata the book doesn't have."""

    def __init__(self, expr: str, missing: list[str]):
        names = ", ".join(missing) if missing else "value"
        super().__init__(f"{{{expr}}}: missing {names}")
        self.missing: list[str] = missing
