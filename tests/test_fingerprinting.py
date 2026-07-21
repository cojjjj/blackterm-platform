from datetime import datetime, timezone

from blackterm_recon.fingerprinting import _fingerprint_web_response, fingerprint_scan
from blackterm_recon.models import PortResult, ScanResult


def result_with(*ports):
    now = datetime.now(timezone.utc).isoformat()
    return ScanResult(
        target="127.0.0.1",
        ip="127.0.0.1",
        hostname="localhost",
        ports=list(ports),
        started_at=now,
        finished_at=now,
        duration_seconds=0.1,
    )


def test_banner_and_service_fingerprints_are_detected():
    result = result_with(
        PortResult(22, "open", "ssh", banner="SSH-2.0-OpenSSH_9.7"),
        PortResult(6379, "open", "redis", banner="-ERR Redis is running"),
    )
    matches = fingerprint_scan(result, timeout=0.01)
    names = {match.name for match in matches}
    assert {"SSH", "OpenSSH", "Redis"} <= names
    assert next(match for match in matches if match.name == "OpenSSH").confidence >= 96


def test_http_evidence_combines_headers_cookies_and_body():
    candidates = {}
    _fingerprint_web_response(
        candidates,
        443,
        {
            "server": "cloudflare",
            "x-powered-by": "Next.js",
            "set-cookie": "laravel_session=abc; Path=/",
            "cf-ray": "1234-TEST",
        },
        '<script id="__NEXT_DATA__"></script><link href="/_next/static/app.css">',
        "HTTP 200 OK",
    )
    assert candidates["cloudflare"].confidence >= 98
    assert candidates["next.js"].confidence >= 98
    assert "laravel" in candidates
    assert "tls/https" in candidates


def test_fingerprints_serialize_on_scan_result():
    result = result_with(PortResult(22, "open", "ssh", banner="OpenSSH"))
    result.fingerprints = fingerprint_scan(result, timeout=0.01)
    payload = result.to_dict()
    assert payload["fingerprints"]
    assert payload["fingerprints"][0]["name"]
