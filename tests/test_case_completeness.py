from blackterm_recon.case_completeness import assess_case_completeness


def test_empty_case_is_early_stage():
    report = assess_case_completeness(
        {"description": ""}, [], [], [], []
    )
    assert report.score == 0
    assert report.level == "EARLY STAGE"
    assert report.missing


def test_complete_case_reaches_mission_ready():
    evidence = [
        {"evidence_type": "DNS", "title": "DNS records", "content": "A record and CNAME"},
        {"evidence_type": "WHOIS", "title": "WHOIS registrar context", "content": "registrar"},
        {"evidence_type": "SSL", "title": "TLS certificate", "content": "X.509 certificate"},
        {"evidence_type": "SCREENSHOT", "title": "Workspace capture", "file_path": "capture.png"},
        {"evidence_type": "AI", "title": "AI investigation summary", "source": "BLACKTERM AI"},
        {"evidence_type": "AI", "title": "Intelligence correlation report", "content": "correlation"},
        {"evidence_type": "HEADERS", "title": "Technology fingerprint", "content": "Server header: nginx"},
    ]
    timeline = [
        {"event_type": "SCAN", "title": "Scan attached", "detail": ""},
        {"event_type": "INTEL", "title": "Intelligence correlation completed", "detail": ""},
        {"event_type": "AI", "title": "AI investigation completed", "detail": ""},
    ]
    report = assess_case_completeness(
        {"description": "Authorized assessment scope"},
        [{"open_ports": 3}],
        [{"note": "Review SMB exposure"}],
        evidence,
        timeline,
    )
    assert report.score == 100
    assert report.level == "MISSION READY"
    assert not report.missing
