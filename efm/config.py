from pathlib import Path
from typing import Literal
from schema import Schema, Optional

valid_actions = ["drm", "rename", "print", "pdf", "download", "none"]
type Action = Literal["drm", "rename", "print", "pdf", "download", "none"]


schema = Schema(
    {
        Optional("extends"): str,
        Optional("actions"): valid_actions,
        Optional("adobe_key_file"): str,
        Optional("adobe_user"): str,
        Optional("adobe_password"): str,
    },
    ignore_extra_keys=True,
)


class Config(object):
    actions: list[Action] | None
    adobe_key_file: str | None
    adobe_user: str | None
    adobe_password: str | None

    def __init__(self, filepath: Path):
        data = schema.validate(load_config(filepath))
        extends = data.get("extends")
        parent = Config(extends) if extends else None
        self.actions = data.get("actions", parent.actions if parent else None)
        self.adobe_key_file = data.get(
            "adobe_key_file", parent.adobe_key_file if parent else None
        )
        self.adobe_user = data.get("adobe_user", parent.adobe_user if parent else None)
        self.adobe_password = data.get(
            "adobe_password", parent.adobe_password if parent else None
        )


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


def get_closest_config(dirpath: str) -> Config | None:
    filepath = get_closest_config_filepath(dirpath)
    if filepath is None:
        return None
    return Config(filepath)


def get_closest_config_filepath(dirpath: str) -> Path | None:
    """
    Get the closest config file to the given directory.
    """
    path = Path(dirpath)
    while True:
        for ext in ["toml", "yaml", "yml", "json"]:
            config_file = path / f"efm.{ext}"
            if config_file.exists():
                return config_file
        if path == path.parent:
            return None
        path = path.parent
