from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Callable, Iterable

from .models import (
    IntelligenceEvidence,
    IntelligenceFinding,
    IntelligenceModuleResult,
    IntelligenceRunResult,
)
from .modules import BUILTIN_MODULES, normalize_target
from .registry import IntelligenceModuleSpec, IntelligenceRegistry


ProgressCallback = Callable[[str, int, str, IntelligenceModuleResult | None], None]


def _level(score: int) -> str:
    if score >= 80:
        return "CRITICAL"
    if score >= 55:
        return "HIGH"
    if score >= 30:
        return "MODERATE"
    return "LOW"


def default_registry() -> IntelligenceRegistry:
    handlers = dict(BUILTIN_MODULES)
    specs = []
    for name, handler in BUILTIN_MODULES:
        dependencies: tuple[str, ...] = ()
        if name in {"asn", "geoip"}:
            dependencies = ("dns",)
        elif name == "technology":
            # Technology analysis consumes HTTP and/or imported scan evidence.
            dependencies = ("http",)
        specs.append(
            IntelligenceModuleSpec(
                name=name,
                handler=handler,
                dependencies=dependencies,
                passive=True,
                description=f"BLACKTERM built-in {name} intelligence module.",
            )
        )
    return IntelligenceRegistry(specs)


class IntelligenceEngine:
    """Dependency-aware, authorized-use passive intelligence orchestration engine.

    The engine accepts optional scanner context so every BLACKTERM surface can
    consume one normalized result instead of independently recalculating data.
    """

    def __init__(
        self,
        *,
        timeout: float = 8.0,
        max_workers: int = 5,
        registry: IntelligenceRegistry | None = None,
    ):
        self.timeout = max(2.0, float(timeout))
        self.max_workers = max(1, min(8, int(max_workers)))
        self.registry = registry or default_registry()

    def run(
        self,
        raw_target: str,
        *,
        enabled_modules: Iterable[str] | None = None,
        progress: ProgressCallback | None = None,
        scan_result: Any | None = None,
        attack_surface: Any | None = None,
        context: dict[str, Any] | None = None,
    ) -> IntelligenceRunResult:
        host, scheme, path = normalize_target(raw_target)
        started_at = datetime.now(timezone.utc).isoformat()
        stages = self.registry.resolve(enabled_modules)
        total = sum(len(stage) for stage in stages)
        completed = 0
        results: dict[str, IntelligenceModuleResult] = {}
        shared_context = dict(context or {})
        shared_context.update(
            {
                "scan_result": scan_result,
                "attack_surface": attack_surface,
            }
        )

        if progress:
            progress("pipeline", 0, f"Intelligence pipeline started for {host}.", None)

        for stage in stages:
            with ThreadPoolExecutor(max_workers=min(self.max_workers, max(1, len(stage)))) as pool:
                futures = {}
                for spec in stage:
                    if progress:
                        progress(spec.name, int(completed / max(1, total) * 100), "Module started.", None)
                    kwargs = {
                        "scheme": scheme,
                        "path": path,
                        "timeout": self.timeout,
                        "prior_results": tuple(results.values()),
                        **shared_context,
                    }
                    futures[pool.submit(spec.handler, host, **kwargs)] = spec

                for future in as_completed(futures):
                    spec = futures[future]
                    try:
                        result = future.result()
                    except Exception as exc:
                        result = IntelligenceModuleResult(
                            module=spec.name,
                            status="error",
                            summary=f"{spec.name} raised an unexpected error.",
                            error=str(exc),
                        )
                    results[spec.name] = result
                    completed += 1
                    if progress:
                        progress(
                            spec.name,
                            int(completed / max(1, total) * 100),
                            result.summary,
                            result,
                        )

        ordered_names = [spec.name for stage in stages for spec in stage]
        ordered = tuple(results[name] for name in ordered_names if name in results)
        successful = [item for item in ordered if item.successful]
        risk_values = [item.risk for item in ordered if item.status != "skipped"]
        # Avoid double-counting multiple views of the same evidence. The largest
        # module risk is primary; additional modules add limited corroboration.
        sorted_risk = sorted(risk_values, reverse=True)
        risk_score = min(100, (sorted_risk[0] if sorted_risk else 0) + sum(sorted_risk[1:]) // 3)
        source_confidence = [item.confidence for item in successful if item.confidence]
        confidence = (
            min(98, int(sum(source_confidence) / len(source_confidence)) + min(10, len(successful)))
            if source_confidence else 25
        )
        level = _level(risk_score)
        errors = sum(1 for item in ordered if item.status == "error")
        summary = (
            f"BLACKTERM completed {len(ordered)} intelligence module(s) for {host}. "
            f"{len(successful)} completed successfully, producing "
            f"{sum(len(item.findings) for item in ordered)} finding(s), "
            f"{sum(len(item.evidence) for item in ordered)} evidence item(s), and "
            f"{sum(len(item.relationships) for item in ordered)} relationship(s). "
            f"Current priority is {level} with {confidence}% confidence."
        )
        if errors:
            summary += f" {errors} module(s) require review or retry."

        operation_id = getattr(scan_result, "operation_id", None)
        result_context = {
            key: value
            for key, value in shared_context.items()
            if key not in {"scan_result", "attack_surface"} and value is not None
        }
        result_context.update(
            {
                "source": "scan" if scan_result is not None else "standalone",
                "module_order": ordered_names,
            }
        )
        result = IntelligenceRunResult(
            target=raw_target,
            normalized_target=host,
            started_at=started_at,
            completed_at=datetime.now(timezone.utc).isoformat(),
            modules=ordered,
            risk_score=risk_score,
            confidence=confidence,
            level=level,
            summary=summary,
            operation_id=operation_id,
            context=result_context,
        )
        if progress:
            progress("pipeline", 100, "Intelligence pipeline complete.", None)
        return result

    def run_for_scan(
        self,
        scan_result: Any,
        *,
        enabled_modules: Iterable[str] = ("scan_context",),
        progress: ProgressCallback | None = None,
    ) -> IntelligenceRunResult:
        """Normalize an existing scan into BLACKTERM's shared intelligence model."""
        return self.run(
            getattr(scan_result, "target", ""),
            enabled_modules=enabled_modules,
            progress=progress,
            scan_result=scan_result,
            attack_surface=getattr(scan_result, "attack_surface", None),
            context={"profile": getattr(scan_result, "profile", "custom")},
        )


__all__ = [
    "IntelligenceEngine",
    "IntelligenceModuleResult",
    "IntelligenceRunResult",
    "IntelligenceFinding",
    "IntelligenceEvidence",
    "IntelligenceModuleSpec",
    "IntelligenceRegistry",
    "default_registry",
]
