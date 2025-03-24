from pathlib import Path
from schema import Schema, Optional

# NOTE: can't use ALL_ACTIONS cause circular dependencies
# NOTE: order matters. drm has to come first for any metadata to work, download has to happen before
#       anything to do with files, etc.
valid_actions = ["download_acsm", "drm", "kfx2epub", "rename", "pdf", "print", "none"]


schema = Schema(
    {
        Optional("extends"): str,
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
        extends = data.get("extends")
        parent = Config(extends) if extends else None
        self.actions = optional_list_value(data, "actions", parent)
        self.adobe_key_files = optional_list_value(data, "adobe_key_files", parent)
        self.b_and_n_key_files = optional_list_value(data, "b_and_n_key_files", parent)
        self.ereader_social_drm_file = optional_value(
            data, "ereader_social_drm_file", parent
        )
        self.kindle_pidnums = optional_list_value(data, "kindle_pidnums", parent)
        self.kindle_serialnums = optional_list_value(data, "kindle_serialnums", parent)
        self.kindle_database_files = optional_list_value(
            data, "kindle_database_files", parent
        )
        self.kindle_android_files = optional_list_value(
            data, "kindle_android_files", parent
        )
        self.adobe_user = optional_value(data, "adobe_user", parent)
        self.adobe_password = data.get(
            "adobe_password", parent.adobe_password if parent else None
        )
        self.pdf_passwords = optional_list_value(data, "pdf_passwords", parent)


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
