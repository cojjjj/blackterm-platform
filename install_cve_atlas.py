from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
PROJECT = Path.cwd()
main = PROJECT / "blackterm_recon" / "desktop" / "main_window.py"
dock = PROJECT / "blackterm_recon" / "desktop" / "dock.py"
if not main.exists() or not dock.exists():
    raise SystemExit("Run this installer from the BLACKTERM project root.")

for rel in [
    "blackterm_recon/intelligence/cve_atlas.py",
    "blackterm_recon/desktop/pages/cve_atlas.py",
]:
    src = ROOT / rel
    dst = PROJECT / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(f"Installed: {rel}")

backup_dir = PROJECT / ".blackterm-backups"
backup_dir.mkdir(exist_ok=True)
for path in (main, dock):
    backup = backup_dir / f"{path.name}.before-cve-atlas"
    if not backup.exists():
        shutil.copy2(path, backup)

text = main.read_text(encoding="utf-8")
imp = "from .pages.cve_atlas import CVEAtlasPage"
if imp not in text:
    text = text.replace("from .pages.threat_intelligence import ThreatIntelligencePage", "from .pages.threat_intelligence import ThreatIntelligencePage\n" + imp)
if "self.cve_atlas = CVEAtlasPage" not in text:
    text = text.replace("self.threat_intelligence = ThreatIntelligencePage(engine, event_bus)", "self.threat_intelligence = ThreatIntelligencePage(engine, event_bus)\n        self.cve_atlas = CVEAtlasPage(engine, event_bus)")
if '("CVE ATLAS", self.cve_atlas),' not in text:
    text = text.replace('(\"THREAT INTELLIGENCE\", self.threat_intelligence),', '(\"THREAT INTELLIGENCE\", self.threat_intelligence),\n            (\"CVE ATLAS\", self.cve_atlas),')
text = text.replace("BLACKTERM X v10.0", "BLACKTERM X v10.6")
main.write_text(text, encoding="utf-8")

dtext = dock.read_text(encoding="utf-8")
if '"CVE ATLAS": "◫",' not in dtext:
    dtext = dtext.replace('"THREAT INTELLIGENCE": "◌",', '"THREAT INTELLIGENCE": "◌",\n    "CVE ATLAS": "◫",')
if '"CVE ATLAS",' not in dtext:
    dtext = dtext.replace('"THREAT INTELLIGENCE",\n        ),', '"THREAT INTELLIGENCE",\n            "CVE ATLAS",\n        ),')
dock.write_text(dtext, encoding="utf-8")
print("Updated: main_window.py")
print("Updated: dock.py")
print("BLACKTERM CVE Atlas v10.6 installed.")
