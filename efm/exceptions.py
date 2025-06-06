from pathlib import Path


class BookError(Exception):
    """Base exception class for all Book-related errors."""

    def __init__(self, filepath:Path, message=None):
        super().__init__(
            f"Error with book: {filepath}{f' - {message}' if message else ''}"
        )


class GetMetadataError(BookError):
    """Error related to book metadata operations."""

    def __init__(self, filepath:Path, message=None, original_error=None):
        super().__init__(
            filepath,
            f"Couldn't get metadata{f' - {message}' if message else ''}{f' - {original_error}' if original_error else ''}",
        )


class RemoveDrmError(BookError):
    """Error related to DRM operations."""

    def __init__(self, filepath:Path, message=None, original_error=None):
        super().__init__(
            filepath,
            f"Couldn't remove DRM{f' - {message}' if message else ''}{f' - {original_error}' if original_error else ''}",
        )


class ZipFixError(RemoveDrmError):
    """Error related to fixing a zip file."""

    def __init__(self, filepath:Path):
        super().__init__(
            filepath,
            "Couldn't fix zip file",
        )


class DetectEncryptionError(RemoveDrmError):
    """Error related to encryption/decryption operations."""

    def __init__(self, filepath:Path, message=None):
        super().__init__(
            filepath,
            f"Couldn't detect DRM type{f' - {message}' if message else ''}",
        )


class MissingDrmKeyFileError(RemoveDrmError):
    """Error when a required key file is missing."""

    def __init__(self, filepath:Path, encryption_type: str, message=None):
        super().__init__(
            filepath,
            f"Missing required key for {encryption_type}, add to your config file{f' - {message}' if message else ''}",
        )


class UnsupportedEncryptionError(RemoveDrmError):
    """Error when the encryption type is not supported."""

    def __init__(self, filepath:Path, encryption_type: str, message=None):
        super().__init__(
            filepath,
            f"{encryption_type} encryption is not supported{f' - {message}' if message else ''}",
        )
