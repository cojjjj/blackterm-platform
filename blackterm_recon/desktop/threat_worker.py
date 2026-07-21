from __future__ import annotations
from PySide6.QtCore import QObject, Signal, Slot
from ..threat_intelligence import ThreatIntelligenceEngine


class ThreatIntelligenceWorker(QObject):
    progress = Signal(str, int, str, object)
    completed = Signal(object)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, target: str, providers: tuple[str, ...], config):
        super().__init__()
        self.target = target
        self.providers = providers
        self.config = config

    @Slot()
    def run(self):
        try:
            engine = ThreatIntelligenceEngine(
                timeout=max(3.0, float(getattr(self.config, "threat_timeout", 8.0))),
                virustotal_api_key=getattr(self.config, "virustotal_api_key", ""),
                abuseipdb_api_key=getattr(self.config, "abuseipdb_api_key", ""),
            )
            result = engine.run(self.target, enabled_providers=self.providers, progress=self.progress.emit)
            self.completed.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.finished.emit()
