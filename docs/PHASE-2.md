# Phase 2 Desktop Alpha

The desktop application talks only to `ReconEngine`.

```text
PySide6 GUI
    |
    v
ReconEngine
  |   |   |
Scan DB Plugins
```

The GUI never writes raw SQL and does not directly coordinate sockets. Long-running scans execute through `ScanWorker` on a `QThread`.
