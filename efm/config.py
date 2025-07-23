from pathlib import Path
from schema import Schema, Optional, Use
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


def _path_exists(s: str) -> Path:
    p = Path(s).expanduser()
    if not p.exists():
        raise ValueError(f"Path {p} does not exist.")
    return p


schema = Schema(
    {
        Optional("output_dir"): Use(_path_exists),
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


@dataclass
class Config:
    output_dir: Path | None = None
    adobe_user: str | None = None
    adobe_password: str | None = None
    adobe_key_files: list[Path] | None = None
    b_and_n_key_files: list[Path] | None = None
    ereader_social_drm_file: Path | None = None
    kindle_pidnums: list[str] | None = None
    kindle_serialnums: list[str] | None = None
    kindle_database_files: list[Path] | None = None
    kindle_android_files: list[Path] | None = None
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
    
    return Config(**schema.validate(raw_data))
