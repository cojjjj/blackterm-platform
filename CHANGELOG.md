# Changelog

## 5.6.0 — Attack Surface Analyst Experience

- Added a glowing, color-coded risk badge.
- Added exposure category cards and proportional surface bars.
- Added technology signature chips.
- Added a local analyst summary generated from observed scan evidence.
- Added CVSS-context columns for prioritization.
- Added interactive finding dossiers with evidence, recommendation, and MITRE ATT&CK context.
- Rebranded the desktop title as BLACKTERM RECON.

## 5.5.0 — Attack Surface Intelligence

- Added a structured Attack Surface Intelligence engine.
- Added risk scoring, surface health scoring, severity counts, and exposure categories.
- Added service-aware findings and defensive recommendations.
- Added lightweight technology detection from service banners and plugin output.
- Added a dedicated Attack Surface desktop page with saved-scan selection.
- Connected completed scans directly to the Attack Surface view.
- Persisted operation ID, scan profile, and attack-surface JSON in SQLite.
- Added automated Attack Surface tests.

## 5.4.0 - Operation Profiles

- Added Quick, Standard, Full, and Custom scan profiles.
- Added mandatory authorization confirmation before a scan begins.
- Added unique BLACKTERM operation IDs to each scan.
- Added a four-stage live operation timeline.
- Added profile and operation metadata to persisted scan results.
- Improved scan controls and operator-facing status information.


## v8.6.0 — Stability Foundation

- Rebuilt animation ownership around QTimer.
- Fixed missing Qt import.
- Added valid PySide6 timer enum usage.
- Preserved paint-safe graph animations.
- Preserved correct QTextCursor usage.
- Consolidated all ambient rendering into RenderSurface.
- Removed stale AmbientBackdrop and ParticleField integration.
- Removed obsolete render tests.
- Added current architecture regression tests.
- Preserved the premium interface, Operator Dashboard, Intelligence Engine,
  Investigation Graph, Live Investigation, cases, evidence, timeline, AI,
  correlation, and reports.
