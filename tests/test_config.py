from blackterm_recon.config import AppConfig


def test_config_validation():
    config = AppConfig(workers=100, timeout=0.5)
    config.validate()
    assert config.workers == 100
