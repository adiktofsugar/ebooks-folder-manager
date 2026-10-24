from pathlib import Path
from typing import override


class BookError(Exception):
    """Base exception class for all Book-related errors."""

    def __init__(self, filepath:Path, message=None):
        super().__init__(
            f"Error with book: {filepath}{f' - {message}' if message else ''}"
        )


class GetMetadataError(BookError):
    """Error related to book metadata operations."""

    @override
    def __init__(self, filepath:Path, message=None, original_error=None):
        super().__init__(
            filepath,
            f"Couldn't get metadata{f' - {message}' if message else ''}{f' - {original_error}' if original_error else ''}",
        )


class RemoveDrmError(BookError):
    """Error related to DRM operations."""

    @override
    def __init__(self, filepath:Path, message=None, original_error=None):
        super().__init__(
            filepath,
            f"Couldn't remove DRM{f' - {message}' if message else ''}{f' - {original_error}' if original_error else ''}",
        )


class ZipFixError(RemoveDrmError):
    """Error related to fixing a zip file."""

    @override
    def __init__(self, filepath:Path):
        super().__init__(
            filepath,
            "Couldn't fix zip file",
        )


class DetectEncryptionError(RemoveDrmError):
    """Error related to encryption/decryption operations."""

    @override
    def __init__(self, filepath:Path, message=None):
        super().__init__(
            filepath,
            f"Couldn't detect DRM type{f' - {message}' if message else ''}",
        )


class MissingDrmKeyFileError(RemoveDrmError):
    """Error when a required key file is missing."""

    @override
    def __init__(self, filepath:Path, encryption_type: str, message=None):
        super().__init__(
            filepath,
            f"Missing required key for {encryption_type}, add to your config file{f' - {message}' if message else ''}",
        )


class UnsupportedEncryptionError(RemoveDrmError):
    """Error when the encryption type is not supported."""

    @override
    def __init__(self, filepath:Path, encryption_type: str, message=None):
        super().__init__(
            filepath,
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

    def __init__(self, filepath: Path, original_error: Exception):
        super().__init__(f"Invalid store file {filepath} - {original_error}")
