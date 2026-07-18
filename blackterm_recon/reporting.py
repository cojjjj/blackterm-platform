from __future__ import annotations
from datetime import datetime
from html import escape
from pathlib import Path

from .desktop.network_model import exposure_score


def write_html(result, destination=None):
    out = Path(destination) if destination else Path.home() / ".blackterm-recon" / "reports" / f"scan_{result.ip.replace('.', '_')}_{datetime.now():%Y%m%d_%H%M%S}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = "".join(
        f"<tr><td>{p.port}/tcp</td><td>{escape(p.state)}</td><td>{escape(p.service)}</td><td>{p.latency_ms or '-'} ms</td><td>{escape(p.banner or '')}</td></tr>"
        for p in result.open_ports
    )
    services = ", ".join(sorted({p.service for p in result.open_ports})) or "None observed"
    html = f"""<!doctype html><html><head><meta charset='utf-8'><title>BLACKTERM // RECON</title><style>
body{{background:#08060d;color:#f5efff;font-family:Segoe UI,Arial;margin:0}}header{{padding:42px;background:linear-gradient(135deg,#12081c,#08060d);border-bottom:1px solid #3b2450}}.brand{{color:#c000ff;font-size:34px;font-weight:900}}main{{padding:32px;max-width:1200px;margin:auto}}.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}}.card{{background:#100b17;border:1px solid #372342;border-radius:12px;padding:18px}}.value{{color:#c000ff;font-size:28px;font-weight:800}}table{{width:100%;border-collapse:collapse;margin-top:24px;background:#100b17}}th,td{{padding:12px;border-bottom:1px solid #372342;text-align:left}}th{{color:#c000ff}}.muted{{color:#9b8aa8}}
</style></head><body><header><div class='brand'>BLACKTERM // RECON</div><div class='muted'>Authorized Network Visibility Report</div></header><main><div class='grid'><div class='card'>Target<div class='value'>{escape(result.target)}</div></div><div class='card'>IP<div class='value'>{escape(result.ip)}</div></div><div class='card'>Open Ports<div class='value'>{len(result.open_ports)}</div></div><div class='card'>Duration<div class='value'>{result.duration_seconds}s</div></div></div><div class='card' style='margin-top:18px'><h2>Executive Summary</h2><p>Observed services: {escape(services)}.</p><p class='muted'>Exposure does not imply vulnerability. Validate configuration only on systems you are authorized to assess.</p></div><table><thead><tr><th>Port</th><th>State</th><th>Service</th><th>Latency</th><th>Banner</th></tr></thead><tbody>{rows}</tbody></table></main></body></html>"""
    out.write_text(html, encoding="utf-8")
    return out


def write_pdf(result, destination):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    out = Path(destination)
    out.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(out), pagesize=letter)
    styles = getSampleStyleSheet()
    story = [Paragraph("BLACKTERM // RECON", styles["Title"]), Paragraph("Authorized Network Visibility Report", styles["Heading2"]), Spacer(1, 12), Paragraph(f"Target: {result.target} ({result.ip})", styles["BodyText"]), Paragraph(f"Open ports: {len(result.open_ports)} | Duration: {result.duration_seconds}s", styles["BodyText"]), Spacer(1, 16)]
    data = [["Port", "State", "Service", "Latency"]] + [[f"{p.port}/tcp", p.state, p.service, f"{p.latency_ms or '-'} ms"] for p in result.open_ports]
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#29053a")), ("TEXTCOLOR", (0,0), (-1,0), colors.white), ("GRID", (0,0), (-1,-1), .5, colors.grey), ("PADDING", (0,0), (-1,-1), 7)]))
    story.append(table)
    doc.build(story)
    return out
