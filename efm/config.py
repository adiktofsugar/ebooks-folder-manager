import logging
from pathlib import Path
from typing import Annotated, ClassVar

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

logger = logging.getLogger(__name__)


def expand_path(path: Path | str | None):
    if path:
        return Path(path).expanduser()


def expand_and_validate_path(path: Path | None):
    """Expand user paths and validate they exist"""
    path = expand_path(path)
    if path and not path.exists():
        raise ValueError(f"Path {path} does not exist")
    return path


def expand_and_validate_path_list(paths: list[Path] | None):
    """Expand user paths in a list and validate they exist"""
    if paths is None:
        return None
    return [expand_and_validate_path(path) for path in paths]


ExistingPath = Annotated[Path | None, BeforeValidator(expand_and_validate_path)]
ExistingPathList = Annotated[
    list[Path] | None, BeforeValidator(expand_and_validate_path_list)
]


class RenameVariant(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    if_: str | None = Field(None, alias="if")
    value: str


# A template, or variants tried in order (a plain string always matches).
Preset = str | list[str | RenameVariant]


class RenameConfig(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    presets: dict[str, Preset] = {}
    default_preset: str | None = None


class Config(BaseModel):
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
    rename: RenameConfig | None = None


def load_config(config_file: Path):
    ext = config_file.suffix[1:]
    if ext == "toml":
        import tomllib

        with open(config_file, "rb") as f:
            return tomllib.load(f)

    if ext in ["yaml", "yml"]:
        import yaml

        with open(config_file) as f:
            return yaml.safe_load(f)

    if ext == "json":
        import json

        with open(config_file) as f:
            return json.load(f)
    raise ValueError(f"Unknown config file extension: {ext}")


def get_config_file(dir: Path) -> Path | None:
    """
    Get the config file in the given directory if it exists.
    """
    for ext in ["toml", "yaml", "yml", "json"]:
        config_file = dir / f"efm.{ext}"
        if config_file.exists():
            return config_file
    return None


def get_config(dir: Path) -> Config | None:
    """
    Get the config by searching up the directory tree and merging parent configs.
    Parent values are only added if not present in child configs.
    """
    # The nearest config, starting from dir, is the primary one
    dir = dir.resolve()
    config_file = None
    while config_file is None:
        config_file = get_config_file(dir)
        if dir == dir.parent:
            break
        if config_file is None:
            dir = dir.parent
    if not config_file:
        return None

    raw_data = load_config(config_file)

    # Search up the directory tree for parent configs
    current_dir = dir.parent
    while current_dir != current_dir.parent:
        parent_config_file = get_config_file(current_dir)
        if parent_config_file:
            parent_data = load_config(parent_config_file)
            # Only add parent values if not present in child
            for key, value in parent_data.items():
                if key not in raw_data:
                    raw_data[key] = value
        current_dir = current_dir.parent

    return Config(**raw_data)
