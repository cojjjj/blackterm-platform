from __future__ import annotations

from dataclasses import dataclass

from .ports import parse_ports


@dataclass(frozen=True, slots=True)
class ScanProfile:
    key: str
    name: str
    description: str
    ports: str
    timeout: float
    workers: int
    banners: bool

    def resolved_ports(self) -> list[int]:
        return parse_ports(self.ports)


SCAN_PROFILES: dict[str, ScanProfile] = {
    "quick": ScanProfile(
        key="quick",
        name="Quick",
        description="Fast visibility check of the most common services.",
        ports="22,80,443,445,3389,8080",
        timeout=0.30,
        workers=80,
        banners=False,
    ),
    "standard": ScanProfile(
        key="standard",
        name="Standard",
        description="Balanced authorized assessment with common ports and banners.",
        ports="common",
        timeout=0.50,
        workers=100,
        banners=True,
    ),
    "full": ScanProfile(
        key="full",
        name="Full",
        description="Broader TCP assessment intended for controlled lab environments.",
        ports="1-1024,1433,1521,2049,2375,3000,3306,3389,5432,5900,6379,8000,8080,8443,9200",
        timeout=0.70,
        workers=160,
        banners=True,
    ),
    "custom": ScanProfile(
        key="custom",
        name="Custom",
        description="Use the ports and options selected by the operator.",
        ports="common",
        timeout=0.50,
        workers=100,
        banners=False,
    ),
}


def get_profile(key: str) -> ScanProfile:
    normalized = (key or "standard").strip().lower()
    if normalized not in SCAN_PROFILES:
        raise ValueError(f"Unknown scan profile: {key}")
    return SCAN_PROFILES[normalized]
