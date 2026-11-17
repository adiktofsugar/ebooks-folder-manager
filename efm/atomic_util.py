"""Writes that either fully happen or leave the destination untouched (temp file + rename)."""

import json
import os
import tempfile
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO


@contextmanager
def open_atomic(file: Path) -> Generator[BinaryIO]:
    """Write to a temp file next to `file`, renamed over it only if the block succeeds."""
    fd, tmp_filepath = tempfile.mkstemp(dir=file.parent, prefix=".tmp-")
    try:
        with os.fdopen(fd, "wb") as f:
            yield f
        os.replace(tmp_filepath, file)
    except BaseException:
        Path(tmp_filepath).unlink(missing_ok=True)
        raise


def write_bytes_atomic(file: Path, data: bytes) -> None:
    with open_atomic(file) as f:
        f.write(data)


def write_text_atomic(file: Path, text: str) -> None:
    write_bytes_atomic(file, text.encode())


def write_json_atomic(file: Path, data: object) -> None:
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    write_text_atomic(file, text)
