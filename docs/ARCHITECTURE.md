# BLACKTERM Architecture

BLACKTERM is organized as a modular desktop platform with clear separation between engine, persistence, event, reporting, and user-interface layers.

## Core Layers

### Recon Engine

Responsible for target validation, resolution, threaded TCP scanning, service detection, banner collection, and normalized scan results.

### Persistence

SQLite-backed repositories store scan history, events, configuration, and future case information.

### Event System

A platform event bus connects scans, reports, AI analysis, cases, plugins, and desktop notifications without tightly coupling modules.

### Desktop UI

PySide6 pages and widgets present Mission Control, scans, history, network visualization, reports, plugins, and settings.

### Reporting

Report builders turn normalized scan results into human-readable HTML and PDF outputs.

## Design Goals

- Modular components
- Clear boundaries between UI and engine code
- Persistent, queryable history
- Testable backend behavior
- Extensible event and plugin systems
- Responsible and authorized use by design
