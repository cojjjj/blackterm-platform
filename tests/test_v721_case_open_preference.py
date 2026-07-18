from pathlib import Path

from blackterm_recon.config import AppConfig, load_config, save_config


def test_case_open_behavior_defaults_to_ask():
    assert AppConfig().case_open_behavior == "ask"


def test_case_open_behavior_round_trip(tmp_path: Path):
    path = tmp_path / "config.json"
    config = AppConfig(case_open_behavior="never")
    save_config(config, path)
    loaded = load_config(path)
    assert loaded.case_open_behavior == "never"


def test_invalid_case_open_behavior_is_rejected():
    config = AppConfig(case_open_behavior="sometimes")
    try:
        config.validate()
    except ValueError as exc:
        assert "case_open_behavior" in str(exc)
    else:
        raise AssertionError("invalid behavior should fail validation")
