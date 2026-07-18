import sys

from PySide6.QtWidgets import QApplication

from ..config import load_config
from ..engine import ReconEngine
from ..events import EventBus, EventStore
from ..logging_setup import configure_logging
from .main_window import MainWindow
from .startup import StartupSequence


def main() -> int:
    config = load_config()
    logger = configure_logging(config.log_level, config.log_path)
    event_store = EventStore(config.database_path)
    event_bus = EventBus(event_store)
    engine = ReconEngine(config, logger, event_bus=event_bus)

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("BLACKTERM")

    operator = {"name": "OPERATOR"}
    startup = StartupSequence()
    startup.accepted_operator.connect(
        lambda name: operator.__setitem__("name", name)
    )
    if startup.exec() != StartupSequence.Accepted:
        return 0

    window = MainWindow(engine, operator["name"], event_bus, event_store)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
