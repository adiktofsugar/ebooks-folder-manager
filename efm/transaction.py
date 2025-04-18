import logging
import os
import shutil
import sys
import tempfile
import traceback
from typing import Literal

from efm.action import ALL_ACTIONS, BaseAction
from efm.metadata import Metadata
from efm.config import Config, get_closest_config, valid_actions

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
        temp_dirpath = tempfile.mkdtemp(prefix=self.filename)
        try:
            logger.debug(
                f"Processing {self.original_filepath} with actions {self.action_ids}"
            )
            action_ids_run = []
            for action_id in valid_actions:
                if action_id == "none":
                    continue
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
                        action_ids_run.append(action_id)
                        old_ext = os.path.splitext(self.current_filepath)[1]
                        after_ext = os.path.splitext(after_filepath)[1]
                        old_filepath = os.path.join(
                            temp_dirpath, f"before_{action_id}{old_ext}"
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
                        elif after_ext != old_ext:
                            self.filename = (
                                f"{os.path.splitext(self.filename)[0]}{after_ext}"
                            )
                            logger.debug(f"Changed extension to {after_ext}")

                        self.current_filepath = os.path.join(
                            temp_dirpath, self.filename
                        )
                        logger.debug(
                            f"Moving {after_filepath} to {self.current_filepath}"
                        )
                        shutil.move(after_filepath, self.current_filepath)

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
                logger.info(
                    f"Successfully executed {', '.join(action_ids_run)} for {new_filepath}. Intermediate files are in {temp_dirpath}. {self.original_filepath} has been backed up to {bak_filepath}."
                )
            else:
                logger.info(f"Skipped all actions for {self.original_filepath}.")

        except:
            traceback.print_exc()
            logger.error(
                f"Failed to complete all actions for {self.original_filepath}. Intermediate files are in {temp_dirpath}"
            )
            raise


def get_action_from_str(
    action_id: str,
    config: Config | None,
    metadata: Metadata | None | Literal[False],
    filepath: str,
    temp_dirpath: str,
    dry: bool,
) -> BaseAction:
    for actionKlass in ALL_ACTIONS:
        if actionKlass.id() == action_id:
            return actionKlass(config, metadata, filepath, temp_dirpath, dry)
    raise ValueError(f"Unknown action {action_id}")
