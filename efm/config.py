from pathlib import Path
from typing import Literal
from schema import Schema, SchemaError, Optional

valid_actions = ["drm", "rename", "print", "pdf", "none"]
type Action = Literal["drm", "rename", "print", "pdf", "none"]


# class ValidatableAction(list):
#     def validate(self):
#         if self not in valid_actions:
#             raise SchemaError(
#                 f"Invalid action: {self}. Must be one of {', '.join(valid_actions)}"
#             )


schema = Schema(
    {
        Optional("actions"): valid_actions,
        Optional("adobe_key_file"): str,
    },
    ignore_extra_keys=True,
)


class Config(object):
    actions: list[Action] | None
    adobe_key_file: str | None

    def __init__(self, filepath: Path):
        data = schema.validate(load_config(filepath))
        self.actions = data.get("actions", None)
        self.adobe_key_file = data.get("adobe_key_file", None)


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
