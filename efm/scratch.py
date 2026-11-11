"""Per-operation working directories that survive failures, for debugging."""

import logging
import shutil
import tempfile
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger(__name__)


@contextmanager
def scratch_dir(label: str, root_dir: Path | None = None) -> Generator[Path]:
    """A fresh directory, deleted on success and kept (and logged) if the body raises."""
    # The system temp dir by default, so kept dirs from repeated failures get cleaned up eventually.
    dir = Path(tempfile.mkdtemp(prefix=f"efm-{label}-", dir=root_dir))
    try:
        yield dir
    except BaseException:
        logger.error(f"Kept scratch directory {dir}")
        raise
    shutil.rmtree(dir, ignore_errors=True)
