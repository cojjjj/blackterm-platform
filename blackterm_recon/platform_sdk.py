from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol, Any


@dataclass(frozen=True, slots=True)
class ModuleManifest:
    key: str
    name: str
    version: str
    description: str
    category: str
    entrypoint: str
    enabled: bool = True


class PlatformModule(Protocol):
    manifest: ModuleManifest

    def create_page(self, context: Any):
        """Return a QWidget-compatible page for the platform shell."""


@dataclass(slots=True)
class PlatformContext:
    engine: Any
    logger: Any
    navigate: Callable[[str], None]


def validate_manifest(manifest: ModuleManifest) -> None:
    if not manifest.key or " " in manifest.key:
        raise ValueError("module key must be non-empty and contain no spaces")
    if not manifest.name:
        raise ValueError("module name is required")
    if not manifest.entrypoint:
        raise ValueError("module entrypoint is required")
