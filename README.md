
## Attack Surface Intelligence

Every completed authorized scan now produces a consolidated attack-surface profile with:

- Open ports and classified services
- Network, web, remote-administration, and database exposure categories
- Lightweight technology signatures from banners and plugin data
- Prioritized findings with evidence and defensive recommendations
- Overall risk and surface-health scores
- Historical scan selection from the desktop Attack Surface page

The scoring is contextual triage, not proof of a vulnerability. Findings should be validated by an authorized operator.

## New in v5.4 — Operation Profiles

BLACKTERM RECON now includes a safer, profile-driven assessment workflow:

- **Quick** — six high-value common services
- **Standard** — balanced common-port assessment with banner detection
- **Full** — broader lab-oriented TCP assessment
- **Custom** — operator-selected ports and banner settings
- Mandatory authorization confirmation before execution
- Unique operation IDs such as `BT-20260720-194211-A3F9`
- Four-stage live scan timeline and clearer evidence records

# BLACKTERM v8.6 — Stability Foundation

```text
RenderSurface
    one ambient compositor

WidgetAnimator
    paint-safe widget updates

GraphicsItemAnimator
    timer-driven graph motion

Current tests
    validate the architecture that ships
```

## Responsible Use

Only scan or analyze assets you own or are explicitly authorized to test. BLACKTERM is built for education, defensive security, lab use, authorized assessments, and portfolio development.

## Contributing

Ideas, bug reports, and focused pull requests are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) before contributing.

## Security

Do not publish sensitive vulnerability details in a public issue. Follow [SECURITY.md](SECURITY.md).

## License

Released under the [MIT License](LICENSE).

---

<div align="center">

Built by [cojjjj](https://github.com/cojjjj) — active development, public preview.

</div>

<!-- BLACKTERM_STATS_START -->
## `blackterm> project --stats`

```text
╔══════════════════════════════════════════════════════════════╗
║                 BLACKTERM PLATFORM v5.6.0                 ║
╚══════════════════════════════════════════════════════════════╝

 STATUS............... ONLINE
 DEVELOPMENT.......... ACTIVE
 SOURCE LINES......... 14,354
 TOTAL TRACKED LINES.. 16,052
 PYTHON LINES......... 15,487
 TEST LINES........... 1,133
 DOCUMENTATION LINES.. 448

 PYTHON FILES......... 130
 PROJECT FILES........ 144
 MODULES.............. 75
 DESKTOP PAGES........ 14
 TESTS DISCOVERED..... 93
 COMMITS.............. 11
 CONTRIBUTORS......... 3

 LANGUAGE TELEMETRY
 Python: 15,487 • Markdown: 448 • YAML: 59 • TOML: 34 • JSON: 24

 LAST REFRESH......... 2026-07-21T02:01:01+00:00
 NEXT OBJECTIVE....... AUTONOMOUS OSINT ENGINE
```

<p align="center">
  <img src="assets/project-stats.svg" alt="BLACKTERM live project statistics" />
</p>
<!-- BLACKTERM_STATS_END -->
