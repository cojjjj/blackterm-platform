from __future__ import annotations
from datetime import datetime
from html import escape
import json
from pathlib import Path


def case_payload(repository, case_id: int) -> dict:
    case = next((c for c in repository.list_cases() if c["id"] == case_id), None)
    if case is None:
        raise ValueError("Case not found")
    return {"case": case, "scans": repository.case_scans(case_id),
            "notes": repository.case_notes(case_id),
            "evidence": repository.case_evidence(case_id),
            "timeline": repository.case_timeline(case_id)}


def write_case_report(repository, case_id: int, destination: str | Path, format_name: str):
    data = case_payload(repository, case_id)
    out = Path(destination)
    out.parent.mkdir(parents=True, exist_ok=True)
    fmt = format_name.lower()
    if fmt == "json":
        out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    elif fmt in {"md", "markdown"}:
        c=data["case"]
        lines=[f"# BLACKTERM Case #{c['id']}: {c['name']}", "", f"**Status:** {c['status']}",
               f"**Created:** {c['created_at']}", "", "## Scope", c['description'] or "No scope recorded.",
               "", "## Timeline"]
        lines += [f"- `{e['created_at']}` **{e['event_type']}** — {e['title']} {e['detail']}" for e in data['timeline']]
        lines += ["", "## Evidence"] + [f"- **{e['title']}** ({e['evidence_type']}) — SHA-256 `{e['sha256']}`" for e in data['evidence']]
        lines += ["", "## Notes"] + [f"### {n['created_at']}\n{n['note']}" for n in data['notes']]
        out.write_text("\n".join(lines), encoding="utf-8")
    elif fmt == "html":
        c=data['case']; timeline=''.join(f"<li><b>{escape(e['event_type'])}</b> {escape(e['title'])}<small>{escape(e['created_at'])}</small><p>{escape(e['detail'])}</p></li>" for e in data['timeline'])
        evidence=''.join(f"<tr><td>{escape(e['evidence_type'])}</td><td>{escape(e['title'])}</td><td><code>{escape(e['sha256'][:16])}…</code></td></tr>" for e in data['evidence'])
        notes=''.join(f"<article><small>{escape(n['created_at'])}</small><p>{escape(n['note'])}</p></article>" for n in data['notes'])
        html=f"""<!doctype html><meta charset='utf-8'><title>BLACKTERM Case #{c['id']}</title><style>body{{background:#08060d;color:#e9ddff;font:15px Segoe UI;margin:0}}header,main{{max-width:1100px;margin:auto;padding:28px}}header{{border-bottom:1px solid #3b2450}}h1,h2{{color:#c000ff}}.card,article{{background:#100b17;border:1px solid #372342;border-radius:12px;padding:16px;margin:12px 0}}small{{display:block;color:#8da0ba}}table{{width:100%;border-collapse:collapse}}td,th{{padding:10px;border-bottom:1px solid #372342;text-align:left}}</style><header><h1>BLACKTERM // CASE #{c['id']}</h1><p>{escape(c['name'])} · {escape(c['status'])}</p></header><main><section class='card'><h2>Scope</h2><p>{escape(c['description'] or 'No scope recorded.')}</p></section><section class='card'><h2>Timeline</h2><ol>{timeline}</ol></section><section class='card'><h2>Evidence Locker</h2><table><tr><th>Type</th><th>Title</th><th>Hash</th></tr>{evidence}</table></section><section><h2>Notes</h2>{notes}</section></main>"""
        out.write_text(html, encoding='utf-8')
    elif fmt == "pdf":
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        styles=getSampleStyleSheet(); story=[]; c=data['case']
        story += [Paragraph(f"BLACKTERM Case #{c['id']}: {c['name']}", styles['Title']), Paragraph(f"Status: {c['status']}", styles['Heading2']), Paragraph(c['description'] or 'No scope recorded.', styles['BodyText']), Spacer(1,12), Paragraph('Timeline', styles['Heading2'])]
        story += [Paragraph(f"{e['created_at']} — {e['event_type']}: {e['title']} {e['detail']}", styles['BodyText']) for e in data['timeline']]
        story += [Spacer(1,12), Paragraph('Evidence', styles['Heading2'])]
        story += [Paragraph(f"{e['evidence_type']} — {e['title']} — SHA-256 {e['sha256']}", styles['BodyText']) for e in data['evidence']]
        SimpleDocTemplate(str(out), pagesize=letter).build(story)
    else:
        raise ValueError(f"Unsupported report format: {format_name}")
    return out
