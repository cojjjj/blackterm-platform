from blackterm_recon.intelligence.engine import default_registry
from blackterm_recon.intelligence.modules import asn_module, geoip_module


class FakeSocket:
    def __init__(self, response: bytes):
        self.response = response
        self.sent = b""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def sendall(self, data):
        self.sent += data

    def recv(self, size):
        response, self.response = self.response, b""
        return response


class FakeHTTPResponse:
    status = 200

    def read(self, size):
        return (
            b'{"success":true,"ip":"203.0.113.10","city":"Example City",'
            b'"region":"New York","country":"United States",'
            b'"connection":{"asn":64500,"org":"Example Networks","isp":"Example ISP"}}'
        )


class FakeHTTPSConnection:
    def __init__(self, *args, **kwargs):
        pass

    def request(self, *args, **kwargs):
        pass

    def getresponse(self):
        return FakeHTTPResponse()

    def close(self):
        pass


def test_default_registry_exposes_osint_modules():
    names = set(default_registry().names())
    assert {"dns", "whois", "asn", "geoip", "ssl", "http", "technology"} <= names


def test_asn_module_normalizes_team_cymru_response(monkeypatch):
    response = (
        b"AS | IP | BGP Prefix | CC | Registry | Allocated | AS Name\n"
        b"64500 | 203.0.113.10 | 203.0.113.0/24 | US | arin | 2020-01-01 | EXAMPLE-NET\n"
    )
    monkeypatch.setattr(
        "blackterm_recon.intelligence.modules._resolve_primary_ip",
        lambda target: "203.0.113.10",
    )
    monkeypatch.setattr(
        "blackterm_recon.intelligence.modules.socket.create_connection",
        lambda *args, **kwargs: FakeSocket(response),
    )
    result = asn_module("example.test")
    assert result.status == "success"
    assert any(item.title == "Autonomous system" and item.detail == "AS64500" for item in result.findings)
    assert any(item.title == "Network organization" for item in result.findings)


def test_geoip_module_tracks_source_and_organization(monkeypatch):
    monkeypatch.setattr(
        "blackterm_recon.intelligence.modules._resolve_primary_ip",
        lambda target: "203.0.113.10",
    )
    monkeypatch.setattr(
        "blackterm_recon.intelligence.modules.HTTPSConnection",
        FakeHTTPSConnection,
    )
    result = geoip_module("example.test")
    assert result.status == "success"
    assert result.evidence[0].source == "ipwho.is"
    assert any(item.title == "Hosting organization" for item in result.findings)
