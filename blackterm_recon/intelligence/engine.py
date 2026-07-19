from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Callable, Iterable

from .models import (
    IntelligenceEvidence,
    IntelligenceFinding,
    IntelligenceModuleResult,
    IntelligenceRunResult,
)
from .modules import BUILTIN_MODULES, normalize_target


ProgressCallback = Callable[[str, int, str, IntelligenceModuleResult | None], None]


def _level(score: int) -> str:
    if score >= 80:
        return "CRITICAL"
    if score >= 55:
        return "HIGH"
    if score >= 30:
        return "MODERATE"
    return "LOW"


class IntelligenceEngine:
    """Authorized-use passive intelligence orchestration engine."""

    def __init__(self, *, timeout: float = 8.0, max_workers: int = 5):
        self.timeout = max(2.0, float(timeout))
        self.max_workers = max(1, min(8, int(max_workers)))

    def run(
        self,
        raw_target: str,
        *,
        enabled_modules: Iterable[str] | None = None,
        progress: ProgressCallback | None = None,
    ) -> IntelligenceRunResult:
        host, scheme, path = normalize_target(raw_target)
        started_at = datetime.now(timezone.utc).isoformat()
        allowed = {name for name, _ in BUILTIN_MODULES}
        enabled = set(enabled_modules or allowed) & allowed
        module_map = dict(BUILTIN_MODULES)
        results: dict[str, IntelligenceModuleResult] = {}

        independent = [name for name in ("dns", "reverse_dns", "whois", "ssl", "http") if name in enabled]
        total = len(independent) + (1 if "technology" in enabled else 0)
        completed = 0

        if progress:
            progress("pipeline", 0, f"Intelligence pipeline started for {host}.", None)

        with ThreadPoolExecutor(max_workers=min(self.max_workers, max(1, len(independent)))) as pool:
            futures = {
                pool.submit(
                    module_map[name],
                    host,
                    scheme=scheme,
                    path=path,
                    timeout=self.timeout,
                ): name
                for name in independent
            }
            for future in as_completed(futures):
                name = futures[future]
                try:
                    result = future.result()
                except Exception as exc:
                    result = IntelligenceModuleResult(
                        module=name,
                        status="error",
                        summary=f"{name} raised an unexpected error.",
                        error=str(exc),
                    )
                results[name] = result
                completed += 1
                if progress:
                    progress(
                        name,
                        int(completed / max(1, total) * 100),
                        result.summary,
                        result,
                    )

        if "technology" in enabled:
            result = module_map["technology"](
                host,
                scheme=scheme,
                path=path,
                timeout=self.timeout,
                prior_results=tuple(results.values()),
            )
            results["technology"] = result
            completed += 1
            if progress:
                progress(
                    "technology",
                    int(completed / max(1, total) * 100),
                    result.summary,
                    result,
                )

        ordered = tuple(results[name] for name, _ in BUILTIN_MODULES if name in results)
        successful = [item for item in ordered if item.successful]
        risk_values = [item.risk for item in ordered if item.status != "skipped"]
        risk_score = min(100, sum(risk_values))
        source_confidence = [item.confidence for item in successful if item.confidence]
        confidence = (
            min(98, int(sum(source_confidence) / len(source_confidence)) + min(12, len(successful) * 2))
            if source_confidence else 25
        )
        level = _level(risk_score)
        errors = sum(1 for item in ordered if item.status == "error")
        summary = (
            f"BLACKTERM completed {len(ordered)} intelligence module(s) for {host}. "
            f"{len(successful)} completed successfully, producing "
            f"{sum(len(item.findings) for item in ordered)} finding(s) and "
            f"{sum(len(item.evidence) for item in ordered)} evidence item(s). "
            f"Current priority is {level} with {confidence}% confidence."
        )
        if errors:
            summary += f" {errors} module(s) require review or retry."

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
        )
        if progress:
            progress("pipeline", 100, "Intelligence pipeline complete.", None)
        return result


__all__ = [
    "IntelligenceEngine",
    "IntelligenceModuleResult",
    "IntelligenceRunResult",
    "IntelligenceFinding",
    "IntelligenceEvidence",
]
