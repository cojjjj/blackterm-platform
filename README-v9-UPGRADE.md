# BLACKTERM v9.0 — Intelligence Platform Shell

This upgrade keeps the existing reconnaissance, cases, event, intelligence, graph, reporting, and plugin systems intact while introducing a cleaner professional desktop shell.

## Added

- Persistent workspace header with current module, operator, clock, and platform status
- One-click **New Investigation** action available from every workspace
- Searchable **Ctrl+K Command Palette**
- Fast navigation across investigations, intelligence, maps, reports, plugins, and settings
- Upgraded command bar with keyboard shortcut discovery
- Updated BLACKTERM v9 platform branding and navigation sizing
- Additional premium styling for the new shell and command palette

## Command Palette

Press `Ctrl+K`, search for a workspace, then press Enter. The palette supports routes such as:

```text
Mission Control
Investigation Workspace
Cases
Attack Surface
Relationship Graph
Global Intelligence
Threat Intelligence
OSINT
Reports
BLACKTERM AI
Plugins
Settings
```

The normal command bar still accepts commands such as:

```text
open mission
open investigation
open graph
open threat
open reports
```

## Run

```powershell
python -m pip install -e .
blackterm-desktop
```

Only scan or analyze systems you own or are explicitly authorized to test.
