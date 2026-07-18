from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class PortResult:
    port: int
    state: str
    service: str = "unknown"
    latency_ms: float | None = None
    banner: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ScanResult:
    target: str
    ip: str
    ports: list[PortResult]
    started_at: str
    finished_at: str
    duration_seconds: float
    hostname: str | None = None
    plugin_results: dict[str, Any] = field(default_factory=dict)

    @property
    def open_ports(self) -> list[PortResult]:
        return [item for item in self.ports if item.state == "open"]

    @property
    def average_open_latency(self) -> float:
        values = [
            item.latency_ms
            for item in self.open_ports
            if item.latency_ms is not None
        ]
        return round(sum(values) / len(values), 2) if values else 0.0

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["open_port_count"] = len(self.open_ports)
        return data


@dataclass(slots=True)
class ScanContext:
    result: ScanResult
    config: Any
