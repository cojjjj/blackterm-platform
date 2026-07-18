from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SecurityModule:
    key: str
    title: str
    description: str
    status: str
    command: str | None = None
    category: str = "SECURITY"


MODULES = [
    SecurityModule(
        "recon", "RECON",
        "Authorized host visibility, live intelligence, cases, reports, and analysis.",
        "ACTIVE", "LIVE SCAN", "NETWORK",
    ),
    SecurityModule(
        "phishscan", "PHISHSCAN",
        "URL inspection, DNS, certificate, reputation, and screenshot intelligence.",
        "INTEGRATION SLOT", None, "WEB",
    ),
    SecurityModule(
        "osint", "OSINT",
        "Public-source collection workspace with source tracking and evidence notes.",
        "SDK READY", None, "INTELLIGENCE",
    ),
    SecurityModule(
        "forensics", "FORENSICS",
        "Artifact triage, metadata, hashes, timelines, and case organization.",
        "SDK READY", None, "INVESTIGATION",
    ),
    SecurityModule(
        "hashlab", "HASHLAB",
        "Hash identification, integrity verification, and safe comparison workflows.",
        "SDK READY", None, "ANALYSIS",
    ),
    SecurityModule(
        "pcap", "PCAP ANALYZER",
        "Packet summaries, protocol statistics, and conversation views.",
        "SDK READY", None, "NETWORK",
    ),
    SecurityModule(
        "threat", "THREAT INTELLIGENCE",
        "Indicator enrichment, relationships, confidence, and source-aware summaries.",
        "SDK READY", None, "INTELLIGENCE",
    ),
]
