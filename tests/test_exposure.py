from blackterm_recon.desktop.network_model import exposure_color, exposure_score


def test_exposure_score_increases_with_ports():
    low, _ = exposure_score([80], ["http"])
    high, _ = exposure_score([22, 80, 443, 445, 3389], ["ssh", "http", "https", "microsoft-ds"])
    assert high > low


def test_exposure_score_is_bounded():
    score, _ = exposure_score(list(range(1, 100)), ["telnet", "vnc"])
    assert score == 100


def test_exposure_colors():
    assert exposure_color(10) == "#35df83"
    assert exposure_color(80) == "#ff5c7a"
