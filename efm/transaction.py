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
from efm.config import Config

logger = logging.getLogger(__name__)


class Transaction:
    def __init__(
        self,
        original_filepath: str,
        action_ids: list[str] | None,
        config: Config | None,
        dry: bool,
    ):
        self.original_filepath = original_filepath
        self.current_filepath = original_filepath
        self.config = config
        self.action_ids = (
            action_ids
            if action_ids is not None
            else config.actions
            if config.actions is not None
            else ["print"]
        )
        self.dry = dry

    def perform(self):
        try:
            filepath, ext = os.path.splitext(self.original_filepath)
            filename = os.path.basename(filepath)
            temp_dirpath = tempfile.mkdtemp(prefix=filename)
            # order matters. drm has to come first for any metadata to work
            for action_id in ["drm", "pdf", "rename", "print"]:
                if action_id in self.action_ids:
                    action = get_action_from_str(
                        action_id, self.current_filepath, temp_dirpath, self.dry
                    )
                    logger.debug(
                        f"Performing action {action_id} on {self.current_filepath}"
                    )
                    after_filepath = action.perform()
                    logger.debug(
                        f"Action {action_id} succeeded and returned filepath {after_filepath}"
                    )
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

                        self.current_filepath = os.path.join(
                            temp_dirpath, f"{filename}{ext}"
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
                logger.debug(
                    f"Moving {self.current_filepath} to {self.original_filepath}"
                )
                shutil.copy(self.current_filepath, self.original_filepath)

        except:
            logger.error(
                f"Failed to complete all actions for {self.original_filepath}. Intermediate files are in {temp_dirpath}"
            )
            raise


def get_action_from_str(
    action: str, filepath: str, temp_dirpath: str, dry: bool
) -> BaseAction:
    match action:
        case "drm":
            return DeDrmAction(filepath, temp_dirpath, dry)
        case "rename":
            return RenameAction(filepath, temp_dirpath, dry)
        case "print":
            return PrintAction(filepath, temp_dirpath, dry)
        case "pdf":
            return ReformatPdfAction(filepath, temp_dirpath, dry)
        case _:
            raise ValueError(f"Unknown action {action}")
