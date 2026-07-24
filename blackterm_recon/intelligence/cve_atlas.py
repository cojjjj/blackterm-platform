from __future__ import annotations

import json
import re
import sqlite3
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

NVD_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
CISA_KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
USER_AGENT = "BLACKTERM-Vulnerability-Intelligence/1.1"


@dataclass(slots=True)
class CVERecord:
    cve_id: str
    description: str
    published: str = ""
    modified: str = ""
    severity: str = "UNKNOWN"
    score: float | None = None
    vector: str = ""
    weaknesses: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    affected: list[str] = field(default_factory=list)
    kev: bool = False
    kev_details: dict[str, Any] = field(default_factory=dict)

    @property
    def mechanism(self) -> str:
        text = self.description.lower()
        patterns = [
            (("buffer overflow", "out-of-bounds", "memory corruption"), "Crafted input can cross a memory boundary. Depending on the component and protections in place, that may crash the process, disclose memory, or alter execution."),
            (("command injection", "os command injection"), "Attacker-controlled input reaches an operating-system command context without being safely separated from command syntax."),
            (("sql injection",), "Attacker-controlled input can change the structure of a database query because data and SQL instructions are not safely separated."),
            (("cross-site scripting", " xss", "stored xss", "reflected xss"), "Untrusted content can be interpreted as browser script in another user's session instead of being displayed only as text."),
            (("path traversal", "directory traversal"), "A crafted file path can escape the intended directory and reach files or locations that should not be accessible."),
            (("deserialization",), "Untrusted serialized content is reconstructed into objects in a way that can trigger unsafe behavior during parsing or object creation."),
            (("authentication bypass",), "A flaw in an authentication decision allows a request to pass without completing the intended identity checks."),
            (("use-after-free",), "The software continues to use memory after it has been released, which can cause corruption and may enable attacker-controlled execution."),
            (("privilege escalation", "elevation of privilege"), "A user or process can cross a trust boundary and gain permissions beyond those originally granted."),
            (("information disclosure", "sensitive information", "data exposure"), "The vulnerable path can return or reveal information that the requester should not be able to access."),
            (("server-side request forgery", "ssrf"), "The server can be induced to make a request chosen by an attacker, potentially reaching internal services or trusted destinations."),
            (("race condition", "time-of-check"), "Two operations can occur in an unsafe order, allowing state to change between a security check and the action that relies on it."),
            (("denial of service", "resource exhaustion"), "Crafted input or repeated requests can force excessive work, memory use, or failure and reduce availability."),
        ]
        padded = f" {text}"
        for needles, explanation in patterns:
            if any(n in padded for n in needles):
                return explanation
        return "The affected component mishandles an attacker-controlled condition, allowing the security impact described by the vendor and CVE record."

    @property
    def beginner_explanation(self) -> str:
        text = self.description.lower()
        if "cross-site scripting" in text or "xss" in text:
            return "A website is supposed to show user-provided text as text. This bug can make the browser treat that text like trusted code, so the code runs when another user opens the affected page."
        if "sql injection" in text:
            return "The application mixes a user's input directly into a database instruction. A malicious user may be able to change what the database command means instead of only supplying normal data."
        if "command injection" in text:
            return "The application passes user-controlled text into a system command. Special characters can make the computer interpret part of that input as a new command."
        if "path traversal" in text or "directory traversal" in text:
            return "The program expects a path inside one folder, but a specially formed path may climb out of that folder and reach files elsewhere on the system."
        if "authentication bypass" in text:
            return "A protected door is checking the wrong thing. Under certain conditions, a request can get through without proving the user is allowed inside."
        if "buffer overflow" in text or "out-of-bounds" in text:
            return "The program receives more or different data than a memory area was designed to hold. That can overwrite nearby memory and change how the program behaves."
        if "denial of service" in text:
            return "A specially formed request can make the service use too many resources or crash, preventing legitimate users from using it."
        return "A normal security assumption inside the affected software can be broken with specially prepared input. The exact result depends on the product, version, configuration, and attacker access described in the advisory."

    @property
    def attack_flow(self) -> list[str]:
        text = self.description.lower()
        entry = "Local user or authenticated user"
        if any(x in text for x in ("remote attacker", "network", "http", "web", "unauthenticated")):
            entry = "Remote attacker"
        component = self.product_summary or "Affected component"
        if "cross-site scripting" in text or "xss" in text:
            return [entry, "Crafted web input", component, "Unsafe output rendering", "Script executes in victim browser"]
        if "sql injection" in text:
            return [entry, "Crafted application input", component, "Unsafe database query", "Unauthorized data access or modification"]
        if "command injection" in text:
            return [entry, "Crafted input", component, "Input reaches shell context", "Operating-system command execution"]
        if "path traversal" in text or "directory traversal" in text:
            return [entry, "Crafted file path", component, "Path escapes intended directory", "Unauthorized file access"]
        if "authentication bypass" in text:
            return [entry, "Manipulated request", component, "Authentication decision fails", "Unauthorized access"]
        return [entry, "Crafted condition or input", component, "Vulnerable code path", self.impact_summary]

    @property
    def impact_summary(self) -> str:
        text = self.description.lower()
        impacts = [
            (("remote code execution", "arbitrary code", "execute code"), "Code execution"),
            (("privilege escalation", "elevation of privilege"), "Privilege escalation"),
            (("information disclosure", "sensitive information"), "Information disclosure"),
            (("denial of service",), "Service disruption"),
            (("cross-site scripting", "xss"), "Browser-side code execution"),
            (("authentication bypass",), "Authentication bypass"),
            (("arbitrary file", "path traversal", "directory traversal"), "Unauthorized file access"),
        ]
        for needles, impact in impacts:
            if any(n in text for n in needles):
                return impact
        return "Security impact described by advisory"

    @property
    def product_summary(self) -> str:
        if not self.affected:
            return ""
        value = self.affected[0]
        parts = value.split(":")
        if len(parts) >= 6:
            vendor = parts[3].replace("_", " ").title()
            product = parts[4].replace("_", " ").title()
            return f"{vendor} {product}".strip()
        return ""

    @property
    def mitre_techniques(self) -> list[tuple[str, str]]:
        text = self.description.lower()
        techniques: list[tuple[str, str]] = []
        if any(x in text for x in ("remote", "web", "http", "network")):
            techniques.append(("T1190", "Exploit Public-Facing Application"))
        if any(x in text for x in ("command injection", "arbitrary command", "execute code", "code execution")):
            techniques.append(("T1059", "Command and Scripting Interpreter"))
        if any(x in text for x in ("credential", "password", "authentication bypass")):
            techniques.append(("T1078", "Valid Accounts / Access Control Abuse"))
        if any(x in text for x in ("information disclosure", "sensitive information", "data exposure")):
            techniques.append(("T1213", "Data from Information Repositories"))
        if any(x in text for x in ("privilege escalation", "elevation of privilege")):
            techniques.append(("T1068", "Exploitation for Privilege Escalation"))
        return techniques[:4]

    @property
    def detection_ideas(self) -> list[str]:
        text = self.description.lower()
        ideas = ["Inventory the affected product and confirm the exact deployed version and exposure."]
        if any(x in text for x in ("http", "web", "cross-site", "sql injection", "path traversal")):
            ideas.append("Review web, reverse-proxy, and WAF logs for unusual parameters, encoding, traversal patterns, or repeated errors.")
        if any(x in text for x in ("command", "code execution", "remote code")):
            ideas.append("Correlate application requests with unexpected child processes, shell execution, scripting engines, and outbound connections.")
        if "authentication bypass" in text:
            ideas.append("Hunt for successful sessions without the expected authentication sequence, token issuance, or identity-provider event.")
        if "information disclosure" in text:
            ideas.append("Review access logs and data-loss telemetry for abnormal reads, bulk responses, or sensitive endpoints accessed by unusual identities.")
        ideas.append("Compare observed activity with vendor-provided indicators and validate detections in an isolated test environment.")
        return ideas

    @property
    def defensive_actions(self) -> list[str]:
        actions = ["Apply the vendor patch or upgrade to a fixed release."]
        if self.kev:
            actions.insert(0, "Prioritize remediation: CISA lists this vulnerability as exploited in the wild.")
        if any(x in self.description.lower() for x in ("network", "remote", "http", "web")):
            actions.append("Reduce exposure with segmentation, allowlists, VPN access, or a reverse proxy until patching is complete.")
        actions.append("Review the vendor advisory for configuration-specific mitigations and affected version details.")
        actions.append("After remediation, verify the installed version and repeat only safe validation checks in an authorized environment.")
        return actions


class CVEAtlasClient:
    def __init__(self, cache_path: str | Path | None = None, timeout: int = 20):
        self.timeout = timeout
        if cache_path is None:
            cache_path = Path.home() / ".blackterm" / "cve_atlas.sqlite3"
        self.cache_path = Path(cache_path)
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._kev_cache: dict[str, dict[str, Any]] | None = None

    def _connect(self):
        return sqlite3.connect(self.cache_path)

    def _init_db(self):
        with self._connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS cve_cache (cache_key TEXT PRIMARY KEY, payload TEXT NOT NULL, saved_at INTEGER NOT NULL)")

    def _request_json(self, url: str) -> dict[str, Any]:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def _cache_get(self, key: str, max_age: int) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute("SELECT payload, saved_at FROM cve_cache WHERE cache_key=?", (key,)).fetchone()
        if not row or int(time.time()) - row[1] > max_age:
            return None
        return json.loads(row[0])

    def _cache_put(self, key: str, payload: dict[str, Any]):
        with self._connect() as db:
            db.execute("INSERT OR REPLACE INTO cve_cache(cache_key,payload,saved_at) VALUES(?,?,?)", (key, json.dumps(payload), int(time.time())))

    def _fetch(self, key: str, url: str, max_age: int = 21600) -> dict[str, Any]:
        cached = self._cache_get(key, max_age)
        if cached is not None:
            return cached
        payload = self._request_json(url)
        self._cache_put(key, payload)
        return payload

    def _load_kev(self) -> dict[str, dict[str, Any]]:
        if self._kev_cache is not None:
            return self._kev_cache
        try:
            payload = self._fetch("cisa-kev", CISA_KEV_URL, 43200)
            self._kev_cache = {item.get("cveID", "").upper(): item for item in payload.get("vulnerabilities", [])}
        except Exception:
            self._kev_cache = {}
        return self._kev_cache

    def lookup(self, cve_id: str) -> CVERecord:
        cve_id = cve_id.strip().upper()
        if not re.fullmatch(r"CVE-\d{4}-\d{4,}", cve_id):
            raise ValueError("Enter a CVE ID such as CVE-2024-3094.")
        url = f"{NVD_URL}?{urllib.parse.urlencode({'cveId': cve_id})}"
        payload = self._fetch(f"cve:{cve_id}", url)
        items = payload.get("vulnerabilities", [])
        if not items:
            raise LookupError(f"No NVD record found for {cve_id}.")
        return self._parse(items[0].get("cve", {}))

    def search(self, keyword: str, limit: int = 50) -> list[CVERecord]:
        keyword = keyword.strip()
        if not keyword:
            raise ValueError("Enter a CVE ID, vendor, product, or vulnerability keyword.")
        if keyword.upper().startswith("CVE-"):
            return [self.lookup(keyword)]
        params = urllib.parse.urlencode({"keywordSearch": keyword, "resultsPerPage": max(1, min(limit, 100))})
        payload = self._fetch(f"search:{keyword.lower()}:{limit}", f"{NVD_URL}?{params}", 10800)
        return [self._parse(item.get("cve", {})) for item in payload.get("vulnerabilities", [])]

    def latest(self, limit: int = 50) -> list[CVERecord]:
        params = urllib.parse.urlencode({"resultsPerPage": max(1, min(limit, 100))})
        payload = self._fetch(f"latest:{limit}", f"{NVD_URL}?{params}", 3600)
        records = [self._parse(item.get("cve", {})) for item in payload.get("vulnerabilities", [])]
        return sorted(records, key=lambda r: r.published, reverse=True)

    def _parse(self, cve: dict[str, Any]) -> CVERecord:
        descriptions = cve.get("descriptions", [])
        description = next((d.get("value", "") for d in descriptions if d.get("lang") == "en"), "")
        metrics = cve.get("metrics", {})
        metric = None
        for key in ("cvssMetricV40", "cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
            if metrics.get(key):
                metric = metrics[key][0]
                break
        cvss = (metric or {}).get("cvssData", {})
        weaknesses: list[str] = []
        for group in cve.get("weaknesses", []):
            for item in group.get("description", []):
                value = item.get("value")
                if value and value not in weaknesses:
                    weaknesses.append(value)
        affected: list[str] = []
        for config in cve.get("configurations", []):
            for node in config.get("nodes", []):
                for match in node.get("cpeMatch", []):
                    criteria = match.get("criteria", "")
                    if criteria and criteria not in affected:
                        affected.append(criteria)
        cve_id = cve.get("id", "UNKNOWN")
        kev_details = self._load_kev().get(cve_id.upper(), {})
        return CVERecord(
            cve_id=cve_id,
            description=description or "No English description is available.",
            published=cve.get("published", ""),
            modified=cve.get("lastModified", ""),
            severity=cvss.get("baseSeverity") or (metric or {}).get("baseSeverity", "UNKNOWN"),
            score=cvss.get("baseScore"),
            vector=cvss.get("vectorString", ""),
            weaknesses=weaknesses,
            references=[r.get("url", "") for r in cve.get("references", []) if r.get("url")],
            affected=affected[:30],
            kev=bool(kev_details),
            kev_details=kev_details,
        )
