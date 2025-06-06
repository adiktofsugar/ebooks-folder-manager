import hashlib
import logging
from pathlib import Path
import shutil
import tempfile
import traceback

import yaml
from efm.action import ALL_ACTIONS
from efm.config import Config, get_closest_config
from efm.metadata import get_metadata

logger = logging.getLogger(__name__)


class Transaction:
    config: Config | None
    original_filepath: Path
    site_dirpath: Path

    def __init__(
        self,
        original_filepath: Path,
        site_dir: Path,
    ):
        self.config = get_closest_config(original_filepath.parent)
        self.original_filepath = original_filepath
        self.site_dirpath = site_dir

    def perform(self) -> Path:
        with open(self.original_filepath, "rb") as f:
            hash = hashlib.blake2b(f.read(), digest_size=20).hexdigest()
        metadata_output_dirpath = self.site_dirpath / "metadata"
        metadata_output_filepath = metadata_output_dirpath / f"{hash}.yaml"
        if metadata_output_filepath.exists():
            logger.info(
                f"Skipping {self.original_filepath} because metadata has already been processed."
            )
            return metadata_output_filepath
        books_output_dirpath = self.site_dirpath / "books"
        temp_dirpath = Path(tempfile.mkdtemp(prefix=hash))
        filepath = Path(shutil.copy(self.original_filepath, temp_dirpath))
        metadata = get_metadata(filepath)
        try:
            logger.debug(f"Processing {self.original_filepath} in {temp_dirpath}")
            for ActionKlass in ALL_ACTIONS:
                action = ActionKlass(
                    self.config,
                    metadata,
                    filepath,
                    temp_dirpath,
                )

                logger.debug(f"Performing action {action.id} on {filepath}")
                filepath = action.perform()
                metadata = action.metadata  # sometimes actions update metadata

            output_filename = f"{self.original_filepath.stem}{filepath.suffix}"
            if metadata:
                output_filename = f"{metadata.author}-{metadata.title}{filepath.suffix}"

            books_output_dirpath.mkdir(parents=True, exist_ok=True)
            metadata_output_dirpath.mkdir(parents=True, exist_ok=True)
            metadata_output_filepath.write_text(
                yaml.dump(
                    dict(
                        filename=output_filename,
                        author=metadata.author if metadata else None,
                        title=metadata.title if metadata else None,
                    )
                )
            )
            shutil.copy(filepath, books_output_dirpath / output_filename)
            shutil.rmtree(temp_dirpath)
            logger.info(
                f"Finished processing {self.original_filepath}. Output file is {self.site_dirpath / f'{hash}{filepath.suffix}'}"
            )
            return metadata_output_filepath

        except:
            traceback.print_exc()
            logger.error(
                f"Failed to process {self.original_filepath}. Intermediate files are in {temp_dirpath}"
            )
            raise
