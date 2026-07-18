from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from time import perf_counter
from typing import Callable
import socket

from .banner import grab_banner
from .config import AppConfig
from .models import PortResult, ScanResult
from .resolver import enforce_target_policy
from .services import identify_service


ProgressCallback = Callable[[int, int, PortResult], None]


def scan_port(ip, port, timeout, banners, banner_timeout) -> PortResult:
    started = perf_counter()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            code = sock.connect_ex((ip, port))
        latency = round((perf_counter() - started) * 1000, 2)
        if code == 0:
            return PortResult(
                port=port,
                state="open",
                service=identify_service(port),
                latency_ms=latency,
                banner=grab_banner(ip, port, banner_timeout) if banners else None,
            )
        return PortResult(port=port, state="closed", latency_ms=latency)
    except socket.timeout:
        return PortResult(port=port, state="filtered", error="timeout")
    except OSError as exc:
        return PortResult(port=port, state="error", error=str(exc))


def scan_host(target: str, ports: list[int], config: AppConfig, progress=None) -> ScanResult:
    ip, hostname = enforce_target_policy(target, config.allow_public_targets)
    started_at = datetime.now(timezone.utc)
    timer = perf_counter()
    results = []

    with ThreadPoolExecutor(max_workers=min(config.workers, len(ports) or 1)) as pool:
        futures = [
            pool.submit(
                scan_port,
                ip,
                port,
                config.timeout,
                config.banners,
                config.banner_timeout,
            )
            for port in ports
        ]
        for done, future in enumerate(as_completed(futures), start=1):
            result = future.result()
            results.append(result)
            if progress:
                progress(done, len(ports), result)

    results.sort(key=lambda x: x.port)
    finished_at = datetime.now(timezone.utc)
    return ScanResult(
        target=target,
        ip=ip,
        hostname=hostname,
        ports=results,
        started_at=started_at.isoformat(),
        finished_at=finished_at.isoformat(),
        duration_seconds=round(perf_counter() - timer, 3),
    )
