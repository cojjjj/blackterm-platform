from datetime import datetime, timezone

from .database import ScanRepository
from .models import ScanContext
from .plugins import PluginManager
from .scanner import scan_host
from .operations import new_operation_id
from .attack_surface import build_attack_surface
from .fingerprinting import fingerprint_scan


class ReconEngine:
    def __init__(self, config, logger, event_bus=None):
        self.config = config
        self.event_bus = event_bus
        self.logger = logger
        self.repository = ScanRepository(config.database_path)
        self.plugins = PluginManager(config.plugin_directory, logger)
        self.plugins.discover()

    def scan(self, target, ports, progress=None, profile="custom"):
        operation_id = new_operation_id()
        self.logger.info(
            "Scan started operation=%s target=%s ports=%d profile=%s",
            operation_id, target, len(ports), profile,
        )
        if self.event_bus:
            from .events import EventLevel
            self.event_bus.emit(
                "network", f"Scanning {target} across {len(ports)} TCP ports.",
                title="Scan Started", level=EventLevel.INFO, module="recon",
                metadata={"target": target, "ports": len(ports), "operation_id": operation_id, "profile": profile},
            )
        events = []
        events.append((
            datetime.now(timezone.utc).isoformat(),
            "START",
            f"{operation_id} started for {target} across {len(ports)} ports ({profile})",
        ))

        def wrapped_progress(done, total, item):
            if item.state == "open":
                events.append((
                    datetime.now(timezone.utc).isoformat(),
                    "OPEN",
                    f"{item.port}/tcp {item.service}",
                ))
                if self.event_bus:
                    from .events import EventLevel
                    level = (
                        EventLevel.WARNING
                        if item.service in {"microsoft-ds", "telnet", "vnc"}
                        else EventLevel.SUCCESS
                    )
                    self.event_bus.emit(
                        "network",
                        f"{item.port}/tcp responded as {item.service}.",
                        title="Open Port Observed",
                        level=level,
                        module="recon",
                        metadata={
                            "target": target,
                            "port": item.port,
                            "service": item.service,
                            "latency_ms": item.latency_ms,
                        },
                    )
            if progress:
                progress(done, total, item)

        result = scan_host(
            target, ports, self.config, wrapped_progress,
            operation_id=operation_id, profile=profile,
        )
        result.plugin_results = self.plugins.execute_all(
            ScanContext(result=result, config=self.config)
        )
        result.fingerprints = fingerprint_scan(
            result, timeout=max(1.0, self.config.banner_timeout)
        )
        result.attack_surface = build_attack_surface(result).to_dict()
        if self.event_bus:
            from .events import EventLevel
            services = sorted({item.service for item in result.open_ports})
            self.event_bus.emit(
                "ai",
                (
                    "Observed services: " + ", ".join(services)
                    if services
                    else "No open services were observed."
                ),
                title="Automated Scan Analysis",
                level=EventLevel.AI,
                module="assistant",
                metadata={"target": target},
            )
        scan_id = self.repository.save(result)
        events.append((
            datetime.now(timezone.utc).isoformat(),
            "DONE",
            f"Scan completed with {len(result.open_ports)} open ports",
        ))
        self.repository.save_events(scan_id, events)
        self.logger.info(
            "Scan complete id=%d operation=%s target=%s open_ports=%d",
            scan_id, operation_id, target, len(result.open_ports)
        )
        if self.event_bus:
            from .events import EventLevel
            self.event_bus.emit(
                "network",
                f"Scan completed in {result.duration_seconds}s with "
                f"{len(result.open_ports)} open port(s).",
                title="Scan Complete",
                level=EventLevel.SUCCESS,
                scan_id=scan_id,
                module="recon",
                metadata={"target": target, "duration": result.duration_seconds},
            )
        return scan_id, result
