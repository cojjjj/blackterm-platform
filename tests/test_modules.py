from blackterm_recon.desktop.modules import MODULES


def test_recon_module_is_active():
    recon = next(module for module in MODULES if module.key == "recon")
    assert recon.status == "ACTIVE"
    assert recon.command == "LIVE SCAN"


def test_module_keys_are_unique():
    keys = [module.key for module in MODULES]
    assert len(keys) == len(set(keys))
