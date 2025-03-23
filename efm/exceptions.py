class BookError(Exception):
    """Base exception class for all Book-related errors."""

    def __init__(self, file_path: str, message=None):
        super().__init__(
            f"Error with book: {file_path}{f' - {message}' if message else ''}"
        )


class GetMetadataError(BookError):
    """Error related to book metadata operations."""

    def __init__(self, file_path: str, message=None, original_error=None):
        super().__init__(
            file_path,
            f"Error reading metadata from {file_path}{f' - {message}' if message else ''}{f' - {original_error}' if original_error else ''}",
        )


class DeDrmError(Exception):
    """Base exception for DeDRM-related errors."""

    pass


class RemoveDrmError(DeDrmError):
    """Error related to DRM operations."""

    def __init__(self, file_path: str, message=None):
        super().__init__(
            f"Error removing DRM from {file_path}{f' - {message}' if message else ''}",
        )


class DetectEncryptionError(RemoveDrmError):
    """Error related to encryption/decryption operations."""

    def __init__(self, file_path: str, message=None):
        super().__init__(
            file_path,
            f"Couldn't detect DRM type{f' - {message}' if message else ''}",
        )


class MissingDrmKeyFileError(RemoveDrmError):
    """Error when a required key file is missing."""

    def __init__(self, file_path: str, encryption_type: str, message=None):
        super().__init__(
            file_path,
            f"Missing required key for {encryption_type}, add to your config file{f' - {message}' if message else ''}",
        )


class UnsupportedEncryptionError(RemoveDrmError):
    """Error when the encryption type is not supported."""

    def __init__(self, file_path: str, encryption_type: str, message=None):
        super().__init__(
            file_path,
            f"{encryption_type} encryption is not supported{f' - {message}' if message else ''}",
        )
