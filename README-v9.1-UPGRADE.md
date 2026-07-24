# BLACKTERM v9.1 — Live Operations Upgrade

This release upgrades the v9 intelligence platform without replacing the existing architecture.

## New in v9.1

- Live CPU, memory, disk, network, thread, and connection telemetry in Mission Control
- Upgraded Investigation Workspace with operational risk scoring
- Exposure summary cards based on actual scan results
- Context-aware BLACKTERM AI next-action guidance
- Version and title updated to v9.1
- Existing command palette, autonomous workflow, cases, graphs, reports, plugins, and scanning preserved

## Run on Windows

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
blackterm-desktop
```

You can also run:

```powershell
python -m blackterm_recon.desktop.app
```
