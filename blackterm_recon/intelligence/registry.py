from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from .models import IntelligenceModuleResult


ModuleCallable = Callable[..., IntelligenceModuleResult]


@dataclass(frozen=True, slots=True)
class IntelligenceModuleSpec:
    """Metadata used by the core engine to schedule an intelligence module."""

    name: str
    handler: ModuleCallable
    dependencies: tuple[str, ...] = ()
    passive: bool = True
    description: str = ""


class IntelligenceRegistry:
    """Small dependency-aware registry for built-in and future intelligence modules."""

    def __init__(self, modules: Iterable[IntelligenceModuleSpec] = ()):
        self._modules: dict[str, IntelligenceModuleSpec] = {}
        for module in modules:
            self.register(module)

    def register(self, module: IntelligenceModuleSpec, *, replace: bool = False) -> None:
        key = module.name.strip().lower()
        if not key:
            raise ValueError("Intelligence module names cannot be empty.")
        if key in self._modules and not replace:
            raise ValueError(f"Intelligence module already registered: {key}")
        self._modules[key] = IntelligenceModuleSpec(
            name=key,
            handler=module.handler,
            dependencies=tuple(item.strip().lower() for item in module.dependencies),
            passive=module.passive,
            description=module.description,
        )

    def names(self) -> tuple[str, ...]:
        return tuple(self._modules)

    def get(self, name: str) -> IntelligenceModuleSpec:
        try:
            return self._modules[name.strip().lower()]
        except KeyError as exc:
            raise KeyError(f"Unknown intelligence module: {name}") from exc

    def resolve(self, enabled: Iterable[str] | None = None) -> tuple[tuple[IntelligenceModuleSpec, ...], ...]:
        """Return dependency-safe execution stages.

        Modules within a stage may execute concurrently. Dependency modules are
        automatically included so a request for ``technology`` also includes its
        required evidence producers when they are registered.
        """

        requested = set(self.names() if enabled is None else (item.lower() for item in enabled))
        unknown = requested - set(self._modules)
        if unknown:
            raise ValueError("Unknown intelligence module(s): " + ", ".join(sorted(unknown)))

        expanded = set(requested)
        pending = list(requested)
        while pending:
            current = pending.pop()
            for dependency in self._modules[current].dependencies:
                if dependency not in self._modules:
                    raise ValueError(f"Module {current} depends on unregistered module {dependency}.")
                if dependency not in expanded:
                    expanded.add(dependency)
                    pending.append(dependency)

        stages: list[tuple[IntelligenceModuleSpec, ...]] = []
        completed: set[str] = set()
        while completed != expanded:
            ready = tuple(
                self._modules[name]
                for name in self._modules
                if name in expanded
                and name not in completed
                and set(self._modules[name].dependencies).issubset(completed)
            )
            if not ready:
                unresolved = sorted(expanded - completed)
                raise ValueError("Circular intelligence module dependency: " + ", ".join(unresolved))
            stages.append(ready)
            completed.update(module.name for module in ready)
        return tuple(stages)
