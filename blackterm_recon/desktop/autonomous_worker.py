from PySide6.QtCore import QObject, Signal, Slot

from ..autonomous_workflow import AutonomousWorkflowEngine


class AutonomousWorkflowWorker(QObject):
    progress = Signal(str, int, str, object)
    completed = Signal(object)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, engine, event_bus, options):
        super().__init__()
        self.workflow = AutonomousWorkflowEngine(engine, event_bus)
        self.options = options

    @Slot()
    def run(self):
        try:
            result = self.workflow.run(
                self.options,
                progress=lambda stage, percent, message, metadata: self.progress.emit(
                    stage, percent, message, metadata
                ),
            )
            self.completed.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.finished.emit()
