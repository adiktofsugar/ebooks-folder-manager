from pathlib import Path
import logging
from typing import Annotated
from pydantic import BaseModel, BeforeValidator

logger = logging.getLogger(__name__)


def expand_path(v: Path | str | None):
    if v:
        return Path(v).expanduser()


def expand_and_validate_path(v: Path | None):
    """Expand user paths and validate they exist"""
    v = expand_path(v)
    if v and not v.exists():
        raise ValueError(f"Path {v} does not exist")
    return v


def expand_and_validate_path_list(v: list[Path] | None):
    """Expand user paths in a list and validate they exist"""
    if v is None:
        return None
    return [expand_and_validate_path(p) for p in v]


ExpandedPath = Annotated[Path | None, BeforeValidator(expand_path)]
ExistingPath = Annotated[Path | None, BeforeValidator(expand_and_validate_path)]
ExistingPathList = Annotated[
    list[Path] | None, BeforeValidator(expand_and_validate_path_list)
]


class Config(BaseModel):
    output_dir: ExpandedPath | None = None
    adobe_user: str | None = None
    adobe_password: str | None = None
    adobe_key_files: ExistingPathList = None
    b_and_n_key_files: ExistingPathList = None
    ereader_social_drm_file: ExistingPath = None
    kindle_pidnums: list[str] | None = None
    kindle_serialnums: list[str] | None = None
    kindle_database_files: ExistingPathList = None
    kindle_android_files: ExistingPathList = None
    pdf_passwords: list[str] | None = None


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


def get_config_filepath(dirpath: Path) -> Path | None:
    """
    Get the config filepath in the given directory if it exists.
    """
    for ext in ["toml", "yaml", "yml", "json"]:
        config_file = dirpath / f"efm.{ext}"
        if config_file.exists():
            return config_file
    return None


def get_config(dirpath: Path) -> Config | None:
    """
    Get the config by searching up the directory tree and merging parent configs.
    Parent values are only added if not present in child configs.
    """
    # Find config in the given directory first
    config_file = get_config_filepath(dirpath)
    if not config_file:
        return None

    # Start with the primary config data
    raw_data = load_config(config_file)

    # Search up the directory tree for parent configs
    current = dirpath.parent.resolve()
    while current != current.parent:
        parent_config = get_config_filepath(current)
        if parent_config:
            parent_data = load_config(parent_config)
            # Only add parent values if not present in child
            for key, value in parent_data.items():
                if key not in raw_data:
                    raw_data[key] = value
        current = current.parent

    return Config(**raw_data)
