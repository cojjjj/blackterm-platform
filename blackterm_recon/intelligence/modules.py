from __future__ import annotations

import json
import re
import socket
import ssl
import time
from datetime import datetime, timezone
from http.client import HTTPConnection, HTTPSConnection
from ipaddress import ip_address
from typing import Callable
from urllib.parse import urlparse

from .models import (
    IntelligenceEvidence,
    IntelligenceFinding,
    IntelligenceModuleResult,
    IntelligenceRelationship,
)


USER_AGENT = "BLACKTERM-Intelligence/8.0 authorized-security-research"
TECH_SIGNATURES = {
    "wordpress": ("WordPress", 3),
    "wp-content": ("WordPress", 3),
    "drupal": ("Drupal", 3),
    "joomla": ("Joomla", 3),
    "react": ("React", 1),
    "next.js": ("Next.js", 1),
    "__next_data__": ("Next.js", 1),
    "vue": ("Vue.js", 1),
    "angular": ("Angular", 1),
    "cloudflare": ("Cloudflare", 1),
    "nginx": ("nginx", 1),
    "apache": ("Apache", 1),
    "iis": ("Microsoft IIS", 1),
}


def _result(module: str, started: float, **kwargs) -> IntelligenceModuleResult:
    return IntelligenceModuleResult(
        module=module,
        duration_ms=max(0, int((time.perf_counter() - started) * 1000)),
        **kwargs,
    )


def normalize_target(raw: str) -> tuple[str, str, str]:
    value = raw.strip()
    if not value:
        raise ValueError("A target is required.")
    parsed = urlparse(value if "://" in value else f"https://{value}")
    host = parsed.hostname or value.split("/")[0]
    host = host.strip("[]").rstrip(".")
    if not host:
        raise ValueError("The target could not be normalized.")
    scheme = parsed.scheme if parsed.scheme in {"http", "https"} else "https"
    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query
    return host, scheme, path


def dns_module(target: str, **_) -> IntelligenceModuleResult:
    started = time.perf_counter()
    try:
        records = socket.getaddrinfo(target, None, proto=socket.IPPROTO_TCP)
        addresses = sorted({item[4][0] for item in records})
        findings = tuple(
            IntelligenceFinding(
                title="Resolved address",
                detail=address,
                severity="INFO",
                confidence=95,
                node_kind="IP",
                metadata={"address": address},
            )
            for address in addresses
        )
        content = json.dumps({"target": target, "addresses": addresses}, indent=2)
        relationships = tuple(
            IntelligenceRelationship(f"target:{target}", f"ip:{address}", "resolves to", 95)
            for address in addresses
        )
        return _result(
            "dns", started,
            status="success",
            summary=f"Resolved {len(addresses)} address(es).",
            findings=findings,
            evidence=(IntelligenceEvidence("DNS", "DNS resolution", target, content),),
            relationships=relationships,
            risk=0,
            confidence=95 if addresses else 45,
        )
    except Exception as exc:
        return _result(
            "dns", started, status="error", summary="DNS resolution failed.",
            risk=0, confidence=0, error=str(exc)
        )


def reverse_dns_module(target: str, **_) -> IntelligenceModuleResult:
    started = time.perf_counter()
    try:
        ip_address(target)
    except ValueError:
        return _result(
            "reverse_dns", started, status="skipped",
            summary="Target is not an IP address.", risk=0, confidence=0
        )
    try:
        hostname, aliases, addresses = socket.gethostbyaddr(target)
        content = json.dumps(
            {"ip": target, "hostname": hostname, "aliases": aliases, "addresses": addresses},
            indent=2,
        )
        return _result(
            "reverse_dns", started, status="success",
            summary=f"Reverse name: {hostname}.",
            findings=(IntelligenceFinding("Reverse DNS", hostname, confidence=90, node_kind="DOMAIN"),),
            evidence=(IntelligenceEvidence("DNS", "Reverse DNS lookup", target, content),),
            relationships=(IntelligenceRelationship(f"ip:{target}", f"domain:{hostname}", "reverse resolves to", 90),),
            risk=0, confidence=90,
        )
    except Exception as exc:
        return _result(
            "reverse_dns", started, status="error",
            summary="No reverse DNS record was returned.", risk=0, confidence=25, error=str(exc)
        )


def whois_module(target: str, timeout: float = 7.0, **_) -> IntelligenceModuleResult:
    started = time.perf_counter()
    try:
        ip_address(target)
        return _result(
            "whois", started, status="skipped",
            summary="Domain WHOIS skipped for an IP target.", risk=0, confidence=0
        )
    except ValueError:
        pass

    query = target.encode("idna", errors="ignore") + b"\r\n"
    try:
        with socket.create_connection(("whois.iana.org", 43), timeout=timeout) as sock:
            sock.sendall(query)
            response = b""
            while len(response) < 180_000:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
        text = response.decode("utf-8", errors="replace")
        referral = re.search(r"(?im)^refer:\s*(\S+)", text)
        if referral:
            server = referral.group(1).strip()
            try:
                with socket.create_connection((server, 43), timeout=timeout) as sock:
                    sock.sendall(query)
                    response = b""
                    while len(response) < 250_000:
                        chunk = sock.recv(4096)
                        if not chunk:
                            break
                        response += chunk
                text = response.decode("utf-8", errors="replace")
            except OSError:
                pass

        registrar = re.search(r"(?im)^registrar:\s*(.+)$", text)
        created = re.search(r"(?im)^(?:creation date|created|registered on):\s*(.+)$", text)
        expires = re.search(r"(?im)^(?:registry expiry date|expiration date|expires):\s*(.+)$", text)
        summary_bits = []
        if registrar:
            summary_bits.append(f"registrar {registrar.group(1).strip()}")
        if created:
            summary_bits.append(f"created {created.group(1).strip()}")
        findings = []
        if created:
            findings.append(IntelligenceFinding("Domain creation", created.group(1).strip(), confidence=75, node_kind="WHOIS"))
        if expires:
            findings.append(IntelligenceFinding("Domain expiration", expires.group(1).strip(), confidence=75, node_kind="WHOIS"))
        return _result(
            "whois", started, status="success",
            summary="; ".join(summary_bits) if summary_bits else "WHOIS response collected.",
            findings=tuple(findings),
            evidence=(IntelligenceEvidence("WHOIS", "Domain registration record", target, text),),
            relationships=(IntelligenceRelationship(f"target:{target}", f"whois:{target}", "registered as", 80),),
            risk=0, confidence=75 if text.strip() else 30,
        )
    except Exception as exc:
        return _result(
            "whois", started, status="error", summary="WHOIS lookup failed.",
            risk=0, confidence=0, error=str(exc)
        )


def ssl_module(target: str, timeout: float = 7.0, **_) -> IntelligenceModuleResult:
    started = time.perf_counter()
    try:
        ip_address(target)
        server_hostname = None
    except ValueError:
        server_hostname = target
    try:
        context = ssl.create_default_context()
        with socket.create_connection((target, 443), timeout=timeout) as raw:
            with context.wrap_socket(raw, server_hostname=server_hostname or target) as wrapped:
                cert = wrapped.getpeercert()
                cipher = wrapped.cipher()
                version = wrapped.version()
        not_after = cert.get("notAfter", "")
        not_before = cert.get("notBefore", "")
        subject = dict(item[0] for item in cert.get("subject", ()))
        issuer = dict(item[0] for item in cert.get("issuer", ()))
        san = [value for kind, value in cert.get("subjectAltName", ()) if kind == "DNS"]
        risk = 0
        findings = []
        if not_after:
            expiry = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
            days = (expiry - datetime.now(timezone.utc)).days
            if days < 0:
                risk = 25
                findings.append(IntelligenceFinding("Expired TLS certificate", f"Expired {-days} day(s) ago.", "HIGH", 25, 98, "SSL"))
            elif days <= 14:
                risk = 12
                findings.append(IntelligenceFinding("TLS certificate expires soon", f"{days} day(s) remaining.", "MEDIUM", 12, 95, "SSL"))
            else:
                findings.append(IntelligenceFinding("TLS certificate validity", f"{days} day(s) remaining.", "INFO", 0, 95, "SSL"))
        payload = {
            "subject": subject,
            "issuer": issuer,
            "not_before": not_before,
            "not_after": not_after,
            "subject_alt_names": san,
            "protocol": version,
            "cipher": cipher,
        }
        return _result(
            "ssl", started, status="success",
            summary=f"{version or 'TLS'} certificate for {subject.get('commonName', target)}.",
            findings=tuple(findings),
            evidence=(IntelligenceEvidence("SSL", "TLS certificate analysis", target, json.dumps(payload, indent=2, default=str)),),
            relationships=(IntelligenceRelationship(f"target:{target}", f"ssl:{target}", "presents certificate", 95),),
            risk=risk, confidence=96,
        )
    except ssl.SSLCertVerificationError as exc:
        return _result(
            "ssl", started, status="error", summary="TLS verification failed.",
            findings=(IntelligenceFinding("TLS verification failure", str(exc), "HIGH", 20, 95, "SSL"),),
            evidence=(IntelligenceEvidence("SSL", "TLS verification error", target, str(exc)),),
            risk=20, confidence=95, error=str(exc)
        )
    except Exception as exc:
        return _result(
            "ssl", started, status="error", summary="TLS service was unavailable.",
            risk=0, confidence=20, error=str(exc)
        )


def _http_fetch(target: str, scheme: str, path: str, timeout: float) -> tuple[int, dict[str, str], bytes, str]:
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,*/*;q=0.8"}
    conn_cls = HTTPSConnection if scheme == "https" else HTTPConnection
    conn = conn_cls(target, timeout=timeout)
    try:
        conn.request("GET", path or "/", headers=headers)
        response = conn.getresponse()
        body = response.read(300_000)
        response_headers = {key.lower(): value for key, value in response.getheaders()}
        return response.status, response_headers, body, response.reason
    finally:
        conn.close()


def http_module(target: str, scheme: str = "https", path: str = "/", timeout: float = 8.0, **_) -> IntelligenceModuleResult:
    started = time.perf_counter()
    attempts = [scheme] + (["http"] if scheme == "https" else ["https"])
    last_error = None
    for current_scheme in dict.fromkeys(attempts):
        try:
            status, headers, body, reason = _http_fetch(target, current_scheme, path, timeout)
            break
        except Exception as exc:
            last_error = exc
    else:
        return _result(
            "http", started, status="error", summary="HTTP collection failed.",
            risk=0, confidence=0, error=str(last_error)
        )

    security_headers = {
        "strict-transport-security": 4,
        "content-security-policy": 4,
        "x-content-type-options": 2,
        "x-frame-options": 2,
        "referrer-policy": 1,
        "permissions-policy": 1,
    }
    missing = [name for name in security_headers if name not in headers]
    risk = min(15, sum(security_headers[name] for name in missing))
    findings = [
        IntelligenceFinding("HTTP status", f"{status} {reason}", confidence=95, node_kind="HEADERS")
    ]
    if missing:
        findings.append(
            IntelligenceFinding(
                "Missing defensive HTTP headers",
                ", ".join(missing),
                "LOW" if risk < 8 else "MEDIUM",
                risk,
                80,
                "HEADERS",
            )
        )
    server = headers.get("server")
    if server:
        findings.append(IntelligenceFinding("Server header", server, confidence=85, node_kind="TECHNOLOGY"))
    powered = headers.get("x-powered-by")
    if powered:
        findings.append(IntelligenceFinding("Technology disclosure", powered, "LOW", 2, 85, "TECHNOLOGY"))

    content = json.dumps(
        {"scheme": current_scheme, "status": status, "reason": reason, "headers": headers},
        indent=2,
    )
    return _result(
        "http", started, status="success",
        summary=f"{current_scheme.upper()} returned {status}; {len(missing)} defensive header(s) missing.",
        findings=tuple(findings),
        evidence=(
            IntelligenceEvidence("HEADERS", "HTTP response headers", f"{current_scheme}://{target}{path}", content),
            IntelligenceEvidence("HTML", "HTTP response sample", f"{current_scheme}://{target}{path}", body.decode("utf-8", errors="replace")),
        ),
        relationships=(IntelligenceRelationship(f"target:{target}", f"http:{target}", "serves", 95),),
        risk=risk, confidence=90,
    )


def technology_module(target: str, prior_results=(), **_) -> IntelligenceModuleResult:
    started = time.perf_counter()
    text_parts = []
    for result in prior_results:
        if result.module != "http":
            continue
        for evidence in result.evidence:
            text_parts.extend([evidence.content, evidence.source])
    haystack = "\n".join(text_parts).lower()
    detected: dict[str, int] = {}
    for signature, (name, weight) in TECH_SIGNATURES.items():
        if signature in haystack:
            detected[name] = max(detected.get(name, 0), weight)
    findings = tuple(
        IntelligenceFinding("Technology detected", name, "INFO", weight, 70, "TECHNOLOGY")
        for name, weight in sorted(detected.items())
    )
    return _result(
        "technology", started,
        status="success" if detected else "skipped",
        summary=", ".join(sorted(detected)) if detected else "No high-confidence technology signature detected.",
        findings=findings,
        evidence=(IntelligenceEvidence("TECHNOLOGY", "Technology fingerprint", target, json.dumps(sorted(detected), indent=2)),) if detected else (),
        relationships=tuple(
            IntelligenceRelationship(f"target:{target}", f"technology:{name}", "uses", 72)
            for name in detected
        ),
        risk=min(8, sum(detected.values())), confidence=72 if detected else 30,
    )


BUILTIN_MODULES: tuple[tuple[str, Callable[..., IntelligenceModuleResult]], ...] = (
    ("dns", dns_module),
    ("reverse_dns", reverse_dns_module),
    ("whois", whois_module),
    ("ssl", ssl_module),
    ("http", http_module),
    ("technology", technology_module),
)
