from PySide6.QtCore import QObject, Signal, Slot


class ScanWorker(QObject):
    progress = Signal(int, int, object)
    completed = Signal(int, object)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, engine, target, ports, profile="custom"):
        super().__init__()
        self.engine = engine
        self.target = target
        self.ports = ports
        self.profile = profile

    @Slot()
    def run(self):
        try:
            scan_id, result = self.engine.scan(
                self.target,
                self.ports,
                progress=lambda done, total, item: self.progress.emit(done, total, item),
                profile=self.profile,
            )
            self.completed.emit(scan_id, result)
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.finished.emit()
