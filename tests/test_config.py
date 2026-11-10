from pathlib import Path

from efm.config import get_config


def test_config_found_in_parent_dir(tmp_path: Path):
    (tmp_path / "efm.toml").write_text('adobe_user = "parent"\nadobe_password = "p"\n')
    sub = tmp_path / "incoming"
    sub.mkdir()
    (sub / "efm.toml").write_text('adobe_user = "child"\n')
    deeper = sub / "deeper"
    deeper.mkdir()

    config = get_config(deeper)
    assert config is not None
    assert config.adobe_user == "child"
    assert config.adobe_password == "p"


def test_no_config(tmp_path: Path):
    assert get_config(tmp_path) is None
