from __future__ import annotations

import ipaddress
import json
import os
import re
import socket
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Callable, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from .models import ProviderResult, ThreatEvidence, ThreatFinding, ThreatIntelligenceResult

ProgressCallback = Callable[[str, int, str, ProviderResult | None], None]


def normalize_indicator(raw: str) -> tuple[str, str]:
    value = raw.strip()
    if not value:
        raise ValueError("An indicator is required.")
    parsed = urlparse(value if "://" in value else f"//{value}")
    host = (parsed.hostname or value).strip().lower().rstrip(".")
    try:
        ipaddress.ip_address(host)
        return host, "ip"
    except ValueError:
        pass
    if not re.fullmatch(r"(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}", host):
        raise ValueError("Enter a valid public IP address, domain, or URL.")
    return host, "domain"


def _request_json(url: str, *, headers=None, data=None, timeout=8.0) -> dict:
    encoded = urlencode(data).encode() if isinstance(data, dict) else data
    request = Request(url, data=encoded, headers=headers or {})
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8", errors="replace"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body[:300]}") from exc
    except URLError as exc:
        raise RuntimeError(str(exc.reason)) from exc


def _result(provider, started, *, status="success", summary="", findings=(), evidence=(), score=0, confidence=0, error=""):
    return ProviderResult(
        provider=provider, status=status, summary=summary,
        findings=tuple(findings), evidence=tuple(evidence),
        score=max(0, min(100, int(score))), confidence=max(0, min(100, int(confidence))),
        duration_ms=int((time.perf_counter() - started) * 1000), error=error,
    )


def local_provider(indicator: str, indicator_type: str, **_) -> ProviderResult:
    started = time.perf_counter()
    findings = []
    evidence = []
    score = 0
    if indicator_type == "ip":
        address = ipaddress.ip_address(indicator)
        if not address.is_global:
            findings.append(ThreatFinding("Non-public address", "The indicator is private, reserved, loopback, or otherwise non-global.", "INFO", 0, 100, "Local analysis"))
        else:
            findings.append(ThreatFinding("Public routable address", "The indicator is a globally routable IP address.", "INFO", 0, 100, "Local analysis"))
    else:
        labels = indicator.split(".")
        suspicious = sum(ch.isdigit() for ch in labels[0]) >= 5 or len(labels[0]) > 35 or labels[0].count("-") >= 4
        punycode = any(label.startswith("xn--") for label in labels)
        if suspicious:
            score += 12
            findings.append(ThreatFinding("Unusual domain structure", "The domain label has characteristics that merit manual review.", "LOW", 12, 65, "Local analysis"))
        if punycode:
            score += 12
            findings.append(ThreatFinding("Internationalized domain", "Punycode is present. This is legitimate in many cases but can also be used for visual impersonation.", "LOW", 12, 75, "Local analysis"))
        try:
            addresses = sorted({item[4][0] for item in socket.getaddrinfo(indicator, None, proto=socket.IPPROTO_TCP)})
            evidence.append(ThreatEvidence("DNS", "Resolved addresses", "System resolver", json.dumps(addresses, indent=2)))
        except OSError as exc:
            score += 15
            findings.append(ThreatFinding("Resolution failure", f"The domain did not resolve during collection: {exc}", "LOW", 15, 80, "System resolver"))
    return _result("local", started, summary="Completed deterministic indicator checks.", findings=findings, evidence=evidence, score=score, confidence=90)


def urlhaus_provider(indicator: str, indicator_type: str, timeout=8.0, **_) -> ProviderResult:
    started = time.perf_counter()
    try:
        data = _request_json("https://urlhaus-api.abuse.ch/v1/host/", data={"host": indicator}, timeout=timeout)
    except Exception as exc:
        return _result("urlhaus", started, status="error", summary="URLhaus lookup failed.", error=str(exc))
    status = str(data.get("query_status", "unknown"))
    urls = data.get("urls") or []
    matches = len(urls)
    findings = []
    score = 0
    if status == "ok" and matches:
        score = min(95, 65 + min(30, matches * 3))
        findings.append(ThreatFinding("URLhaus match", f"URLhaus returned {matches} malicious URL record(s) associated with this host.", "HIGH", score, 95, "URLhaus", {"matches": matches}))
    elif status in {"no_results", "invalid_host"}:
        findings.append(ThreatFinding("No URLhaus match", "No active URLhaus host record was returned.", "INFO", 0, 85, "URLhaus"))
    return _result("urlhaus", started, summary=f"Query status: {status}; matches: {matches}.", findings=findings, evidence=(ThreatEvidence("THREAT_FEED", "URLhaus response", "URLhaus", json.dumps(data, indent=2)),), score=score, confidence=90)


def virustotal_provider(indicator: str, indicator_type: str, timeout=8.0, api_key="", **_) -> ProviderResult:
    started = time.perf_counter()
    key = api_key or os.getenv("BLACKTERM_VIRUSTOTAL_API_KEY", "")
    if not key:
        return _result("virustotal", started, status="skipped", summary="API key not configured.")
    kind = "ip_addresses" if indicator_type == "ip" else "domains"
    try:
        data = _request_json(f"https://www.virustotal.com/api/v3/{kind}/{indicator}", headers={"x-apikey": key}, timeout=timeout)
    except Exception as exc:
        return _result("virustotal", started, status="error", summary="VirusTotal lookup failed.", error=str(exc))
    stats = (((data.get("data") or {}).get("attributes") or {}).get("last_analysis_stats") or {})
    malicious = int(stats.get("malicious", 0)); suspicious = int(stats.get("suspicious", 0)); harmless = int(stats.get("harmless", 0))
    score = min(100, malicious * 12 + suspicious * 5)
    findings = []
    if malicious or suspicious:
        sev = "CRITICAL" if malicious >= 5 else "HIGH" if malicious else "MODERATE"
        findings.append(ThreatFinding("VirusTotal detections", f"{malicious} engine(s) marked malicious and {suspicious} marked suspicious.", sev, score, 95, "VirusTotal", stats))
    else:
        findings.append(ThreatFinding("No VirusTotal detections", f"No malicious or suspicious engines were reported; {harmless} marked harmless.", "INFO", 0, 85, "VirusTotal", stats))
    return _result("virustotal", started, summary=f"malicious={malicious}, suspicious={suspicious}, harmless={harmless}", findings=findings, evidence=(ThreatEvidence("REPUTATION", "VirusTotal response", "VirusTotal", json.dumps(data, indent=2)),), score=score, confidence=95)


def abuseipdb_provider(indicator: str, indicator_type: str, timeout=8.0, api_key="", **_) -> ProviderResult:
    started = time.perf_counter()
    if indicator_type != "ip":
        return _result("abuseipdb", started, status="skipped", summary="Provider applies to IP indicators only.")
    key = api_key or os.getenv("BLACKTERM_ABUSEIPDB_API_KEY", "")
    if not key:
        return _result("abuseipdb", started, status="skipped", summary="API key not configured.")
    url = "https://api.abuseipdb.com/api/v2/check?" + urlencode({"ipAddress": indicator, "maxAgeInDays": 90, "verbose": ""})
    try:
        data = _request_json(url, headers={"Key": key, "Accept": "application/json"}, timeout=timeout)
    except Exception as exc:
        return _result("abuseipdb", started, status="error", summary="AbuseIPDB lookup failed.", error=str(exc))
    info = data.get("data") or {}
    abuse = int(info.get("abuseConfidenceScore", 0)); reports = int(info.get("totalReports", 0))
    findings = []
    if abuse:
        sev = "CRITICAL" if abuse >= 80 else "HIGH" if abuse >= 50 else "MODERATE" if abuse >= 20 else "LOW"
        findings.append(ThreatFinding("AbuseIPDB reputation", f"Abuse confidence is {abuse}% across {reports} report(s).", sev, abuse, 92, "AbuseIPDB", info))
    else:
        findings.append(ThreatFinding("No AbuseIPDB confidence", f"Abuse confidence is 0%; total reports: {reports}.", "INFO", 0, 80, "AbuseIPDB", info))
    return _result("abuseipdb", started, summary=f"abuse confidence={abuse}%; reports={reports}", findings=findings, evidence=(ThreatEvidence("REPUTATION", "AbuseIPDB response", "AbuseIPDB", json.dumps(data, indent=2)),), score=abuse, confidence=92)


PROVIDERS = {
    "local": local_provider,
    "urlhaus": urlhaus_provider,
    "virustotal": virustotal_provider,
    "abuseipdb": abuseipdb_provider,
}


def _level(score: int) -> str:
    if score >= 80: return "CRITICAL"
    if score >= 55: return "HIGH"
    if score >= 30: return "MODERATE"
    if score >= 10: return "LOW"
    return "CLEAN"


class ThreatIntelligenceEngine:
    def __init__(self, *, timeout=8.0, max_workers=4, virustotal_api_key="", abuseipdb_api_key=""):
        self.timeout = max(2.0, float(timeout))
        self.max_workers = max(1, min(6, int(max_workers)))
        self.virustotal_api_key = virustotal_api_key
        self.abuseipdb_api_key = abuseipdb_api_key

    def run(self, raw_target: str, *, enabled_providers: Iterable[str] | None = None, progress: ProgressCallback | None = None) -> ThreatIntelligenceResult:
        indicator, indicator_type = normalize_indicator(raw_target)
        started_at = datetime.now(timezone.utc).isoformat()
        names = tuple(enabled_providers or PROVIDERS.keys())
        names = tuple(name for name in names if name in PROVIDERS)
        if not names:
            raise ValueError("At least one threat intelligence provider must be enabled.")
        results = {}
        if progress: progress("pipeline", 0, f"Threat intelligence started for {indicator}.", None)
        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(names))) as pool:
            futures = {}
            for name in names:
                if progress: progress(name, 0, "Provider started.", None)
                futures[pool.submit(PROVIDERS[name], indicator, indicator_type, timeout=self.timeout, api_key=(self.virustotal_api_key if name == "virustotal" else self.abuseipdb_api_key if name == "abuseipdb" else ""))] = name
            completed = 0
            for future in as_completed(futures):
                name = futures[future]
                try:
                    result = future.result()
                except Exception as exc:
                    result = ProviderResult(name, "error", f"{name} raised an unexpected error.", error=str(exc))
                results[name] = result
                completed += 1
                if progress: progress(name, int(completed / len(names) * 100), result.summary, result)
        ordered = tuple(results[name] for name in names)
        scored = [p for p in ordered if p.status == "success" and p.confidence > 0]
        threat_score = max((p.score for p in scored), default=0)
        if len(scored) > 1:
            weighted = sum(p.score * p.confidence for p in scored) / max(1, sum(p.confidence for p in scored))
            threat_score = min(100, round(max(threat_score * .75, weighted)))
        confidence = round(sum(p.confidence for p in scored) / len(scored)) if scored else 0
        level = _level(threat_score)
        ioc_matches = sum(1 for f in (f for p in ordered for f in p.findings) if f.score >= 30)
        verdict = "KNOWN OR STRONGLY SUSPECTED MALICIOUS" if threat_score >= 80 else "SUSPICIOUS" if threat_score >= 30 else "LOW REPUTATION RISK" if threat_score >= 10 else "NO KNOWN THREAT MATCH"
        failed = sum(1 for p in ordered if p.status == "error")
        skipped = sum(1 for p in ordered if p.status == "skipped")
        summary = f"BLACKTERM queried {len(ordered)} provider(s); {len(scored)} completed successfully, {skipped} skipped, and {failed} require review. Current verdict is {verdict} at {confidence}% confidence."
        result = ThreatIntelligenceResult(raw_target, indicator, indicator_type, started_at, datetime.now(timezone.utc).isoformat(), ordered, threat_score, confidence, level, verdict, summary, ioc_matches, 0)
        if progress: progress("pipeline", 100, "Threat intelligence pipeline complete.", None)
        return result
