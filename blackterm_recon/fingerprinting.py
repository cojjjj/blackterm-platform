from __future__ import annotations

from dataclasses import dataclass, field
from http.client import HTTPConnection, HTTPSConnection
import ssl
from typing import Iterable

from .fingerprint_signatures import (
    BANNER_SIGNATURES,
    BODY_SIGNATURES,
    COOKIE_SIGNATURES,
    HEADER_SIGNATURES,
    SERVICE_SIGNATURES,
)
from .models import PortResult, ScanResult, TechnologyFingerprint

WEB_PORTS = {80, 443, 8000, 8080, 8081, 8443, 8888}
WEB_SERVICES = {"http", "https", "http-proxy", "https-alt"}
MAX_BODY_BYTES = 512_000


@dataclass(slots=True)
class _Candidate:
    name: str
    category: str
    confidence: int
    evidence: list[str] = field(default_factory=list)
    sources: set[str] = field(default_factory=set)
    ports: set[int] = field(default_factory=set)

    def merge(self, confidence: int, evidence: str, source: str, port: int | None) -> None:
        # Independent evidence raises confidence without allowing weak signatures
        # to become certain from repetition alone.
        if source not in self.sources:
            self.confidence = min(99, max(self.confidence, confidence) + (5 if self.sources else 0))
        else:
            self.confidence = max(self.confidence, confidence)
        self.sources.add(source)
        if evidence and evidence not in self.evidence:
            self.evidence.append(evidence[:240])
        if port is not None:
            self.ports.add(port)


def _add(
    candidates: dict[str, _Candidate],
    name: str,
    category: str,
    confidence: int,
    evidence: str,
    source: str,
    port: int | None = None,
) -> None:
    key = name.casefold()
    candidate = candidates.get(key)
    if candidate is None:
        candidate = _Candidate(name, category, confidence)
        candidates[key] = candidate
    candidate.merge(confidence, evidence, source, port)


def _match_tokens(
    value: str,
    signatures: dict[str, tuple[str, str, int]],
    candidates: dict[str, _Candidate],
    *,
    source: str,
    evidence_prefix: str,
    port: int | None,
) -> None:
    lower = value.casefold()
    for token, (name, category, confidence) in signatures.items():
        if token in lower:
            _add(
                candidates, name, category, confidence,
                f"{evidence_prefix}: {value[:180]}", source, port,
            )


def _web_endpoint(port: PortResult) -> tuple[bool, int]:
    is_tls = port.port in {443, 8443} or port.service in {"https", "https-alt"}
    return is_tls, port.port


def _probe_http(host: str, port: PortResult, timeout: float) -> tuple[dict[str, str], str, str] | None:
    is_tls, endpoint_port = _web_endpoint(port)
    connection_cls = HTTPSConnection if is_tls else HTTPConnection
    kwargs = {"host": host, "port": endpoint_port, "timeout": timeout}
    if is_tls:
        # Fingerprinting is observational. An invalid or self-signed certificate
        # should not prevent collecting public response metadata.
        kwargs["context"] = ssl._create_unverified_context()  # noqa: SLF001
    connection = connection_cls(**kwargs)
    try:
        connection.request(
            "GET", "/",
            headers={
                "Host": host,
                "User-Agent": "BLACKTERM-RECON/6.1 authorized-fingerprinting",
                "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
                "Connection": "close",
            },
        )
        response = connection.getresponse()
        headers = {key.casefold(): value for key, value in response.getheaders()}
        body = response.read(MAX_BODY_BYTES).decode("utf-8", errors="replace")
        status = f"HTTP {response.status} {response.reason or ''}".strip()
        return headers, body, status
    except (OSError, ssl.SSLError, TimeoutError):
        return None
    finally:
        connection.close()


def _fingerprint_web_response(
    candidates: dict[str, _Candidate],
    port: int,
    headers: dict[str, str],
    body: str,
    status: str,
) -> None:
    for header_name, signatures in HEADER_SIGNATURES.items():
        value = headers.get(header_name, "")
        if value:
            _match_tokens(
                value, signatures, candidates,
                source=f"http_header:{header_name}",
                evidence_prefix=header_name,
                port=port,
            )

    cookies = headers.get("set-cookie", "")
    if cookies:
        _match_tokens(
            cookies, COOKIE_SIGNATURES, candidates,
            source="http_cookie", evidence_prefix="Set-Cookie", port=port,
        )

    body_lower = body.casefold()
    for token, (name, category, confidence) in BODY_SIGNATURES.items():
        if token in body_lower:
            _add(
                candidates, name, category, confidence,
                f"HTML marker: {token}", "http_body", port,
            )

    if headers.get("cf-ray") or headers.get("cf-cache-status"):
        _add(candidates, "Cloudflare", "cdn", 98, "Cloudflare response header present", "http_header", port)
    if headers.get("x-vercel-id"):
        _add(candidates, "Vercel", "hosting", 98, "x-vercel-id response header present", "http_header", port)
    if headers.get("x-amz-cf-id"):
        _add(candidates, "Amazon CloudFront", "cdn", 98, "x-amz-cf-id response header present", "http_header", port)
    if headers.get("x-drupal-cache"):
        _add(candidates, "Drupal", "cms", 98, "x-drupal-cache response header present", "http_header", port)

    _add(candidates, "HTTP", "protocol", 72, status, "http_status", port)
    if port in {443, 8443}:
        _add(candidates, "TLS/HTTPS", "protocol", 80, f"TLS web response on TCP/{port}", "http_status", port)


def fingerprint_scan(result: ScanResult, timeout: float = 2.5) -> list[TechnologyFingerprint]:
    """Passively fingerprint technologies observed during an authorized scan.

    Existing service names and banners are always analyzed. Open web services are
    additionally queried at `/` with one bounded GET request to collect response
    headers, cookies, and HTML markers. No paths are brute-forced and no exploit
    checks are performed.
    """
    candidates: dict[str, _Candidate] = {}

    for item in result.open_ports:
        service = (item.service or "unknown").casefold()
        if service in SERVICE_SIGNATURES:
            name, category, confidence = SERVICE_SIGNATURES[service]
            _add(
                candidates, name, category, confidence,
                f"Service classification: {item.port}/tcp {item.service}",
                "service", item.port,
            )
        if item.banner:
            _match_tokens(
                item.banner, BANNER_SIGNATURES, candidates,
                source="banner", evidence_prefix=f"TCP/{item.port} banner", port=item.port,
            )

    web_candidates = [
        item for item in result.open_ports
        if item.port in WEB_PORTS or item.service in WEB_SERVICES
    ][:8]
    host = result.hostname or result.target or result.ip
    for item in web_candidates:
        response = _probe_http(host, item, max(0.25, min(timeout, 8.0)))
        if response is not None:
            headers, body, status = response
            _fingerprint_web_response(candidates, item.port, headers, body, status)

    fingerprints = [
        TechnologyFingerprint(
            name=item.name,
            category=item.category,
            confidence=item.confidence,
            evidence=item.evidence[:8],
            sources=sorted(item.sources),
            ports=sorted(item.ports),
        )
        for item in candidates.values()
    ]
    return sorted(fingerprints, key=lambda item: (-item.confidence, item.category, item.name.casefold()))


def technology_names(fingerprints: Iterable[TechnologyFingerprint]) -> list[str]:
    return [item.name for item in fingerprints]
