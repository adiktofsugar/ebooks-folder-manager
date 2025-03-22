import logging
import os
import shutil
import tempfile

from efm.action import (
    BaseAction,
    DeDrmAction,
    PrintAction,
    ReformatPdfAction,
    RenameAction,
)
from efm.metadata import Metadata
from efm.config import Config, get_closest_config

logger = logging.getLogger(__name__)


class Transaction:
    def __init__(
        self,
        original_filepath: str,
        action_ids: list[str] | None,
        dry: bool,
    ):
        self.config = get_closest_config(os.path.dirname(original_filepath))
        self.metadata = None  # we save metadata so each action can have / modify it
        self.filename = os.path.basename(original_filepath)
        self.original_filepath = original_filepath
        self.current_filepath = original_filepath
        self.action_ids = (
            action_ids
            if action_ids is not None
            else self.config.actions
            if self.config is not None and self.config.actions is not None
            else ["print"]
        )
        self.dry = dry

    def perform(self):
        try:
            filename, ext = os.path.splitext(self.filename)
            temp_dirpath = tempfile.mkdtemp(prefix=self.filename)
            # order matters. drm has to come first for any metadata to work
            for action_id in ["drm", "pdf", "rename", "print"]:
                if action_id in self.action_ids:
                    action = get_action_from_str(
                        action_id,
                        self.config,
                        self.metadata,
                        self.current_filepath,
                        temp_dirpath,
                        self.dry,
                    )
                    logger.debug(
                        f"Performing action {action_id} on {self.current_filepath}"
                    )
                    after_filepath = action.perform()
                    logger.debug(
                        f"Action {action_id} succeeded and returned filepath {after_filepath}"
                    )
                    # save metadata for next action
                    self.metadata = action.metadata
                    if after_filepath != self.current_filepath:
                        old_filepath = os.path.join(
                            temp_dirpath, f"before_{action_id}{ext}"
                        )
                        if self.current_filepath == self.original_filepath:
                            logger.debug(
                                f"Copying {self.current_filepath} to {old_filepath}"
                            )
                            # don't delete the original file
                            shutil.copy(self.current_filepath, old_filepath)
                        else:
                            logger.debug(
                                f"Moving {self.current_filepath} to {old_filepath}"
                            )
                            shutil.move(self.current_filepath, old_filepath)

                        if action_id == "rename":
                            self.filename = os.path.basename(after_filepath)
                            logger.debug(f"Renamed to {self.filename}")

                        self.current_filepath = os.path.join(
                            temp_dirpath, self.filename
                        )
                        logger.debug(
                            f"Moving {after_filepath} to {self.current_filepath}"
                        )
                        shutil.move(after_filepath, self.current_filepath)

            logger.info(
                f"All actions succeeded for {self.original_filepath}. Intermediate files are in {temp_dirpath}."
            )
            if self.current_filepath != self.original_filepath:
                bak_filepath = f"{self.original_filepath}.bak"
                i = 0
                while os.path.exists(bak_filepath):
                    i += 1
                    bak_filepath = f"{self.original_filepath}.{i}.bak"
                logger.debug(f"Moving {self.original_filepath} to {bak_filepath}")
                shutil.move(self.original_filepath, bak_filepath)
                new_filepath = os.path.join(
                    os.path.dirname(self.original_filepath), self.filename
                )
                logger.debug(f"Moving {self.current_filepath} to {new_filepath}")
                shutil.copy(self.current_filepath, new_filepath)

        except:
            logger.error(
                f"Failed to complete all actions for {self.original_filepath}. Intermediate files are in {temp_dirpath}"
            )
            raise


def get_action_from_str(
    action: str,
    config: Config,
    metadata: Metadata,
    filepath: str,
    temp_dirpath: str,
    dry: bool,
) -> BaseAction:
    match action:
        case "drm":
            return DeDrmAction(config, metadata, filepath, temp_dirpath, dry)
        case "rename":
            return RenameAction(config, metadata, filepath, temp_dirpath, dry)
        case "print":
            return PrintAction(config, metadata, filepath, temp_dirpath, dry)
        case "pdf":
            return ReformatPdfAction(config, metadata, filepath, temp_dirpath, dry)
        case _:
            raise ValueError(f"Unknown action {action}")
