"""Fulfilling Adobe .acsm tokens into the books they stand for."""

import logging
from pathlib import Path

from efm.config import Config
from efm.exceptions import BookError

logger = logging.getLogger(__name__)


def fulfill(acsm: Path, out_dir: Path, config: Config | None) -> Path:
    """Download the book `acsm` points to into `out_dir`. Needs adobe_user/adobe_password."""
    if not config or not config.adobe_user or not config.adobe_password:
        raise BookError(
            acsm,
            message="Can't fulfill ACSM - add adobe_user and adobe_password to your config file",
        )

    # Imported here because importing adl creates and loads its data dir.
    from adl.epub_get import get_ebook

    from adl import AdeptError, GetEbookException

    try:
        _use_account(acsm, config.adobe_user, config.adobe_password)
        # get_ebook logs and swallows most of its own errors, so None is also a failure.
        downloaded = get_ebook(str(acsm), str(out_dir))
    except (AdeptError, GetEbookException) as e:
        # adl's messages already say what to do, so pass them through as-is.
        raise BookError(acsm, message=str(e)) from e
    if downloaded is None:
        raise BookError(acsm, message="Fulfillment failed, see log above")
    logger.debug(f"Fulfilled {acsm} to {downloaded}")
    return Path(downloaded)


def _use_account(acsm: Path, username: str, password: str) -> None:
    from adl.exceptions import AdeptError
    from adl.login import login

    from adl import account, data

    user = next((a for a in data.accounts if a.sign_id == username), None)
    if user is None:
        try:
            login(username, password)
        except AdeptError as e:
            # Its message says what to fix (wrong password, ByteBooks migration, 2FA).
            raise BookError(acsm, message=str(e)) from e
    elif data.config is None or data.config.current_user != user.urn:
        account.set_default_account(user.urn)

    current = data.get_current_account()
    if current is None or current.sign_id != username:
        raise BookError(acsm, message=f"Couldn't sign in to Adobe as {username}")
