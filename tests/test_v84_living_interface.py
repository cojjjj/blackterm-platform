from pathlib import Path

from blackterm_recon.desktop.living_interface import BOOT_STAGES


def test_boot_sequence_reaches_platform_ready():
    assert BOOT_STAGES
    assert BOOT_STAGES[-1].progress == 100
    assert "ready" in BOOT_STAGES[-1].label.lower()


def test_living_interface_integration_contracts_exist():
    root = Path(__file__).resolve().parents[1]
    main = (root / "blackterm_recon/desktop/main_window.py").read_text(encoding="utf-8")
    dock = (root / "blackterm_recon/desktop/dock.py").read_text(encoding="utf-8")
    operator = (
        root / "blackterm_recon/desktop/operator_dashboard_page.py"
    ).read_text(encoding="utf-8")

    assert "BootOverlay" in main
    assert "FadeController" in main
    assert "PulseController" in dock
    assert "LoadingStrip" in operator
    assert "class DockButton" in dock
