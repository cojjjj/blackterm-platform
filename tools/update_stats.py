from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

START_MARKER = "<!-- BLACKTERM_STATS_START -->"
END_MARKER = "<!-- BLACKTERM_STATS_END -->"

EXCLUDED_DIRS = {
    ".git", ".venv", "venv", "env", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", ".tox", "build", "dist", "site",
    "node_modules", ".idea", ".vscode", "htmlcov", "coverage",
}

CODE_EXTENSIONS = {
    ".py": "Python",
    ".qss": "Qt Stylesheet",
    ".json": "JSON",
    ".toml": "TOML",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".md": "Markdown",
    ".html": "HTML",
    ".css": "CSS",
    ".js": "JavaScript",
    ".ps1": "PowerShell",
    ".sh": "Shell",
}

SOURCE_EXTENSIONS = {".py", ".qss", ".html", ".css", ".js", ".ps1", ".sh"}


@dataclass(frozen=True)
class ProjectStats:
    version: str
    generated_at: str
    total_lines: int
    source_lines: int
    python_lines: int
    test_lines: int
    documentation_lines: int
    total_files: int
    python_files: int
    test_files: int
    modules: int
    desktop_pages: int
    commits: int
    contributors: int
    tests_collected: int
    languages: dict[str, int]


def iter_project_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in CODE_EXTENSIONS:
            continue
        yield path


def line_count(path: Path) -> int:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            return sum(1 for _ in handle)
    except OSError:
        return 0


def git_output(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args], cwd=root, capture_output=True, text=True,
            check=True, timeout=10,
        )
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def detect_version(root: Path) -> str:
    init_file = root / "blackterm_recon" / "__init__.py"
    if init_file.exists():
        text = init_file.read_text(encoding="utf-8", errors="replace")
        match = re.search(r'__version__\s*=\s*["\']([^"\']+)', text)
        if match:
            return match.group(1)

    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        text = pyproject.read_text(encoding="utf-8", errors="replace")
        match = re.search(r'^version\s*=\s*["\']([^"\']+)', text, re.MULTILINE)
        if match:
            return match.group(1)
    return "development"


def collect_test_count(root: Path) -> int:
    output = git_output(root, "ls-files", "tests")
    test_paths = [root / line for line in output.splitlines() if line.endswith(".py")]
    if not test_paths:
        test_paths = list((root / "tests").rglob("test_*.py")) if (root / "tests").exists() else []

    count = 0
    pattern = re.compile(r"^\s*(?:async\s+)?def\s+test_[A-Za-z0-9_]+\s*\(", re.MULTILINE)
    for path in test_paths:
        try:
            count += len(pattern.findall(path.read_text(encoding="utf-8", errors="replace")))
        except OSError:
            pass
    return count


def collect_stats(root: Path) -> ProjectStats:
    files = list(iter_project_files(root))
    counts = {path: line_count(path) for path in files}
    language_lines: Counter[str] = Counter()

    for path, lines in counts.items():
        language_lines[CODE_EXTENSIONS[path.suffix.lower()]] += lines

    python_files = [p for p in files if p.suffix.lower() == ".py"]
    test_files = [p for p in python_files if "tests" in p.parts or p.name.startswith("test_")]
    source_files = [p for p in files if p.suffix.lower() in SOURCE_EXTENSIONS and p not in test_files]
    doc_files = [p for p in files if p.suffix.lower() == ".md"]

    package_root = root / "blackterm_recon"
    modules = len([p for p in python_files if package_root in p.parents and p.name != "__init__.py"])
    pages_root = package_root / "desktop" / "pages"
    desktop_pages = len([p for p in python_files if pages_root in p.parents and p.name != "__init__.py"])

    commit_text = git_output(root, "rev-list", "--count", "HEAD")
    commits = int(commit_text) if commit_text.isdigit() else 0

    contributor_text = git_output(root, "shortlog", "-sne", "HEAD")
    contributors = len([line for line in contributor_text.splitlines() if line.strip()])

    return ProjectStats(
        version=detect_version(root),
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        total_lines=sum(counts.values()),
        source_lines=sum(counts[p] for p in source_files),
        python_lines=sum(counts[p] for p in python_files),
        test_lines=sum(counts[p] for p in test_files),
        documentation_lines=sum(counts[p] for p in doc_files),
        total_files=len(files),
        python_files=len(python_files),
        test_files=len(test_files),
        modules=modules,
        desktop_pages=desktop_pages,
        commits=commits,
        contributors=contributors,
        tests_collected=collect_test_count(root),
        languages=dict(language_lines.most_common()),
    )


def format_number(value: int) -> str:
    return f"{value:,}"


def terminal_block(stats: ProjectStats) -> str:
    language_summary = " • ".join(
        f"{name}: {format_number(lines)}" for name, lines in list(stats.languages.items())[:5]
    ) or "No source files detected"

    return f"""{START_MARKER}
## `blackterm> project --stats`

```text
╔══════════════════════════════════════════════════════════════╗
║                 BLACKTERM PLATFORM v{stats.version:<22}║
╚══════════════════════════════════════════════════════════════╝

 STATUS............... ONLINE
 DEVELOPMENT.......... ACTIVE
 SOURCE LINES......... {format_number(stats.source_lines)}
 TOTAL TRACKED LINES.. {format_number(stats.total_lines)}
 PYTHON LINES......... {format_number(stats.python_lines)}
 TEST LINES........... {format_number(stats.test_lines)}
 DOCUMENTATION LINES.. {format_number(stats.documentation_lines)}

 PYTHON FILES......... {format_number(stats.python_files)}
 PROJECT FILES........ {format_number(stats.total_files)}
 MODULES.............. {format_number(stats.modules)}
 DESKTOP PAGES........ {format_number(stats.desktop_pages)}
 TESTS DISCOVERED..... {format_number(stats.tests_collected)}
 COMMITS.............. {format_number(stats.commits)}
 CONTRIBUTORS......... {format_number(stats.contributors)}

 LANGUAGE TELEMETRY
 {language_summary}

 LAST REFRESH......... {stats.generated_at}
 NEXT OBJECTIVE....... AUTONOMOUS OSINT ENGINE
```

<p align="center">
  <img src="assets/project-stats.svg" alt="BLACKTERM live project statistics" />
</p>
{END_MARKER}"""


def replace_stats_section(readme: Path, block: str) -> bool:
    if readme.exists():
        content = readme.read_text(encoding="utf-8", errors="replace")
    else:
        content = "# BLACKTERM Platform\n"

    pattern = re.compile(
        re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER), re.DOTALL
    )
    if pattern.search(content):
        updated = pattern.sub(block, content)
    else:
        separator = "\n\n" if content.rstrip() else ""
        updated = content.rstrip() + separator + block + "\n"

    changed = updated != content
    if changed:
        readme.write_text(updated, encoding="utf-8", newline="\n")
    return changed


def svg_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def write_svg(path: Path, stats: ProjectStats) -> None:
    rows = [
        ("VERSION", f"v{stats.version}"),
        ("SOURCE LINES", format_number(stats.source_lines)),
        ("PYTHON FILES", format_number(stats.python_files)),
        ("MODULES", format_number(stats.modules)),
        ("TESTS", format_number(stats.tests_collected)),
        ("COMMITS", format_number(stats.commits)),
    ]
    row_markup = []
    for index, (label, value) in enumerate(rows):
        y = 105 + index * 34
        row_markup.append(
            f'<text x="34" y="{y}" class="label">{svg_escape(label)}</text>'
            f'<text x="466" y="{y}" text-anchor="end" class="value">{svg_escape(value)}</text>'
        )

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="500" height="330" viewBox="0 0 500 330" role="img" aria-label="BLACKTERM project statistics">
  <defs>
    <linearGradient id="bg" x1="0" x2="1" y1="0" y2="1">
      <stop offset="0" stop-color="#050912"/>
      <stop offset="1" stop-color="#12071c"/>
    </linearGradient>
    <filter id="glow"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  </defs>
  <rect width="500" height="330" rx="14" fill="url(#bg)" stroke="#2c6d91"/>
  <path d="M0 58 H500" stroke="#242b43"/>
  <circle cx="34" cy="30" r="5" fill="#00f5a0" filter="url(#glow)"/>
  <text x="50" y="36" class="title">BLACKTERM // LIVE BUILD TELEMETRY</text>
  {''.join(row_markup)}
  <path d="M26 287 H474" stroke="#242b43"/>
  <text x="34" y="313" class="footer">STATUS: ONLINE</text>
  <text x="466" y="313" text-anchor="end" class="footer">UPDATED {svg_escape(stats.generated_at[:10])}</text>
  <style>
    text {{ font-family: Consolas, 'Courier New', monospace; }}
    .title {{ fill:#e9f4ff; font-size:14px; font-weight:700; letter-spacing:1px; }}
    .label {{ fill:#8da9c4; font-size:13px; }}
    .value {{ fill:#2eb7ff; font-size:15px; font-weight:700; }}
    .footer {{ fill:#00f5a0; font-size:11px; letter-spacing:.7px; }}
  </style>
</svg>'''
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(svg, encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh BLACKTERM repository statistics.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--check", action="store_true", help="Exit 1 when generated files are stale.")
    parser.add_argument("--print", dest="print_stats", action="store_true", help="Print JSON statistics.")
    args = parser.parse_args()

    root = args.root.resolve()
    stats = collect_stats(root)
    readme = root / "README.md"
    stats_json = root / "assets" / "project-stats.json"
    stats_svg = root / "assets" / "project-stats.svg"

    before_readme = readme.read_text(encoding="utf-8", errors="replace") if readme.exists() else ""
    before_json = stats_json.read_text(encoding="utf-8", errors="replace") if stats_json.exists() else ""
    before_svg = stats_svg.read_text(encoding="utf-8", errors="replace") if stats_svg.exists() else ""

    replace_stats_section(readme, terminal_block(stats))
    stats_json.parent.mkdir(parents=True, exist_ok=True)
    stats_json.write_text(json.dumps(asdict(stats), indent=2) + "\n", encoding="utf-8")
    write_svg(stats_svg, stats)

    changed = (
        before_readme != readme.read_text(encoding="utf-8")
        or before_json != stats_json.read_text(encoding="utf-8")
        or before_svg != stats_svg.read_text(encoding="utf-8")
    )

    if args.print_stats:
        print(json.dumps(asdict(stats), indent=2))
    else:
        print(
            f"BLACKTERM stats refreshed: {stats.source_lines:,} source lines, "
            f"{stats.python_files} Python files, {stats.tests_collected} tests."
        )

    return 1 if args.check and changed else 0


if __name__ == "__main__":
    raise SystemExit(main())
