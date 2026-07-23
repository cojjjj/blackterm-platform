import json

from blackterm_recon.desktop.pages.global_map import GlobalIntelligenceMapPage


def test_extract_geoip_payload_without_constructing_widget():
    payload = {
        "modules": [{
            "module": "geoip", "status": "success",
            "evidence": [{"content": json.dumps({"latitude": 42.1, "longitude": -78.4})}],
        }]
    }
    result = GlobalIntelligenceMapPage._extract_geo(payload)
    assert result is not None
    assert result[0] == 42.1
    assert result[1] == -78.4


def test_extract_geoip_ignores_failed_module():
    payload = {"modules": [{"module": "geoip", "status": "error", "evidence": []}]}
    assert GlobalIntelligenceMapPage._extract_geo(payload) is None
