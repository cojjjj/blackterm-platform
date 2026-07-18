from blackterm_recon.desktop.network_model import classify_host


def test_windows_service_classification():
    device_type, label = classify_host({"microsoft-ds", "epmap"})
    assert device_type == "windows"
    assert "Windows" in label


def test_linux_service_classification():
    device_type, _ = classify_host({"ssh"})
    assert device_type == "linux"


def test_web_service_classification():
    device_type, _ = classify_host({"http", "https"})
    assert device_type == "web"


def test_unknown_classification():
    device_type, _ = classify_host(set())
    assert device_type == "unknown"
