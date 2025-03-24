from pathlib import Path
from schema import Schema, Optional

# NOTE: can't use ALL_ACTIONS cause circular dependencies
# NOTE: order matters. drm has to come first for any metadata to work, download has to happen before
#       anything to do with files, etc.
valid_actions = ["download_acsm", "drm", "kfx2epub", "rename", "pdf", "print", "none"]


schema = Schema(
    {
        Optional("actions"): valid_actions,
        Optional("adobe_key_files"): list[str],
        Optional("b_and_n_key_files"): list[str],
        Optional("ereader_social_drm_file"): str,
        Optional("adobe_user"): str,
        Optional("adobe_password"): str,
        Optional("pdf_passwords"): list[str],
        Optional("kindle_pidnums"): list[str],
        Optional("kindle_serialnums"): list[str],
        # kindle_database_files is a list of files created by kindlekey
        Optional("kindle_database_files"): list[str],
        Optional("kindle_android_files"): [str],
    },
    ignore_extra_keys=True,
)


class Config(object):
    actions: list[str] | None
    adobe_key_files: list[str] | None
    b_and_n_key_files: list[str] | None
    ereader_social_drm_file: str | None
    kindle_pidnums: list[str] | None
    kindle_serialnums: list[str] | None
    kindle_database_files: list[str] | None
    kindle_android_files: list[str] | None
    adobe_user: str | None
    adobe_password: str | None
    pdf_passwords: list[str] | None

    def __init__(self, filepath: Path):
        data = schema.validate(load_config(filepath))
        self.actions = data.get("actions")
        self.adobe_key_files = data.get("adobe_key_files")
        self.b_and_n_key_files = data.get("b_and_n_key_files")
        self.ereader_social_drm_file = data.get("ereader_social_drm_file")
        self.kindle_pidnums = data.get("kindle_pidnums")
        self.kindle_serialnums = data.get("kindle_serialnums")
        self.kindle_database_files = data.get("kindle_database_files")
        self.kindle_android_files = data.get("kindle_android_files")
        self.adobe_user = data.get("adobe_user")
        self.adobe_password = data.get("adobe_password")
        self.pdf_passwords = data.get("pdf_passwords")


def optional_value(d: dict[str, str], key: str, parent: Config | None) -> str | None:
    return d.get(key, getattr(parent, key) if parent else None)


def optional_list_value(
    d: dict[str, list[str]], key: str, parent: Config | None
) -> list[str] | None:
    value = d.get(key)
    parent_value = getattr(parent, key) if parent else None
    if value is None:
        return parent_value
    return value + parent_value if parent_value else []


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
