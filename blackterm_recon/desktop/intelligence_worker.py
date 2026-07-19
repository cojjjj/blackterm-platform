from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from ..intelligence.engine import IntelligenceEngine


class IntelligenceWorker(QObject):
    progress = Signal(str, int, str, object)
    completed = Signal(object)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, target: str, enabled_modules: tuple[str, ...]):
        super().__init__()
        self.target = target
        self.enabled_modules = enabled_modules

    @Slot()
    def run(self):
        try:
            engine = IntelligenceEngine()
            result = engine.run(
                self.target,
                enabled_modules=self.enabled_modules,
                progress=lambda module, percent, message, module_result: self.progress.emit(
                    module, percent, message, module_result
                ),
            )
            self.completed.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.finished.emit()
