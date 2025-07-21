from pathlib import Path
from schema import Schema, Optional, Use
import logging

logger = logging.getLogger(__name__)


def _path_exists(s: str) -> Path:
    p = Path(s).expanduser()
    if not p.exists():
        raise ValueError(f"Path {p} does not exist.")
    return p


schema = Schema(
    {
        Optional("output_dir"): str,
        Optional("adobe_user"): str,
        Optional("adobe_password"): str,
        Optional("adobe_key_files"): [Use(_path_exists)],
        Optional("b_and_n_key_files"): [Use(_path_exists)],
        Optional("ereader_social_drm_file"): Use(_path_exists),
        Optional("pdf_passwords"): list[str],
        Optional("kindle_pidnums"): list[str],
        Optional("kindle_serialnums"): list[str],
        # kindle_database_files is a list of files created by kindlekey
        Optional("kindle_database_files"): [Use(_path_exists)],
        Optional("kindle_android_files"): [Use(_path_exists)],
    },
)


class Config(object):
    output_dir: str | None
    adobe_user: str | None
    adobe_password: str | None
    adobe_key_files: list[Path] | None
    b_and_n_key_files: list[Path] | None
    ereader_social_drm_file: Path | None
    kindle_pidnums: list[str] | None
    kindle_serialnums: list[str] | None
    kindle_database_files: list[Path] | None
    kindle_android_files: list[Path] | None
    pdf_passwords: list[str] | None

    def __init__(self, filepath: Path):
        data = schema.validate(load_config(filepath))
        self.output_dir = data.get("output_dir")
        self.adobe_user = data.get("adobe_user")
        self.adobe_password = data.get("adobe_password")
        self.adobe_key_files = data.get("adobe_key_files")
        self.b_and_n_key_files = data.get("b_and_n_key_files")
        self.ereader_social_drm_file = data.get("ereader_social_drm_file")
        self.kindle_pidnums = data.get("kindle_pidnums")
        self.kindle_serialnums = data.get("kindle_serialnums")
        self.kindle_database_files = data.get("kindle_database_files")
        self.kindle_android_files = data.get("kindle_android_files")
        self.pdf_passwords = data.get("pdf_passwords")


def load_config(filepath: Path):
    ext = filepath.suffix[1:]
    if ext == "toml":
        import toml

        return toml.load(filepath)

    if ext in ["yaml", "yml"]:
        import yaml

        with open(filepath) as f:
            return yaml.safe_load(f)

    if ext == "json":
        import json

        with open(filepath) as f:
            return json.load(f)
    raise ValueError(f"Unknown config file extension: {ext}")


def get_config(dirpath: Path) -> Config | None:
    """
    Get the config file in the given directory.
    """
    for ext in ["toml", "yaml", "yml", "json"]:
        config_file = dirpath / f"efm.{ext}"
        if config_file.exists():
            return Config(config_file)
    return None
