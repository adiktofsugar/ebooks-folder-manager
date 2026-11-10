"""Per-operation working directories that survive failures, for debugging."""

import logging
import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger(__name__)


@contextmanager
def scratch_dir(label: str, root: Path | None = None) -> Iterator[Path]:
    """A fresh directory, deleted on success and kept (and logged) if the body raises."""
    # The system temp dir by default, so kept dirs from repeated failures get cleaned up eventually.
    path = Path(tempfile.mkdtemp(prefix=f"efm-{label}-", dir=root))
    try:
        yield path
    except BaseException:
        logger.error(f"Kept scratch directory {path}")
        raise
    shutil.rmtree(path, ignore_errors=True)
